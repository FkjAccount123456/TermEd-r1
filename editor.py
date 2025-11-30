from typing import Callable, NamedTuple
from renderer import Theme, themes
from renderers.renderers import get_renderer
from screen import Screen, VScreen
from utils import ed_getch, flush, get_char_type, get_file_ext, get_width, log, gotoxy, init_term, reset_term
from drawer import Drawer, DrawerSettings
from buffer import BufferBase
from ederrors import *
from tagparse import parse_tags_file, tags_navigate, merge_tags, TagEntry, FileEntry
from fuzzy import fuzzy_find
from os import get_terminal_size
from textinputer import TextInputer
import os
import time
import threading as tr
import shutil
from queue import Queue
import multiprocessing as mp
from dataclasses import dataclass
from filetypes import get_filetype
from tagsgen import TagsGenerator


def check_tree(win: "Window"):
    if isinstance(win, TextBuffer):
        return f"TextBuffer({repr(win.file)})"
    if isinstance(win, Split):
        return f"Split({check_tree(win.win1)}, {check_tree(win.win2)})"
    return type(win).__name__


running = False


def getch_process(q):
    while running:
        q.put(ed_getch())


HSplit, VSplit = False, True
PrioBuffer = 0


# 又是可恶的徒手绘图（
# 要不然封装一下吧
def draw_text(self: "WindowLike", top: int, left: int, width: int, text: str, tp: str, prio=0, rev=False):
    # print(f"draw_text{(type(self).__name__, top, left, width, len(text), tp, prio)}")
    shw = 0
    color = self.editor.theme.get(tp, False)
    start = 0
    if rev and (sumw := sum(map(get_width, text))) > width:
        while start < len(text) and sumw > width:
            start += 1
            sumw -= get_width(text[start - 1])
    for ch in text[start:]:
        cur_width = get_width(ch)
        if shw + cur_width > width:
            break
        self.editor.screen.change(top, left + shw, ch, color, prio)
        shw += cur_width
    while shw < width:
        self.editor.screen.change(top, left + shw, " ", color, prio)
        shw += 1


def cmdcmp_files(arg: str):
    arg = os.path.expanduser(arg)
    dirname = os.path.dirname(arg)
    name = os.path.basename(arg)
    menu, ndels = [], []
    if os.path.exists(dirname) and os.path.isdir(dirname) or not dirname:
        words = os.listdir(dirname) if dirname else os.listdir()
        menu = filter(lambda x: x[:len(name)] == name, words)
        menu = list(map(lambda x: x + '/'[:os.path.isdir(os.path.join(dirname, x))], menu))
        menu.sort()
        ndels = [len(name) for _ in menu]
    return menu, ndels


def cmdcmp_dirs(arg: str):
    arg = os.path.expanduser(arg)
    dirname = os.path.dirname(arg)
    name = os.path.basename(arg)
    menu, ndels = [], []
    if os.path.exists(dirname) and os.path.isdir(dirname) or not dirname:
        words = os.listdir(dirname) if dirname else os.listdir()
        menu = list(filter(lambda x: x[:len(name)] == name and os.path.isdir(os.path.join(dirname, x)), words))
        menu.sort()
        ndels = [len(name) for _ in menu]
    return menu, ndels


class FileBase(BufferBase):
    def __init__(self, editor: "Editor"):
        super().__init__()
        self.editor = editor

    def reset_drawer(self):
        ...

    def reset_scroll(self):
        ...

    def init_settings(self):
        ...

    def reopen(self):
        assert self.file
        with open(self.file, "r", encoding="utf-8") as f:
            text = f.read()
        self.textinputer.clear()
        self.textinputer.insert(0, 0, text)
        self.y = self.ideal_x = self.x = 0
        self.textinputer.save()
        self.renderer = get_renderer(self.file)(self, self.text)

    def load_existed(self, path: str):
        # 大换血啊（
        #
        for model in self.editor.fb_maps[path]:
            self.textinputer = model.textinputer
            self.renderer = model.renderer
            self.y = self.ideal_x = self.x = 0
            self.reset_drawer()
            self.text = self.textinputer.text
        self.editor.fb_maps[path].add(self)

    def _open_file(self, arg: str, force=False):
        # 2025-8-18
        # 全是问题
        arg = arg.strip()
        old = self.file
        msg = None
        if not arg:
            if self.file and (force or self.textinputer.is_saved()) and os.path.exists(self.file):
                try:
                    self.reopen()
                    self.init_settings()
                    return 'Reopened ' + self.file
                except:
                    return 'Reopen failed'
            if not self.textinputer.is_saved() and not force:
                return 'Reopen failed, file not saved'
            return
        if arg:
            if self.file and os.path.abspath(self.file) == os.path.abspath(arg):
                if force and not self.textinputer.is_saved() and os.path.exists(self.file):
                    try:
                        self.reopen()
                        self.init_settings()
                        return 'Reopened ' + self.file
                    except:
                        return 'Reopen failed'
                if not self.textinputer.is_saved() and not force:
                    return 'Reopened failed, file not saved'
                return
            self.file = arg
        if self.file and (path := os.path.abspath(self.file)) in self.editor.fb_maps\
                and self.editor.fb_maps[path]:
            if not self.textinputer.is_saved() and not force:
                self.file = old
                return 'Open failed, file not saved'
            self.load_existed(path)
            msg = f'Opened {self.file}'
        elif self.file:
            if not self.textinputer.is_saved() and not force:
                self.file = old
                return 'Open failed, file not saved'
            if not os.path.exists(self.file):
                self.textinputer = TextInputer(self)
                self.text = self.textinputer.text
                self.renderer = get_renderer(self.file)(self, self.text)
                self.reset_drawer()
                self.y = self.ideal_x = self.x = 0
                self.textinputer.save()
                msg = 'Created a new buffer'
            else:
                try:
                    with open(self.file, "r", encoding="utf-8") as f:
                        text = f.read()
                    self.textinputer = TextInputer(self)
                    self.text = self.textinputer.text
                    self.renderer = get_renderer(self.file)(self, self.text)
                    self.textinputer.insert(0, 0, text)
                    self.reset_drawer()
                    self.y = self.ideal_x = self.x = 0
                    self.reset_scroll()
                    self.textinputer.save()
                    msg = f'Opened {self.file}'
                except:
                    msg = f'Failed to open {self.file}'
                    self.file = old
        if old:
            self.editor.fb_maps[os.path.abspath(old)].remove(self)
        if self.file:
            if os.path.abspath(self.file) not in self.editor.fb_maps:
                self.editor.fb_maps[os.path.abspath(self.file)] = set()
            self.editor.fb_maps[os.path.abspath(self.file)].add(self)
        self.init_settings()
        return msg

    def open_file(self, arg: str, force=False):
        if res := self._open_file(arg, force):
            self.editor.send_message(res)

    def _save_file(self, arg: str):
        msg = None
        if not (arg == "" and self.file is None):
            if arg:
                old_file = self.file
                self.file = arg
            else:
                old_file = self.file
            if isinstance(self.file, str):
                try:
                    with open(self.file, "w", encoding="utf-8") as f:
                        f.write("\n".join(self.text))
                    self.textinputer.save()
                    if not old_file or get_filetype(self.file) != get_filetype(old_file):
                        self.renderer = get_renderer(self.file)(self, self.text)
                    msg = f'Saved {self.file}'
                except:
                    self.file = old_file
                    msg = f'Failed to save {self.file}'
            if old_file is not None and os.path.abspath(old_file) != os.path.abspath(self.file)\
                    and os.path.exists(old_file):
                if os.path.abspath(old_file) in self.editor.fb_maps:
                    self.editor.fb_maps[os.path.abspath(old_file)].remove(self)
                if self.file is not None:
                    path = os.path.abspath(self.file)
                    self.editor.fb_maps[path].add(self)
        return msg

    def save_file(self, arg: str):
        if res := self._save_file(arg):
            self.editor.send_message(res)
        self.editor.hook_file_upd(arg)


class WindowLike:
    def __init__(self):
        self.floatwins: list[FloatWin] = []
        self.editor: Editor

    def get_prio(self):
        return PrioBuffer

    def draw(self):
        for win in self.floatwins:
            win.draw()


class KeyHolder:
    def __init__(self):
        self.keymap = {}
        self.cmdmap = {}
        self.cmdcmp = {}
        self.id: int

    def bind_key(self, mode: str, key: list[str], func: Callable):
        if mode not in self.keymap:
            self.keymap[mode] = {}
        cur = self.keymap[mode]
        for k in key[:-1]:
            if k not in cur:
                cur[k] = {}
            cur = cur[k]
        cur[key[-1]] = func


    def cursor_real_pos(self) -> tuple[int, int]:
        ...

    def mode_normal(self):
        ...


class FloatWinFeatures(NamedTuple):
    border: bool = True


class FloatWin(WindowLike):
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: WindowLike | None,
                 features: FloatWinFeatures | None = None):
        super().__init__()
        self.top, self.left, self.h, self.w = top, left, h, w
        self.editor = editor
        self.parent = parent
        self.id = self.editor.alloc_id(self)
        self.features = features if features else FloatWinFeatures()
        self.v_screen = VScreen(self.top + self.features.border, self.left + self.features.border,
                                self.h - self.features.border * 2, self.w - self.features.border * 2,
                                self.editor.screen, self.get_prio())
        self.hide = False
        self.title = ""

    def resize(self, h: int, w: int):
        self.h, self.w = h, w
        self.v_screen.h = self.h - self.features.border * 2
        self.v_screen.w = self.w - self.features.border * 2

    def move(self, top: int, left: int):
        self.top, self.left = top, left
        self.v_screen.top = self.top + self.features.border
        self.v_screen.left = self.left + self.features.border

    def set_features(self, features: FloatWinFeatures):
        self.features = features

    def get_prio(self):
        if self.parent:
            return self.parent.get_prio() + 1
        return PrioBuffer

    def draw_text(self, top: int, left: int, text: str, tp: str):
        draw_text(self, self.v_screen.top + top, self.v_screen.left + left, self.v_screen.w,
                  text, tp, self.get_prio())

    def draw(self):
        super().draw()
        if self.hide:
            return
        if self.features.border:
            self.v_screen.change(-1, -1, "+", self.editor.theme.get("border", False))
            self.v_screen.change(self.h - 2, -1, "+", self.editor.theme.get("border", False))
            self.v_screen.change(-1, self.w - 2, "+", self.editor.theme.get("border", False))
            self.v_screen.change(self.h - 2, self.w - 2, "+", self.editor.theme.get("border", False))
            for i in range(self.h - 2):
                self.v_screen.change(i, -1, "|", self.editor.theme.get("border", False))
                self.v_screen.change(i, self.w - 2, "|", self.editor.theme.get("border", False))
            for i in range(self.w - 2):
                self.v_screen.change(-1, i, "-", self.editor.theme.get("border", False))
                self.v_screen.change(self.h - 2, i, "-", self.editor.theme.get("border", False))
            if self.title:
                twidth = min(self.v_screen.w // 2, sum(map(get_width, self.title)))
                tleft = (self.v_screen.w - twidth) // 2
                draw_text(self, self.top, self.v_screen.left + tleft, twidth,
                          self.title, "border", self.get_prio())


class FloatBuffer(FloatWin, KeyHolder):
    def __init__(self, top: int, left: int, h: int, w: int,
                    editor: "Editor", parent: WindowLike | None,
                    features: FloatWinFeatures | None = None):
        KeyHolder.__init__(self)
        FloatWin.__init__(self, top, left, h, w, editor, parent, features)


class ThemeSelector(FloatBuffer):
    def __init__(self, editor: "Editor"):
        super().__init__(0, 0, 10, 10, editor, None)
        self.set_pos()

        self.menu_h = self.h - 2
        self.options = list(themes.keys())
        self.selected = self.options.index(self.editor.theme_name)
        self.scroll = 0
        self.scroll_menu()

        self.keymap = {
            "INSERT": {},
            "NORMAL": {
                "j": self.cursor_down,
                "k": self.cursor_up,
                "<up>": self.cursor_up,
                "<down>": self.cursor_down,
                "<tab>": self.cursor_down,
                "g": {
                    "g": self.cursor_head,
                },
                "G": self.cursor_tail,
                "<pagedown>": self.cursor_pagedown,
                "<pageup>": self.cursor_pageup,
                "<esc>": self.quit,
                "q": self.quit,
                "<cr>": self.quit,
            },
            "VISUAL": {},
            "COMMAND": {},
        }

        self.hide = True
        self.title = "Theme Selector"

    def get_prio(self):
        return 1001

    def quit(self, *_):
        self.hide = True
        for i in reversed(self.editor.winmove_seq):
            if not isinstance(self.editor.win_ids[i], ThemeSelector):
                self.editor.cur = self.editor.win_ids[i]
                return
        cur = self.editor.gwin.find_buffer()
        if cur:
            self.editor.cur = cur
        else:
            self.editor.quit_editor()

    def cursor_up(self, n=1):
        for _ in range(n):
            self.selected -= 1
            if self.selected < 0:
                self.selected = len(self.options) - 1

    def cursor_down(self, n=1):
        for _ in range(n):
            self.selected += 1
            if self.selected >= len(self.options):
                self.selected = 0

    def cursor_pageup(self, n=1):
        self.selected = max(self.selected - n * self.menu_h, 0)

    def cursor_pagedown(self, n=1):
        self.selected = min(self.selected + n * self.menu_h, len(self.options) - 1)

    def cursor_head(self, *_):
        self.selected = 0

    def cursor_tail(self, n=-1):
        if n == -1:
            self.selected = len(self.options) - 1
        else:
            self.selected = max(min(n, self.menu_h), 0)

    def scroll_menu(self):
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected - self.menu_h >= self.scroll:
            self.scroll = self.selected - self.menu_h + 1

    def set_pos(self):
        self.move(self.editor.h // 4, self.editor.w // 4)
        self.resize(self.editor.h // 2, self.editor.w // 2)
        self.menu_h = self.h - 2

    def fill_screen(self):
        self.set_pos()
        self.scroll_menu()
        self.editor.accept_cmd_set_theme(self.options[self.selected])
        for i in range(self.menu_h):
            self.draw_text(i, 0, "" if i >= len(self.options) else self.options[i + self.scroll],
                           "completion_selected" if i + self.scroll == self.selected else "text")

    def draw(self):
        if self.hide:
            return
        self.fill_screen()
        super().draw()


class InputBox(FloatBuffer):
    def insert(self, text: str):
        ...


# 2025-8-8
# 应该是目前看来最复杂的一个FloatWin
# 不过仍然没法跟初期的逆天绘制相比
# 毕竟基础设施都成熟了，经验也积累起来了
class FuzzyFinder(InputBox):
    def __init__(self, editor: "Editor"):
        super().__init__(0, 0, 10, 10, editor, None)
        self.set_pos()

        self.options: list[str] = []
        self.fdentry: FileEntry | None = None
        self.selected = 0
        self.scroll = 0

        self.x = 0
        self.xscroll = 0
        self.input_text = ""

        self.keymap = {
            "INSERT": {
                "<up>": self.select_up,
                "<down>": self.select_down,
                "<tab>": self.select_down,
                "<C-n>": self.select_down,
                "<C-p>": self.select_up,
                "<pageup>": self.select_pageup,
                "<pagedown>": self.select_pagedown,
                "<left>": self.input_left,
                "<right>": self.input_right,
                "<home>": self.input_head,
                "<end>": self.input_tail,
                "<bs>": self.input_backspace,
                "<del>": self.input_delete,
                "<cr>": self.accept,
                "<esc>": self.quit,
            },
            "NORMAL": {},
            "VISUAL": {},
            "COMMAND": {},
        }

        self.refill()
        self.hide = False
        self.title = "Fuzzy Finder"

    def find_cur(self) -> "Buffer | None":
        for i in reversed(self.editor.winmove_seq):
            if isinstance(self.editor.win_ids[i], TextBuffer):
                self.editor.cur = self.editor.win_ids[i]
                return self.editor.win_ids[i]
        return self.editor.gwin.find_buffer()

    def remove_self(self):
        self.editor.floatwins.remove(self)

    def accept(self, *_):
        self.hide = True
        if cur := self.find_cur():
            self.editor.cur = cur
            if isinstance(self.editor.cur, TextBuffer):
                self.editor.cur.goto_entry(self.fdentry)
        else:
            self.editor.quit_editor()
        self.remove_self()

    def quit(self, *_):
        self.hide = True
        if cur := self.find_cur():
            self.editor.cur = cur
        else:
            self.editor.quit_editor()
        self.remove_self()

    def select_up(self, *_):
        self.selected -= 1
        if self.selected < 0:
            self.selected = max(0, len(self.options) - 1)
        self.fill_preview()

    def select_down(self, *_):
        self.selected += 1
        if self.selected >= len(self.options):
            self.selected = 0
        self.fill_preview()

    def select_pageup(self, *_):
        self.selected = max(self.selected - self.menu_h, 0)
        self.fill_preview()

    def select_pagedown(self, *_):
        self.selected = min(self.selected + self.menu_h, len(self.options) - 1)
        self.fill_preview()

    def input_left(self, *_):
        self.x = max(self.x - 1, 0)

    def input_right(self, *_):
        self.x = min(self.x + 1, len(self.input_text))

    def input_head(self, *_):
        self.x = 0

    def input_tail(self, *_):
        self.x = len(self.input_text)

    def input_backspace(self, *_):
        if self.x > 0:
            self.input_text = self.input_text[:self.x - 1] + self.input_text[self.x:]
            self.x -= 1
            self.refill()

    def input_delete(self, *_):
        if self.x < len(self.input_text):
            self.input_text = self.input_text[:self.x] + self.input_text[self.x + 1:]
            self.refill()

    def insert(self, text: str):
        self.input_text = self.input_text[:self.x] + text + self.input_text[self.x:]
        self.x += len(text)
        self.refill()

    # 这个应由子类实现
    # 可恶，都多少层继承了
    def source(self):
        ...

    def fill_preview(self):
        ...

    def refill(self):
        prev_select = self.options[self.selected] if self.options else None
        self.source()
        if prev_select and prev_select in self.options:
            self.selected = self.options.index(prev_select)
        else:
            self.selected = 0
        self.fill_preview()

    def set_pos(self):
        self.move(self.editor.h // 8, self.editor.w // 8)
        self.resize(self.editor.h // 4 * 3, self.editor.w // 4 * 3)
        self.menu_h = self.h - 4
        self.optsw = self.v_screen.w // 3

    def set_scroll(self):
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected - self.menu_h >= self.scroll:
            self.scroll = self.selected - self.menu_h + 1

        if self.x < self.xscroll:
            self.xscroll = self.x
        else:
            inputw = self.optsw - 1
            curw = 0
            i = self.x - 1
            for i in range(self.x - 1, -1, -1):
                iw = get_width(self.input_text[i])
                if curw + iw > inputw:
                    break
                curw += iw
            if i > self.xscroll:
                self.xscroll = i

    def get_prio(self):
        return 1001

    def fill_screen(self):
        self.set_pos()
        self.set_scroll()
        prio = self.get_prio()
        draw_text(
            self, self.v_screen.top, self.v_screen.left, self.optsw,
            self.input_text[self.xscroll:], "text", prio)
        self.editor.screen.set_cursor(
            self.v_screen.top, self.v_screen.left + sum(map(get_width, self.input_text[self.xscroll : self.x])))
        for i in range(self.optsw):
            self.v_screen.change(1, i, "-", self.editor.theme.get("border", False))
        for i in range(self.menu_h):
            draw_text(
                self, self.v_screen.top + i + 2, self.v_screen.left, self.optsw,
                " " + ("" if i + self.scroll >= len(self.options) else self.options[i + self.scroll]),
                "completion_selected" if i + self.scroll == self.selected else "text", prio)
        dleft = self.v_screen.left + self.optsw + 1
        dw = self.v_screen.w - self.optsw - 1
        dh = self.v_screen.h
        if self.fdentry:
            file, (y, _) = self.fdentry
            try:
                with open(file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except:
                lines = ["Unsupported encoding"]
        else:
            file = ""
            y = -1
            lines = []
        dstart = max(0, y - dh // 2) - 1
        dstart = min(dstart, len(lines) - 1)
        self.v_screen.change(0, self.optsw, "|", self.editor.theme.get("border", False))
        draw_text(self, self.v_screen.top, dleft, dw, file, "text", prio, rev=True)
        for i in range(1, dh):
            self.v_screen.change(i, self.optsw, "|", self.editor.theme.get("border", False))
            draw_text(self, self.v_screen.top + i, dleft, dw,
                " " + ("" if dstart + i >= len(lines) else lines[dstart + i].replace("\n", "").replace("\r", "")),
                "completion_selected" if dstart + i == y else "text", prio)

    def draw(self):
        if self.hide:
            return
        self.fill_screen()
        super().draw()


class FuzzyTags(FuzzyFinder):
    def __init__(self, editor):
        super().__init__(editor)
        self.title = "Fuzzy Tags"

    def source(self):
        self.optex = []
        self.options = []
        options = []
        optexs = []
        for tags in self.editor.tags.values():
            for tag in tags:
                options.append(tag["name"])
                optexs.append(tag)
        fuzzy = fuzzy_find(self.input_text, options)
        for i in range(1, fuzzy[0] + 1):
            self.options.append(options[fuzzy[i]])
            self.optex.append(optexs[fuzzy[i]])

    def fill_preview(self):
        if self.optex:
            self.fdentry = tags_navigate(self.optex[self.selected])


class FuzzyFiles(FuzzyFinder):
    def __init__(self, editor):
        super().__init__(editor)
        self.title = "Fuzzy Files"

    def find_files(self, path: str) -> list[str]:
        if '.git' in path:
            return []
        try:
            files = []
            for file in os.listdir(path):
                if os.path.isfile(fullpath := os.path.join(path, file)):
                    files.append(fullpath)
                elif os.path.isdir(fullpath):
                    files.extend(self.find_files(fullpath))
            return files
        except:
            return []

    def source(self):
        self.options = []
        options = self.find_files(os.curdir)
        fuzzy = fuzzy_find(self.input_text, options)
        for i in range(1, fuzzy[0] + 1):
            self.options.append(options[fuzzy[i]])

    def fill_preview(self):
        if self.options:
            self.fdentry = self.options[self.selected], (0, 0)


# 《磁盘密集型》
# 后面也许会搞缓存
class TagSelector(FloatBuffer):
    def __init__(self, editor: "Editor"):
        super().__init__(0, 0, 10, 10, editor, None)
        self.set_pos()

        self.options: list[TagEntry]
        self.selected = 0
        self.scroll = 0

        self.keymap = {
            "INSERT": {},
            "NORMAL": {
                "j": self.cursor_down,
                "k": self.cursor_up,
                "<up>": self.cursor_up,
                "<down>": self.cursor_down,
                "<tab>": self.cursor_down,
                "g": {
                    "g": self.cursor_head,
                },
                "G": self.cursor_tail,
                "<pagedown>": self.cursor_pagedown,
                "<pageup>": self.cursor_pageup,
                "<esc>": self.quit,
                "q": self.quit,
                "<cr>": self.accept,
            },
            "VISUAL": {},
            "COMMAND": {},
        }

        self.hide = True
        self.title = "Tag Selector"

    def get_prio(self):
        return 1001

    def find_cur(self) -> "Buffer | None":
        for i in reversed(self.editor.winmove_seq):
            if isinstance(self.editor.win_ids[i], TextBuffer):
                self.editor.cur = self.editor.win_ids[i]
                return self.editor.win_ids[i]
        return self.editor.gwin.find_buffer()

    def quit(self, *_):
        self.hide = True
        if cur := self.find_cur():
            self.editor.cur = cur
        else:
            self.editor.quit_editor()

    def accept(self, *_):
        self.hide = True
        if cur := self.find_cur():
            self.editor.cur = cur
            if isinstance(self.editor.cur, TextBuffer):
                self.editor.cur.goto_tag(self.options[self.selected])
        else:
            self.editor.quit_editor()

    def cursor_up(self, n=1):
        for _ in range(n):
            self.selected -= 1
            if self.selected < 0:
                self.selected = len(self.options) - 1

    def cursor_down(self, n=1):
        for _ in range(n):
            self.selected += 1
            if self.selected >= len(self.options):
                self.selected = 0

    def cursor_pageup(self, n=1):
        self.selected = max(self.selected - n * self.menu_h, 0)

    def cursor_pagedown(self, n=1):
        self.selected = min(self.selected + n * self.menu_h, len(self.options) - 1)

    def cursor_head(self, *_):
        self.selected = 0

    def cursor_tail(self, n=-1):
        if n == -1:
            self.selected = len(self.options) - 1
        else:
            self.selected = max(min(n, self.menu_h), 0)

    def start(self, options: list[TagEntry]):
        self.options = options
        self.selected = 0
        self.scroll = 0
        self.hide = False

    def scroll_menu(self):
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected - self.menu_h >= self.scroll:
            self.scroll = self.selected - self.menu_h + 1

    def set_pos(self):
        self.move(self.editor.h // 8, self.editor.w // 8)
        self.resize(self.editor.h // 4 * 3, self.editor.w // 4 * 3)
        self.menu_h = self.h - 2

    def fill_screen(self):
        self.set_pos()
        self.scroll_menu()
        optionsw = self.v_screen.w // 3
        for i in range(self.menu_h):
            draw_text(
                self, self.v_screen.top + i, self.v_screen.left, optionsw,
                "" if i >= len(self.options) else f"[{i + self.scroll}]" + self.options[i + self.scroll]["name"],
                "completion_selected" if i + self.scroll == self.selected else "text", self.get_prio())
        dleft = self.v_screen.left + optionsw + 1
        displayw = self.v_screen.w - optionsw - 1
        displayh = self.v_screen.h
        try:
            with open(self.options[self.selected]["path"], "r", encoding="utf-8") as f:
                lines = f.readlines()
            if res := tags_navigate(self.options[self.selected], lines):
                _, (y, _) = res
                dstart = max(0, y - displayh // 2) - 1
                self.v_screen.change(0, optionsw, "|", self.editor.theme.get("border", False))
                draw_text(self, self.v_screen.top, dleft, displayw,
                        self.options[self.selected]["path"], "text", self.get_prio(), rev=True)
                for i in range(1, displayh):
                    self.v_screen.change(i, optionsw, "|", self.editor.theme.get("border", False))
                    draw_text(self, self.v_screen.top + i, dleft, displayw,
                            "" if dstart + i >= len(lines) else lines[dstart + i].replace("\n", "").replace("\r", ""),
                            "completion_selected" if dstart + i == y else "text", self.get_prio())
        except:
            pass

    def draw(self):
        if self.hide:
            return
        self.fill_screen()
        super().draw()


class Window(WindowLike):
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: "tuple[Split, bool] | None"):
        super().__init__()
        self.top, self.left, self.h, self.w = top, left, h, w
        self.editor, self.parent = editor, parent
        self.id = self.editor.alloc_id(self)

    def close(self):
        # del self.editor.win_ids[self.id]
        self.editor.remove_id(self.id)

    def find_buffer(self) -> "Buffer | None":
        ...

    def resize(self, h: int, w: int):
        if h < 10 or w < 20:
            raise WinResizeError()

    def check_resize(self, h: int, w: int) -> bool:
        return h >= 10 and w >= 20

    def resize_bottomup(self, h: int, w: int):
        if not self.check_resize(h, w) or not self.parent:
            raise WinResizeError()
        parent, sp_id = self.parent
        if parent.sp_tp == HSplit:
            if parent.h - h < 10:
                parent.resize_bottomup(h + 10, w)
            if not sp_id:
                parent.change_pos(h, 0)
            else:
                parent.change_pos(parent.h - h, 1)
            if w != parent.w:
                parent.resize_bottomup(parent.h, w)
        else:
            if parent.w - w - 1 < 20:
                parent.resize_bottomup(h, w + 20 + 1)
            if not sp_id:
                parent.change_pos(w + 1, 0)
            else:
                parent.change_pos(parent.w - w, 1)
            if h != parent.h:
                parent.resize_bottomup(h, parent.w)
        # if not isinstance(self, Split):
        #     self.resize(h, w)
        # else:
        #     self.h, self.w = h, w

    # 大道至简啊（
    def find_right(self, h: int) -> "Buffer | None":
        if not self.parent:
            return None
        if self.parent[0].sp_tp == VSplit and self.parent[1] == 0:
            return self.parent[0].win2.find_left_buffer(h)
        return self.parent[0].find_right(h)

    def find_left_buffer(self, h: int) -> "Buffer":
        if isinstance(self, Buffer):
            return self
        assert isinstance(self, Split)
        if self.sp_tp == VSplit:
            return self.win1.find_left_buffer(h)
        if self.sp_pos + self.top <= h:
            return self.win2.find_left_buffer(h)
        return self.win1.find_left_buffer(h)

    def find_left(self, h: int) -> "Buffer | None":
        if not self.parent:
            return None
        if self.parent[0].sp_tp == VSplit and self.parent[1] == 1:
            return self.parent[0].win1.find_right_buffer(h)
        return self.parent[0].find_left(h)

    def find_right_buffer(self, h: int) -> "Buffer":
        if isinstance(self, Buffer):
            return self
        assert isinstance(self, Split)
        if self.sp_tp == VSplit:
            return self.win2.find_right_buffer(h)
        if self.sp_pos + self.top <= h:
            return self.win2.find_right_buffer(h)
        return self.win1.find_right_buffer(h)

    def find_down(self, w: int) -> "Buffer | None":
        if not self.parent:
            return None
        if self.parent[0].sp_tp == HSplit and self.parent[1] == 0:
            return self.parent[0].win2.find_up_buffer(w)
        return self.parent[0].find_down(w)

    def find_up_buffer(self, w: int) -> "Buffer":
        if isinstance(self, Buffer):
            return self
        assert isinstance(self, Split)
        if self.sp_tp == HSplit:
            return self.win1.find_up_buffer(w)
        if self.sp_pos + self.left < w:
            return self.win2.find_up_buffer(w)
        return self.win1.find_up_buffer(w)

    def find_up(self, w: int) -> "Buffer | None":
        if not self.parent:
            return None
        if self.parent[0].sp_tp == HSplit and self.parent[1] == 1:
            return self.parent[0].win1.find_down_buffer(w)
        return self.parent[0].find_up(w)

    def find_down_buffer(self, w: int) -> "Buffer":
        if isinstance(self, Buffer):
            return self
        assert isinstance(self, Split)
        if self.sp_tp == HSplit:
            return self.win2.find_down_buffer(w)
        if self.sp_pos + self.left < w:
            return self.win2.find_down_buffer(w)
        return self.win1.find_down_buffer(w)

    def move(self, top: int, left: int):
        ...

    # 新窗口在右下
    def split(self, sp_tp: bool, buf_tp = None, reserve=-1, *args):
        if self.h < 20 and sp_tp == HSplit or self.w < 41 and sp_tp == VSplit:
            return
        if buf_tp is None:
            buf_tp = TextBuffer
        if sp_tp == HSplit:
            # 2025-8-17
            # 666多长时间了这顺序还是错的
            # 不过好像时间确实不长
            upper_h = self.h // 2 if reserve == -1 else max(reserve, 10)
            new_sp = Split(self.top, self.left, self.h, self.w,
                           self.editor, self.parent, sp_tp, upper_h)
            new_buf = buf_tp(self.top + upper_h, self.left, self.h - upper_h, self.w,
                             self.editor, (new_sp, True), *args)
            self.resize(upper_h, self.w)
        else:
            # log(("split", self.h, self.w, (self.w - 1) // 2))
            left_w = (self.w - 1) // 2 if reserve == -1 else max(reserve, 20)
            new_sp = Split(self.top, self.left, self.h, self.w,
                           self.editor, self.parent, sp_tp, left_w + 1)
            new_w = self.w - left_w - 1
            new_buf = buf_tp(self.top, self.left + left_w + 1, self.h, new_w,
                             self.editor, (new_sp, True), *args)
            self.resize(self.h, left_w)

        new_sp.win1, new_sp.win2 = self, new_buf
        self.parent = new_sp, False
        if new_sp.parent:
            if not new_sp.parent[1]:
                new_sp.parent[0].win1 = new_sp
            else:
                new_sp.parent[0].win2 = new_sp
        else:
            new_sp.editor.gwin = new_sp

    def key_resize_h_add(self, n=1):
        try:
            self.resize_bottomup(self.h + n, self.w)
        except:
            pass

    def key_resize_h_sub(self, n=1):
        try:
            self.resize_bottomup(self.h - n, self.w)
        except:
            pass

    def key_resize_v_add(self, n=1):
        try:
            self.resize_bottomup(self.h, self.w + n)
        except:
            pass

    def key_resize_v_sub(self, n=1):
        try:
            self.resize_bottomup(self.h, self.w - n)
        except:
            pass


class Buffer(Window, KeyHolder):
    def __init__(self, top: int, left: int, h: int, w: int,
                    editor: "Editor", parent: "tuple[Split, bool] | None"):
        KeyHolder.__init__(self)
        Window.__init__(self, top, left, h, w, editor, parent)

    def find_buffer(self) -> "Buffer | None":
        return self

    def resize(self, h: int, w: int):
        Window.resize(self, self.h, self.w)
        self.h, self.w = h, w

    def move(self, top: int, left: int):
        self.left, self.top = left, top


class MenuBuffer(Buffer):
    def __init__(self, top, left, h, w, editor, parent):
        super().__init__(top, left, h, w, editor, parent)
        self.scroll = 0
        self.y = 0
        self.buffer = []

        self.keymap = {
            "INSERT": {},
            "NORMAL": {
                "j": self.cursor_down,
                "k": self.cursor_up,
                "<down>": self.cursor_down,
                "<up>": self.cursor_up,
                "g": {
                    "g": self.cursor_head,
                },
                "G": self.cursor_tail,
                "<pageup>": self.cursor_pageup,
                "<pagedown>": self.cursor_pagedown,
                "o": self.proc_open,
                "<cr>": self.proc_open,
                "<tab>": self.proc_open,

                "<C-up>": self.key_resize_h_sub,
                "<C-down>": self.key_resize_h_add,
                "<C-left>": self.key_resize_v_sub,
                "<C-right>": self.key_resize_v_add,
            },
            "VISUAL": {},
            "COMMAND": {},
        }

    def cursor_real_pos(self) -> tuple[int, int]:
        return self.top + self.y, self.left

    def cursor_up(self, n: int = 1):
        if self.y > 0:
            self.y -= 1

    def cursor_down(self, n: int = 1):
        if self.y < len(self.buffer) - 1:
            self.y += 1

    def cursor_head(self, *_):
        self.y = 0

    def cursor_tail(self, n: int = -1):
        self.y = len(self.buffer) - 1

    def cursor_pageup(self, n: int = 1):
        for _ in range(n):
            self.y = max(0, self.y - self.h + 1)

    def cursor_pagedown(self, n: int = 1):
        for _ in range(n):
            self.y = min(len(self.buffer) - 1, self.y + self.h - 1)

    def proc_open(self):
        ...

    def scroll_buffer(self, y: int):
        if y < self.scroll:
            self.scroll = y
        elif y - self.h + 2 > self.scroll:
            self.scroll = y - self.h + 2


class FileExplorer(MenuBuffer):
    def __init__(self, top, left, h, w, editor, parent, path=None):
        super().__init__(top, left, h, w, editor, parent)
        self.expanded = set()
        if path:
            path = os.path.expanduser(path)
        self.root = os.path.abspath(os.curdir if not path or not os.path.exists(path) or not os.path.isdir(path) else path)
        self.file_tree = self.build_tree(self.root)
        self.scroll = 0
        self.y = 0
        self.buffer = self.gen_buffer(self.file_tree)

        self.bind_key("NORMAL", ["c"], self.proc_change_root)
        self.bind_key("NORMAL", ["p"], self.proc_change_to_parent)
        self.bind_key("NORMAL", ["R"], self.update)
        self.bind_key("NORMAL", ["a"], self.proc_key_add_file)
        self.bind_key("NORMAL", ["d"], self.proc_key_del_file)
        self.cmdmap = {
            "cd": self.change_root,
            "add": self.proc_add_file,
            "del": self.proc_del_file,
            "confirm_delete": self.proc_confirm_del_file,
        }
        self.cmdcmp = {
            "cd": cmdcmp_dirs,
            "add": cmdcmp_files,
            "del": cmdcmp_files,
        }

    def proc_open(self):
        # print("proc_open", self.buffer[self.y + self.scroll])
        if os.path.isdir(self.buffer[self.y + self.scroll][1]):
            if self.buffer[self.y + self.scroll][1] not in self.expanded:
                self.expanded.add(self.buffer[self.y + self.scroll][1])
            else:
                self.expanded.remove(self.buffer[self.y + self.scroll][1])
            self.update()
        else:
            ok = False
            for winid in reversed(self.editor.winmove_seq):
                if isinstance(self.editor.win_ids[winid], FileBase):
                    self.editor.cur = self.editor.win_ids[winid]
                    if isinstance(self.editor.cur, FileBase):
                        self.editor.cur.open_file(self.buffer[self.y + self.scroll][1])
                    ok = True
            if not ok:
                self.split(VSplit, TextBuffer)
                if self.parent and isinstance(self.parent[0].win2, TextBuffer):
                    self.editor.cur = self.parent[0].win2
                if isinstance(self.editor.cur, FileBase):
                    self.editor.cur.open_file(self.buffer[self.y + self.scroll][1])
                self.resize_bottomup(self.h, max(30, self.editor.w // 5))

    def proc_change_root(self):
        self.change_root(self.buffer[self.y + self.scroll][1])

    def proc_change_to_parent(self):
        if os.path.abspath(os.path.join(self.root, os.pardir)) != self.root:
            self.change_root(os.path.abspath(os.path.join(self.root, os.pardir)))

    def proc_key_add_file(self):
        curfile = self.buffer[self.y + self.scroll][1]
        self.editor.mode_command(":add " + os.path.dirname(curfile) + "/")
        self.editor.cmd_pos = len(self.editor.cur_cmd)

    def proc_key_del_file(self):
        curfile = self.buffer[self.y + self.scroll][1]
        if os.path.isdir(curfile):
            curfile += "/"
        self.editor.mode_command(":del " + curfile)
        self.editor.cmd_pos = len(self.editor.cur_cmd)

    def proc_add_file(self, arg: str):
        try:
            if arg.endswith("/"):
                os.makedirs(arg, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(arg), exist_ok=True)
                with open(arg, "w", encoding="utf-8") as f:
                    pass
            self.editor.hook_file_upd(arg)
        except:
            pass
        self.update()

    def proc_del_file(self, arg: str):
        self.editor.mode_command(":confirm_delete " + arg)
        self.editor.cmd_pos = len(self.editor.cur_cmd)

    def proc_confirm_del_file(self, arg: str):
        try:
            if arg.endswith("/") or os.path.isdir(arg):
                shutil.rmtree(arg)
            else:
                os.remove(arg)
            self.editor.hook_file_upd(arg)
        except:
            pass
        self.update()

    def sort_dir(self, path: str):
        dirs = []
        files = []
        for name in sorted(os.listdir(path)):
            full_path = os.path.join(path, name)
            if os.path.isdir(full_path):
                dirs.append(name)
            else:
                files.append(name)
        return dirs + files

    def build_tree(self, path: str):
        tree = []
        for name in self.sort_dir(path):
            full_path = os.path.join(path, name)
            if os.path.isdir(full_path):
                if full_path not in self.expanded:
                    tree.append((name, full_path, None))
                else:
                    tree.append((name, full_path, self.build_tree(full_path)))
            else:
                tree.append((name, full_path))
        return tree

    def gen_buffer(self, tree: list | None, level: int = 0) -> list[str]:
        if tree is None:
            return []
        res = []
        for i in tree:
            if len(i) == 3:
                res.append(('  ' * level + ('~ ' if i[1] in self.expanded else '+ ') + i[0], i[1]))
                res.extend(self.gen_buffer(i[2], level + 1))
            else:
                res.append(('  ' + '  ' * level + i[0], i[1]))
        return res

    def update(self):
        self.file_tree = self.build_tree(self.root)
        self.buffer = self.gen_buffer(self.file_tree)

    def change_root(self, root: str):
        if not os.path.exists(root) or not os.path.isdir(root):
            return
        self.root = os.path.abspath(root)
        self.y = 0
        self.update()

    def draw(self):
        super().draw()
        self.scroll_buffer(self.y)
        if self.buffer:
            for i in range(0, self.h - 1):
                if self.scroll + i < len(self.buffer):
                    draw_text(self, self.top + i, self.left, self.w,
                              self.buffer[self.scroll + i][0],
                              "sel" if i + self.scroll == self.y and self.editor.cur == self else "text",
                              PrioBuffer)
                else:
                    draw_text(self, self.top + i, self.left, self.w,
                              "", "text", PrioBuffer)
        else:
            for i in range(0, self.h - 1):
                draw_text(self, self.top + i, self.left, self.w,
                          "", "sel" if self.editor.cur == self else "text", PrioBuffer)
        draw_text(self, self.top + self.h - 1, self.left, self.w,
                  "Tree: " + self.root, "modeline", PrioBuffer)


class TagBar(MenuBuffer):
    def __init__(self, top, left, h, w, editor, parent):
        super().__init__(top, left, h, w, editor, parent)
        self.scroll = 0
        self.y = 0
        self.file: TextBuffer | None = None
        self.prev_file = None
        self.update_buffer()

    def find_prevbuf(self):
        for winid in reversed(self.editor.winmove_seq):
            if isinstance(self.editor.win_ids[winid], TextBuffer):
                self.file = self.editor.win_ids[winid]
                return
        self.file = None

    def update_buffer(self):
        self.find_prevbuf()
        if not self.file or not self.file.file:
            self.y = 0
            return
        if self.prev_file and os.path.samefile(self.file.file, self.prev_file):
            return
        self.buffer: list[TagEntry] = []
        file = os.path.abspath(self.file.file)
        for _, tags in self.editor.tags.items():
            for tag in tags:
                if os.path.abspath(tag["path"]) == file:
                    self.buffer.append(tag)
        self.buffer.sort(key=lambda x: x["name"])
        if self.y >= len(self.buffer) and len(self.buffer):
            self.y = len(self.buffer) - 1

    def proc_open(self):
        if not self.file:
            return
        self.file.goto_tag(self.buffer[self.y])
        self.editor.cur = self.file

    def draw(self):
        super().draw()
        self.update_buffer()
        self.prev_file = self.file.file if self.file else None
        self.scroll_buffer(self.y)
        for i in range(0, self.h - 1):
            if self.scroll + i < len(self.buffer):
                cur = self.buffer[self.scroll + i]
                draw_text(self, self.top + i, self.left, self.w,
                          "%s%s" % (cur["kind"] + " " if "kind" in cur else "", cur["name"]),
                          "sel" if i + self.scroll == self.y and self.editor.cur == self else "text",
                          PrioBuffer)
            else:
                draw_text(self, self.top + i, self.left, self.w,
                          "", "text", PrioBuffer)
        draw_text(self, self.top + self.h - 1, self.left, self.w,
                  "TagBar: " + self.file.file if self.file and self.file.file else "TagBar",
                  "modeline", PrioBuffer)


@dataclass
class TextBufferSettings:
    linum: bool = True
    tab_width: int = 4
    expand_tab: bool = True


class TextBuffer(Buffer, FileBase):
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: "tuple[Split, bool] | None"):
        Buffer.__init__(self, top, left, h, w, editor, parent)
        FileBase.__init__(self, editor)
        self.prio = PrioBuffer
        self.file: str | None = None
        self.drawer = Drawer(editor.screen, self.text, self.left, self.top,
                             self.h - 1, self.w, editor, DrawerSettings(), self.prio)

        # 2025-4-30
        # 仅实验性功能，不确定是否长期保留
        # 但确实好写，所以先写了（
        # 2025-7-21
        # 前端改用FloatWin实现
        self.cmp_menu: list[str] = []
        self.cmp_func: list[Callable] = []
        self.cmp_select = -1
        self.cmp_scroll = 0
        self.cmp_maxshow = 10
        self.cmp_maxwidth = 50
        self.cmp_minwidth = 10
        self.cmp_border = False
        self.cmp_win = FloatWin(0, 0, self.cmp_maxshow + self.cmp_border * 2, self.cmp_maxwidth + self.cmp_border * 2,
                                self.editor, self, FloatWinFeatures(border=self.cmp_border))
        self.floatwins.append(self.cmp_win)

        self.read_callback: Callable | None = None

        self.keymap = {
            "INSERT": {
                "<esc>": self.mode_normal,

                "<up>": self.cursor_up,
                "<down>": self.cursor_down,
                "<left>": self.cursor_left,
                "<right>": self.cursor_right,
                "<pageup>": self.cursor_pageup,
                "<pagedown>": self.cursor_pagedown,
                "<home>": self.cursor_home,
                "<end>": self.cursor_end,

                "<bs>": self.del_before_cursor,
                "<tab>": self.key_tab,
                "<cr>": self.key_enter,
                "<space>": lambda *_: self.insert(" "),

                "<C-n>": self.cmp_select_next,
                "<C-p>": self.cmp_select_prev,
                "<C-y>": self.cmp_menu_accept,

                "<C-h>": self.del_before_cursor,
                "<C-w>": self.del_word_before_cursor,
            },
            "NORMAL": {
                "K": self.debug_inspect,

                "i": self.mode_insert,
                "v": self.mode_select,

                "<C-up>": self.key_resize_h_sub,
                "<C-down>": self.key_resize_h_add,
                "<C-left>": self.key_resize_v_sub,
                "<C-right>": self.key_resize_v_add,

                "a": self.key_normal_a,
                "A": self.key_normal_A,
                "I": self.key_normal_I,
                "o": self.key_normal_o,
                "O": self.key_normal_O,
                "s": self.key_normal_s,
                "S": self.key_normal_S,

                "x": self.key_normal_x,
                "D": self.key_normal_D,
                "C": self.key_normal_C,

                "P": self.paste_before_cursor,
                "p": self.paste_after_cursor,
                "u": self.undo,
                "<C-r>": self.redo,

                "h": self.cursor_left,
                "j": self.cursor_down,
                "k": self.cursor_up,
                "l": self.cursor_right,
                "<up>": self.cursor_up,
                "<down>": self.cursor_down,
                "<left>": self.cursor_left,
                "<right>": self.cursor_right,
                "<pageup>": self.cursor_pageup,
                "<pagedown>": self.cursor_pagedown,
                "<home>": self.cursor_home,
                "<end>": self.cursor_end,
                "0": self.cursor_home,
                "$": self.cursor_end,
                "^": self.cursor_start,
                "g": {
                    "g": self.cursor_head,
                },
                "G": self.cursor_tail,
                "w": self.cursor_next_word,
                "e": self.cursor_next_word_end,
                "b": self.cursor_prev_word,
                "<space>": self.cursor_next_char,
                "<bs>": self.cursor_prev_char,
                "f": self.cursor_fnxt_char,
                "F": self.cursor_fprv_char,
                "n": self.find_next,
                "N": self.find_prev,
                "%": self.goto_match,
                "{": self.cursor_prev_paragragh,
                "}": self.cursor_next_paragragh,
                "(": self.cursor_prev_paragragh,
                ")": self.cursor_next_paragragh,

                # "d": self.merge_dict(self.gen_readpos_keymap(self.delete_to, self.delete_in), {
                #     "d": lambda *n: self.key_del_line(*n),
                # }),
                # "c": self.gen_readpos_keymap(self.change_to, self.change_in),
                # "y": self.merge_dict(self.gen_readpos_keymap(self.yank_to, self.yank_in), {
                #     "y": lambda *n: self.key_yank_line(*n),
                # }),

                "d": KeyWrapper(self.delete_in, self.gen_wrapper_keymap({
                    "d": self.get_range_cur_line,
                })),
                "c": KeyWrapper(self.change_in, self.gen_wrapper_keymap({})),
                "y": KeyWrapper(self.yank_in, self.gen_wrapper_keymap({
                    "y": self.get_range_cur_line,
                })),

                "<C-]>": self.goto_tagfind,
            },
            "VISUAL": {
                "<esc>": self.mode_normal,

                "y": self.select_yank,
                "c": self.select_cut,
                "d": self.select_del,
                "x": self.select_del,
                "s": self.select_del,

                "h": self.cursor_left,
                "j": self.cursor_down,
                "k": self.cursor_up,
                "l": self.cursor_right,
                "<up>": self.cursor_up,
                "<down>": self.cursor_down,
                "<left>": self.cursor_left,
                "<right>": self.cursor_right,
                "<pageup>": self.cursor_pageup,
                "<pagedown>": self.cursor_pagedown,
                "<home>": self.cursor_home,
                "<end>": self.cursor_end,
                "0": self.cursor_home,
                "$": self.cursor_end,
                "^": self.cursor_start,
                "g": {
                    "g": self.cursor_head,
                },
                "G": self.cursor_tail,
                "w": self.cursor_next_word,
                "b": self.cursor_prev_word,
                "<space>": self.cursor_next_char,
                "<bs>": self.cursor_prev_char,
                "f": self.cursor_fnxt_char,
                "F": self.cursor_fprv_char,
                "n": self.find_next,
                "N": self.find_prev,
                "%": self.goto_match,
                "{": self.cursor_prev_paragragh,
                "}": self.cursor_next_paragragh,
                "(": self.cursor_prev_paragragh,
                ")": self.cursor_next_paragragh,

                "i": {
                    "w": lambda *n: self.select_in(self.get_range_cur_word, *n),
                    "p": lambda *n: self.select_in(lambda: self.get_range_paragraph(True), *n),
                    "(": lambda *n: self.select_in(lambda: self.get_range_match("(", True), *n),
                    "[": lambda *n: self.select_in(lambda: self.get_range_match("[", True), *n),
                    "{": lambda *n: self.select_in(lambda: self.get_range_match("{", True), *n),
                    "<": lambda *n: self.select_in(lambda: self.get_range_match("<", True), *n),
                },
                "a": {
                    "w": lambda *n: self.select_in(self.get_range_cur_word, *n),
                    "p": lambda *n: self.select_in(lambda: self.get_range_paragraph(), *n),
                    "(": lambda *n: self.select_in(lambda: self.get_range_match("("), *n),
                    "[": lambda *n: self.select_in(lambda: self.get_range_match("["), *n),
                    "{": lambda *n: self.select_in(lambda: self.get_range_match("{"), *n),
                    "<": lambda *n: self.select_in(lambda: self.get_range_match("<"), *n),
                },
            },
            "COMMAND": {
            },
        }
        self.cmdmap = {
            "o": self.open_file,
            "o!": lambda *n: self.open_file(*n, force=True),
            "e": self.open_file,
            "e!": lambda *n: self.open_file(*n, force=True),
            "w": self.save_file,
            "f": self.start_find,
            "s": self.start_substitute,
            "tag": self.tags_find,
        }
        self.cmdcmp = {
            "o": cmdcmp_files,
            "o!": cmdcmp_files,
            "e": cmdcmp_files,
            "e!": cmdcmp_files,
            "w": cmdcmp_files,
        }

        self.settings = TextBufferSettings()

    def init_settings(self):
        self.settings = TextBufferSettings()
        if self.file:
            ft = get_filetype(self.file)
            if ft in ('c', 'cpp', 'json'):
                self.settings.tab_width = 2
            elif ft in ('make'):
                self.settings.expand_tab = False

        self.update_settings()

    def update_settings(self):
        self.drawer.update_settings(DrawerSettings(self.settings.linum, self.settings.tab_width))

    def debug_inspect(self, *n):
        try:
            gotoxy(self.editor.h, 1)
            print(self.renderer.get(self.y, self.x), end=" ")
        except:
            pass

    def close(self):
        super().close()
        if self.file:
            self.editor.fb_maps[os.path.abspath(self.file)].remove(self)
        # 2025-4-20 要干什么来着？
        # 这里貌似没有什么要改的了
        # 2025-8-18
        # 想起来了，是保存检查，不过可以在caller那里做

    # 主打的就是一个多范式（
    def gen_readpos_to_fn(self, fn: Callable):
        return lambda *n: self.read_callback and self.read_callback(self.gen_rangeto_fn(fn, *n))

    def gen_readpos_in_fn(self, fn: Callable):
        return lambda *n: self.read_callback and self.read_callback(lambda: fn(*n))

    # 有副作用
    def merge_dict(self, k1: dict, k2: dict):
        for k, v in k2.items():
            if k in k1:
                if isinstance(v, dict) and isinstance(k1[k], dict):
                    k1[k] = self.merge_dict(k1[k], v)
                else:
                    k1[k] = v
            else:
                k1[k] = v
        return k1

    def gen_wrapper_keymap(self, to_merge: dict):
        keymap = {
            "h": self.gen_rangeto_fn(self.cursor_left),
            "l": self.gen_rangeto_fn(self.cursor_right),
            "k": self.gen_rangeto_fn(self.cursor_up),
            "j": self.gen_rangeto_fn(self.cursor_down),
            "<up>": self.gen_rangeto_fn(self.cursor_up),
            "<down>": self.gen_rangeto_fn(self.cursor_down),
            "<left>": self.gen_rangeto_fn(self.cursor_left),
            "<right>": self.gen_rangeto_fn(self.cursor_right),
            "<pageup>": self.gen_rangeto_fn(self.cursor_pageup),
            "<pagedown>": self.gen_rangeto_fn(self.cursor_pagedown),
            "<home>": self.gen_rangeto_fn(self.cursor_home),
            "<end>": self.gen_rangeto_fn(self.cursor_end),
            "w": self.gen_rangeto_fn(self.cursor_next_word_end),
            "e": self.gen_rangeto_fn(self.cursor_next_word_end),
            "b": self.gen_rangeto_fn(self.cursor_prev_word),
            "g": {
                "g": self.gen_rangeto_fn(self.cursor_head),
            },
            "G": self.gen_rangeto_fn(self.cursor_tail),
            "0": self.gen_rangeto_fn(self.cursor_head),
            "$": self.gen_rangeto_fn(self.cursor_tail),
            "^": self.gen_rangeto_fn(self.cursor_start),
            " ": self.gen_rangeto_fn(self.cursor_next_char),
            "<bs>": self.gen_rangeto_fn(self.cursor_prev_char),
            "f": self.gen_rangeto_fn(self.cursor_fnxt_char),
            "F": self.gen_rangeto_fn(self.cursor_fprv_char),
            "n": self.gen_rangeto_fn(self.find_next),
            "N": self.gen_rangeto_fn(self.find_prev),
            "%": self.gen_rangeto_fn(self.goto_match),
            "{": self.gen_rangeto_fn(self.cursor_prev_paragragh),
            "}": self.gen_rangeto_fn(self.cursor_next_paragragh),
            "(": self.gen_rangeto_fn(self.cursor_prev_paragragh),
            ")": self.gen_rangeto_fn(self.cursor_next_paragragh),

            "i": {
                "w": lambda *_: self.get_range_cur_word(),
                "(": lambda *_: self.get_range_match("(", True),
                "[": lambda *_: self.get_range_match("[", True),
                "{": lambda *_: self.get_range_match("{", True),
                "<": lambda *_: self.get_range_match("<", True),
            },
            "a": {
                "w": lambda *_: self.get_range_cur_word(),
                "(": lambda *_: self.get_range_match("("),
                "[": lambda *_: self.get_range_match("["),
                "{": lambda *_: self.get_range_match("{"),
                "<": lambda *_: self.get_range_match("<"),
            },
        }
        keymap = self.merge_dict(keymap, to_merge)
        return keymap

    def reset_drawer(self):
        self.drawer.text = self.textinputer.text

    def reset_scroll(self):
        self.drawer.scry = 0

    def mode_select(self, *_):
        self.mode = "VISUAL"
        self.editor.mode = None
        self.sely, self.selx = self.y, self.x

    def mode_normal(self, *_):
        self.mode = "NORMAL"
        self.editor.mode = None

    def mode_insert(self, *_):
        self.mode = "INSERT"
        self.editor.mode = None

    def key_enter(self, *_):
        if self.cmp_menu:
            self.cmp_menu_accept()
        else:
            self.proc_indentcmd(self.renderer.get_indent(self.y, self.x))

    def key_tab(self, *_):
        if self.cmp_menu:
            self.cmp_select_next()
        else:
            self.insert_tab()

    def insert_tab(self, *_):
        self.y, self.x = self.textinputer.insert(self.y, self.x,
                                                 " " * self.settings.tab_width if self.settings.expand_tab else "\t")
        self.ideal_x = self.x

    def cursor_pageup(self, n: int = 1):
        for _ in range(n):
            self.y, _ = self.drawer.scroll_up(
                self.y,
                self.drawer.get_line_hw(self.text[self.y][: self.x])[0] - 1,
                self.h - 2,
            )
            if self.y < 0:
                self.y = 0
        self.x = min(len(self.text[self.y]), self.ideal_x)

    def goto_entry(self, entry: FileEntry | None):
        if not entry:
            return
        file, (y, x) = entry
        self.open_file(file)
        if self.file and os.path.abspath(self.file) == os.path.abspath(file):
            self.y = y
            self.x = self.ideal_x = x

    def goto_tag(self, tag: TagEntry):
        if entry := tags_navigate(tag):
            self.goto_entry(entry)

    def tags_find(self, tag: str):
        # print(self.editor.tagsfile, self.editor.tags)
        if tag in self.editor.tags:
            if len(self.editor.tags[tag]) > 1:
                self.editor.start_tagselect(self.editor.tags[tag])
            else:
                self.goto_tag(self.editor.tags[tag][0])

    def goto_tagfind(self, *_):
        cur_range = self.get_range_cur_word()
        if cur_range:
            (y, x), (q, p) = cur_range
            text = self.textinputer.get(y, x, q, p)
            self.tags_find(text)

    def cursor_pagedown(self, n: int = 1):
        for _ in range(n):
            self.y, _ = self.drawer.scroll_down(
                self.y,
                self.drawer.get_line_hw(self.text[self.y][: self.x])[0] - 1,
                self.h - 2,
            )
            if self.y >= len(self.text):
                self.y = len(self.text) - 1
        self.x = min(len(self.text[self.y]), self.ideal_x)

    def cmp_select_next(self):
        if self.cmp_select == len(self.cmp_menu) - 1:
            self.cmp_select = -1
        else:
            self.cmp_select += 1

    def cmp_select_prev(self):
        if self.cmp_select == -1:
            self.cmp_select = len(self.cmp_menu) - 1
        else:
            self.cmp_select -= 1

    def cmp_menu_update(self, menu: list[str], func: list[Callable]):
        if self.cmp_select == -1 or self.cmp_menu[self.cmp_select] not in menu:
            self.cmp_select = -1
        else:
            self.cmp_select = menu.index(self.cmp_menu[self.cmp_select])
        self.cmp_func = func
        self.cmp_menu = menu

    def clear_cmp_menu(self):
        self.cmp_menu = []
        self.cmp_func = []
        self.cmp_select = -1

    def cmp_menu_accept(self):
        if self.cmp_menu:
            self.cmp_func[max(0, self.cmp_select)]()
            self.clear_cmp_menu()

    def fill_cmp_menu(self):
        use_fuzzy = True
        menu = []
        func = []
        cw_range = self.get_range_last_word()
        if cw_range:
            cur_word = self.textinputer.get(*cw_range[0], *cw_range[1])
            if get_char_type(cur_word[0]) != 1:
                self.cmp_menu_update(menu, func)
                return
            if not use_fuzzy:
                for i in sorted(self.get_all_words()):
                    if i[:len(cur_word)] == cur_word and len(i) > len(cur_word):
                        menu.append(i)
                        func.append(self.gen_cmp_func(i))
            else:
                words = list(self.get_all_words())
                fuzzy_words = fuzzy_find(cur_word, words)
                for i in range(1, fuzzy_words[0] + 1):
                    if (word := words[fuzzy_words[i]]) != cur_word:
                        menu.append(word)
                        func.append(self.gen_cmp_func(word))
        self.cmp_menu_update(menu, func)

    def get_all_words(self):
        words = set()
        for ln in self.text:
            cur = ""
            for i in ln:
                tp = get_char_type(i)
                if tp == 1:
                    cur += i
                if tp != 1 and cur:
                    words.add(cur)
                    cur = ""
            if cur:
                words.add(cur)
        return words

    def gen_cmp_func(self, text: str):
        return lambda: self.replace(text, self.get_range_last_word())

    def resize(self, h: int, w: int):
        Window.resize(self, h, w)
        self.h, self.w = h, w
        self.drawer.update_size(self.h - 1, self.w)

    def check_resize(self, h: int, w: int):
        return h >= 10 and w >= 20

    def move(self, top: int, left: int):
        self.top, self.left = top, left
        self.drawer.move(self.top, self.left)

    def find_buffer(self) -> "Buffer | None":
        return self

    def get_menu_height(self) -> tuple[int, bool]:
        need_h = min(self.cmp_maxshow, len(self.cmp_menu)) + self.cmp_border
        real_h = self.cursor_real_pos()[0]
        if self.editor.h - real_h - 1 < need_h and real_h > self.editor.h - real_h - 1:
            return min(need_h - self.cmp_border, real_h), True
        return min(need_h - self.cmp_border, self.editor.h - real_h - 1), False

    def set_menu_scroll(self, menu_h: int):
        cmp_select = max(self.cmp_select, 0)
        if cmp_select + 1 > self.cmp_scroll + menu_h:
            self.cmp_scroll = cmp_select + 1 - menu_h
        if cmp_select < self.cmp_scroll:
            self.cmp_scroll = cmp_select

    def cursor_real_pos(self):
        self.drawer.scroll_buffer(self.y, self.x)
        cursor = self.drawer.draw_cursor(self.y, self.x)
        return cursor[0] + self.top, cursor[1] + self.left

    def draw(self):
        self.drawer.scroll_buffer(self.y, self.x)
        if not self.editor.mode and self.mode == "VISUAL":
            if (self.y, self.x) < (self.sely, self.selx):
                self.drawer.draw(self.renderer, self.y, (self.y, self.x), (self.sely, self.selx))
            else:
                self.drawer.draw(self.renderer, self.y, (self.sely, self.selx), (self.y, self.x))
        else:
            self.drawer.draw(self.renderer, self.y)
        cursor_real_pos = self.cursor_real_pos()
        if self.editor.cur == self and self.editor.mode != "COMMAND":
            self.editor.screen.set_cursor(*cursor_real_pos)

        if self.file:
            file = self.file
        else:
            file = "untitled"
        saved = self.textinputer.is_saved()
        file = f"{'[+]' if not saved else ''} {file}"
        if sum(map(get_width, file)) > self.w:
            if get_width(file[-1]) >= 2:
                file = file[:self.w - 1] + ".."
            else:
                file = file[:self.w - 2] + ".."
        modeline = file
        draw_text(self, self.top + self.h - 1, self.left, self.w, modeline, "modeline", PrioBuffer)

        if self.cmp_menu and self.editor.cur == self and self.editor.get_mode() == "INSERT":
            menu_h, menu_dir = self.get_menu_height()
            self.set_menu_scroll(menu_h)
            # 这很省行数了（
            menu_w = max(self.cmp_minwidth, min(self.cmp_maxwidth,
                         max(map(lambda x: sum(map(get_width, x)), self.cmp_menu))))
            if cursor_real_pos[1] + menu_w + 1 > self.editor.w:
                menu_left = self.editor.w - menu_w
            else:
                menu_left = cursor_real_pos[1] + 1
            if menu_dir:  # 光标之上
                self.cmp_win.move(cursor_real_pos[0] - menu_h, menu_left)
            # r = range(cursor_real_pos[0] - menu_h, cursor_real_pos[0])
                # start = cursor_real_pos[0] - menu_h
            else:         # 光标之下
                self.cmp_win.move(cursor_real_pos[0] + 1, menu_left)
                # r = range(cursor_real_pos[0] + 1, cursor_real_pos[0] + 1 + menu_h)
                # start = cursor_real_pos[0] + 1
            self.cmp_win.resize(menu_h + self.cmp_border * 2, menu_w + self.cmp_border * 2)
            # for ln in r:
            #     draw_text(self, ln, menu_left, menu_w,
            #               self.cmp_menu[ln - start + self.cmp_scroll],
            #               "completion" if ln - start + self.cmp_scroll != self.cmp_select else 'completion_selected',
            #               self.prio + 1)
            for i in range(menu_h):
                self.cmp_win.draw_text(i, 0,
                                       self.cmp_menu[i + self.cmp_scroll] if i + self.cmp_scroll < len(self.cmp_menu) else "",
                                       "completion" if i + self.cmp_scroll != self.cmp_select else 'completion_selected')
            self.cmp_win.hide = False
        else:
            self.cmp_win.hide = True

        # self.editor.debug_points.extend([(self.top, self.left),
        #                                  (self.top + self.h - 1, self.left + self.w - 1)])

        Buffer.draw(self)


# Debug神器
# 2025-4-22
# 禁用非Buffer/Split窗口
class deprecated_TextWindow(Window):
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: "tuple[Split, bool] | None",
                 name: str):
        super().__init__(top, left, h, w, editor, parent)
        self.name = name
        self.text = [""]
        self.renderer = get_renderer()(self, self.text)
        self.drawer = Drawer(editor.screen, self.text, self.left, self.top,
                             self.h - 1, self.w, editor, DrawerSettings(), 0)

    def add_log(self, s: str):
        self.text.insert(len(self.text) - 1, s)

    def find_buffer(self) -> "Buffer | None":
        return None

    def resize(self, h: int, w: int):
        super().resize(h, w)
        self.h, self.w = h, w
        self.drawer.update_size(self.h - 1, self.w)

    def move(self, top: int, left: int):
        self.top, self.left = top, left
        self.drawer.move(self.top, self.left)

    def draw(self):
        self.drawer.scroll_buffer(0, 0)
        self.drawer.draw(self.renderer, -1)

        modeline = self.name[: self.w]
        shw = 0
        for ch in modeline:
            self.editor.screen.change(self.top + self.h - 1, self.left + shw, ch,
                                      self.editor.theme.get("modeline", False))
            shw += get_width(ch)
        while shw < self.w:
            self.editor.screen.change(self.top + self.h - 1, self.left + shw, " ",
                                      self.editor.theme.get("modeline", False))
            shw += 1

def TextWindow(*_):
    raise EditorDeprecatedError("TextWindow")


class Split(Window):
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: "tuple[Split, bool] | None",
                 sp_tp: bool, sp_pos: int):
        super().__init__(top, left, h, w, editor, parent)
        self.sp_tp, self.sp_pos = sp_tp, sp_pos
        self.win1: Window
        self.win2: Window

    def revert(self):
        # self.win1.resize(*win2size)
        # self.win2.resize(*win1size)
        self.sp_pos = self.win2.h if self.sp_tp == HSplit else self.win2.w + 1
        self.win1.parent = self, True
        self.win2.parent = self, False
        self.win1, self.win2 = self.win2, self.win1
        if self.sp_tp == HSplit:
            self.win1.move(self.top, self.left)
            self.win2.move(self.top + self.sp_pos, self.left)
        else:
            self.win1.move(self.top, self.left)
            self.win2.move(self.top, self.left + self.sp_pos)

    def change_pos(self, pos: int, ignore_id=-1):
        if self.sp_tp == VSplit:
            if self.h < 10 or pos < 20 or self.w - pos < 20:
                raise WinResizeError()
            if ignore_id != 0:
                self.win1.resize(self.h, pos - 1)
            else:
                self.win1.h, self.win1.w = self.h, pos - 1
            if ignore_id != 1:
                self.win2.resize(self.h, self.w - pos)
            else:
                self.win2.h, self.win2.w = self.h, self.w - pos
            self.win2.move(self.top, self.left + pos)
        else:
            if pos < 10 or self.h - pos < 10 or self.w < 20:
                raise WinResizeError()
            if ignore_id != 0:
                self.win1.resize(pos, self.w)
            else:
                self.win1.h, self.win1.w = pos, self.w
            if ignore_id != 1:
                self.win2.resize(self.h - pos, self.w)
            else:
                self.win2.h, self.win2.w = self.h - pos, self.w
            self.win2.move(self.top + pos, self.left)
        self.sp_pos = pos

    def find_buffer(self) -> "Buffer | None":
        if (buf := self.win1.find_buffer()):
            return buf
        return self.win2.find_buffer()

    def resize(self, h: int, w: int):
        super().resize(h, w)
        if self.sp_tp == HSplit:
            upper_h = max(10, self.sp_pos * h // self.h)
            if upper_h < 10 or h - upper_h < 10 or w < 20:
                raise WinResizeError()
            self.win1.resize(upper_h, w)
            self.win2.resize(h - upper_h, w)
            self.win2.move(self.top + upper_h, self.left)
            self.sp_pos = upper_h
        else:
            left_w = max(20, (self.sp_pos - 1) * w // self.w)
            if h < 10 or left_w < 20 or w - left_w - 1 < 20:
                raise WinResizeError()
            self.win1.resize(h, left_w)
            self.win2.resize(h, w - left_w - 1)
            self.win2.move(self.top, self.left + left_w + 1)
            self.sp_pos = left_w + 1
        self.h, self.w = h, w

    def check_resize(self, h: int, w: int) -> bool:
        if self.sp_tp == HSplit:
            upper_h = max(10, self.sp_pos * h // self.h)
            return (h >= 20 and w >= 20
                    and self.win1.check_resize(upper_h, w)
                    and self.win2.check_resize(h - upper_h, w))
        else:
            left_w = max(20, (self.sp_pos - 1) * w // self.w)
            return (h >= 10 and left_w >= 20
                    and self.win1.check_resize(h, left_w)
                    and self.win2.check_resize(h, w - left_w - 1))

    def move(self, top: int, left: int):
        self.win1.move(top, left)
        if self.sp_tp == HSplit:
            self.win2.move(top + self.sp_pos, left)
        else:
            self.win2.move(top, left + self.sp_pos)
        self.top, self.left = top, left

    def draw(self):
        super().draw()
        self.win1.draw()
        self.win2.draw()
        if self.sp_tp == VSplit:
            for i in range(self.top, self.top + self.h):
                self.editor.screen.change(i, self.left + self.sp_pos - 1, "|",
                                          self.editor.theme.get("text", False))


class KeyWrapper:
    def __init__(self, fn: Callable, keymap: dict):
        self.fn = fn
        self.keymap = keymap


# 写个简单的状态机还是很简单的
class KeyReader:
    def __init__(self, editor: "Editor"):
        self.editor = editor
        self.nrep = -1
        self.k = self.ck = None
        self.key_seq = []
        self.wrappers: list[tuple[Callable, int]] = []
        self.subkey: dict | None = None

    def _pack_fn(self, fn: Callable, res: Callable, *args):
        return lambda *n: fn(lambda: res(*args), *n)

    def get_wrapped(self, fn: Callable, nrep: int):
        res = fn
        for fn, cur_nrep in self.wrappers:
            if nrep != -1:
                res = self._pack_fn(fn, res, nrep)
            else:
                res = self._pack_fn(fn, res)
            nrep = cur_nrep
        return nrep, res

    def read_key(self, key: str):
        self.key_seq.append(key)
        mode = self.editor.get_mode()
        if mode not in ("COMMAND", "INSERT") and len(key) == 1 and key.isdigit() and (key != '0' or self.nrep != -1):
            if self.nrep != -1:
                self.nrep *= 10
                self.nrep += int(key)
            else:
                self.nrep = int(key)
            return

        if self.wrappers:
            if key in self.subkey:  # type: ignore
                self.subkey = self.subkey[key]  # type: ignore
            else:
                self.subkey = None
                self.wrappers = []
        elif not self.k and not self.ck:
            if key in self.editor.keymap[mode]:
                self.k = self.editor.keymap[mode][key]
            if key in self.editor.cur.keymap[mode]:
                self.ck = self.editor.cur.keymap[mode][key]
        else:
            if isinstance(self.k, dict):
                if key in self.k:
                    self.k = self.k[key]
                else:
                    self.k = None
            if isinstance(self.ck, dict):
                if key in self.ck:
                    self.ck = self.ck[key]
                else:
                    self.ck = None

        # 我说白了，能跑就不要动
        # 不过确实堆成答辩了
        if self.wrappers:
            if callable(self.subkey) or isinstance(self.subkey, KeyWrapper):
                nrep, self.nrep = self.nrep, -1
                subkey, self.subkey = self.subkey, None
                if isinstance(subkey, KeyWrapper):
                    self.wrappers.append((subkey.fn, nrep))
                    self.subkey = subkey.keymap
                    return
                key_seq, self.key_seq = self.key_seq, []
                wrapped = self.get_wrapped(subkey, nrep)
                self.wrappers = []
                return *wrapped, key_seq
            elif not isinstance(self.subkey, dict):
                self.subkey = None
                self.wrappers = []
                self.k = self.ck = None
                self.nrep = -1
                key_seq, self.key_seq = self.key_seq, []
                return key_seq
        else:
            if callable(self.k) or isinstance(self.k, KeyWrapper):
                nrep, self.nrep = self.nrep, -1
                k, self.k = self.k, None
                self.ck = None
                if isinstance(k, KeyWrapper):
                    self.wrappers.append((k.fn, nrep))
                    self.subkey = k.keymap
                    return
                key_seq, self.key_seq = self.key_seq, []
                return nrep, k, key_seq
            elif not isinstance(self.k, dict):
                self.k = None
            if callable(self.ck) or isinstance(self.ck, KeyWrapper):
                nrep, self.nrep = self.nrep, -1
                ck, self.ck = self.ck, None
                self.k = None
                if isinstance(ck, KeyWrapper):
                    self.wrappers.append((ck.fn, nrep))
                    self.subkey = ck.keymap
                    return
                key_seq, self.key_seq = self.key_seq, []
                return nrep, ck, key_seq
            elif not isinstance(self.ck, dict):
                self.ck = None
            if not self.k and not self.ck:
                key_seq, self.key_seq = self.key_seq, []
                self.nrep = -1
                return key_seq


class Editor:
    def __init__(self, h: int, w: int):
        self.win_ids = {}
        self.fb_maps: dict[str, set[FileBase]] = {}
        self.h, self.w = h, w
        self.screen = Screen(self.h, self.w)
        self.theme_name = "Tokyo Night Storm"
        self.theme = Theme(themes[self.theme_name])
        self.linum = True
        self.cur: KeyHolder = TextBuffer(0, 0, self.h - 1, self.w, self, None)
        self.gwin: Window = self.cur
        self.running = False
        self.cur_key: str = ""
        self.reader_queue = Queue()
        self.reader = tr.Thread(target=getch_process, args=(self.reader_queue,), daemon=True)
        self.keyreader = KeyReader(self)
        # self.getch_thread = Thread(target=self.getch, args=(), daemon=True)

        # 记得手动注册<cr> <tab> <space>
        self.keymap = {
            "INSERT": {
            },
            "NORMAL": {
                ":": lambda *_: self.mode_command(":"),

                ";": {
                    "h": self.key_winmove_left,
                    "l": self.key_winmove_right,
                    "k": self.key_winmove_up,
                    "j": self.key_winmove_down,
                    "s": {
                        "t": self.accept_cmd_selectheme,
                    },
                    "f": {
                        "t": self.accept_cmd_fuzzytags,
                        "f": self.accept_cmd_fuzzyfiles,
                    },
                },
            },
            "VISUAL": {
            },
            "COMMAND": {
                "<esc>": self.mode_normal,

                "<left>": self.cmd_cursor_left,
                "<right>": self.cmd_cursor_right,
                "<home>": self.cmd_cursor_home,
                "<end>": self.cmd_cursor_end,
                "<C-p>": self.cmd_select_prev,
                "<C-n>": self.cmd_select_next,
                "<tab>": self.cmd_select_next,
                "<C-y>": self.cmd_select_accept,

                "<cr>": self.accept_cmd,
                "<bs>": self.cmd_backspace,
                "<space>": lambda *_: self.cmd_insert(" "),
            },
        }
        self.cmdmap = {
            "q": lambda *args: self.accept_cmd_close_window(False, *args),
            "q!": lambda *args: self.accept_cmd_close_window(True, *args),
            "qa": self.quit_editor_checked,
            "qa!": self.quit_editor,
            "sp": self.accept_cmd_hsplit,
            "vsp": self.accept_cmd_vsplit,
            "sg": self.accept_cmd_goto_by_id,
            "wh": self.accept_cmd_resize_h,
            "ww": self.accept_cmd_resize_w,
            "tree": self.open_explorer,
            "theme": self.accept_cmd_set_theme,
            "selectheme": self.accept_cmd_selectheme,
            "addtags": self.accept_cmd_add_tags,
            "cleartags": self.accept_cmd_clear_tags,
            "tagbar": self.accept_cmd_tagbar,
            "reloadtags": self.accept_cmd_reload_tags,
            "system": self.accept_cmd_system,
        }
        self.cmdcmp = {
            "sp": cmdcmp_files,
            "vsp": cmdcmp_files,
            "addtags": cmdcmp_files,
            "tree": cmdcmp_dirs,
            "theme": self.cmdcmp_themes,
        }
        self.mode: None | str = None  # BufferHold/EditorHold
        self.cur_cmd = ""
        self.cmd_pos = 0
        self.message = ""
        self.msgtime = time.time()
        self.MSGLAST = 10
        self.floatwins: list[FloatWin] = []

        self.tagsfile: list[str] = []
        self.tags: dict[str, list[TagEntry]] = {}

        self.debug_points: list[tuple[int, int]] = []

        self.winmove_seq: list[int] = [self.cur.id]

        self.theme_selector = ThemeSelector(self)
        self.tag_selector = TagSelector(self)

        self.tagsgen = TagsGenerator(os.getcwd())

        self.floatwins.append(self.theme_selector)
        self.floatwins.append(self.tag_selector)

        self.add_tags(self.tagsgen.output)

        # Wild Menu
        self.cmp_menu: list[str] = []
        self.cmp_func: list[Callable] = []
        self.cmp_select = -1
        self.cmp_scroll = 0
        self.cmp_maxshow = 10
        self.cmp_maxwidth = 50
        self.cmp_minwidth = 10
        self.cmp_border = False
        self.cmp_win = FloatWin(0, 0, self.cmp_maxshow + self.cmp_border * 2, self.cmp_maxwidth + self.cmp_border * 2,
                                self, None, FloatWinFeatures(border=self.cmp_border))
        self.cmp_win.get_prio = lambda: PrioBuffer + 1
        self.floatwins.append(self.cmp_win)
        self.cmp_win.hide = True

        # self.accept_cmd_add_tags(r"D:\msys64\clang64\include\tags")

        # self.gwin.split(True, TextWindow, "Debug Window")
        # self.debug_win: TextWindow = self.gwin.win2
        # self.gwin.change_pos(self.w // 4 * 3)

        # self.gwin.floatwins.append(FloatWin(5, 10, 5, 5, self, self.gwin))

    def remove_id(self, id: int):
        del self.win_ids[id]
        self.winmove_seq = list(filter(lambda x: x != id, self.winmove_seq))

    def get_mode(self):
        if isinstance(self.cur, InputBox):
            return "INSERT"
        if not self.mode and isinstance(self.cur, BufferBase):
            return self.cur.mode
        if not self.mode:
            return "NORMAL"
        return self.mode

    def mode_normal(self):
        self.cur.mode_normal()
        self.mode = None
        self.cur_cmd = ""
        self.cmd_pos = 0

    def mode_command(self, s: str = ":"):
        self.mode = "COMMAND"
        self.cur_cmd = s
        self.cmd_pos = 1

    def cmd_cursor_left(self, *_):
        if self.cmd_pos - 1 > 0:
            self.cmd_pos -= 1

    def cmd_cursor_right(self, *_):
        if self.cmd_pos < len(self.cur_cmd):
            self.cmd_pos += 1

    def cmd_cursor_home(self, *_):
        self.cmd_pos = 0

    def cmd_cursor_end(self, *_):
        self.cmd_pos = len(self.cur_cmd)

    def cmd_backspace(self, *_):
        if self.cmd_pos - 1 > 0:
            self.cur_cmd = self.cur_cmd[:self.cmd_pos - 1] + self.cur_cmd[self.cmd_pos:]
            self.cmd_pos -= 1
        elif self.cmd_pos == 1 and self.cur_cmd == ":":
            self.mode_normal()

    def cmd_select_next(self, *_):
        self.cmp_select += 1
        if self.cmp_select >= len(self.cmp_menu):
            self.cmp_select = -1

    def cmd_select_prev(self, *_):
        self.cmp_select -= 1
        if self.cmp_select < -1:
            self.cmp_select = len(self.cmp_menu) - 1

    def cmd_select_accept(self, *_):
        if self.cmp_menu and self.cmp_select >= 0:
            self.cmp_func[self.cmp_select]()
            self.cmp_select = -1

    def accept_cmd(self, *_):
        if self.cmp_menu and self.cmp_select != -1:
            self.cmd_select_accept()
            return
        self.cur_cmd = self.cur_cmd[1:].strip()
        split_pos = self.cur_cmd.find(" ")
        if split_pos == -1:
            split_pos = len(self.cur_cmd)
        head = self.cur_cmd[:split_pos]
        tail = self.cur_cmd[split_pos + 1:]
        self.mode_normal()
        if head in self.cur.cmdmap:
            self.cur.cmdmap[head](tail)
        elif head in self.cmdmap:
            self.cmdmap[head](tail)

    def accept_cmd_hsplit(self, arg: str):
        if not isinstance(self.cur, Buffer):
            return
        self.cur.split(HSplit)
        arg = arg.strip()
        if os.path.exists(arg) and os.path.isfile(arg):
            self.cur.parent[0].win2.open_file(arg)  # type: ignore
        self.cur = self.cur.parent[0].win2  # type: ignore

    def accept_cmd_vsplit(self, arg: str):
        if not isinstance(self.cur, Buffer):
            return
        self.cur.split(VSplit)
        arg = arg.strip()
        if os.path.exists(arg) and os.path.isfile(arg):
            self.cur.parent[0].win2.open_file(arg)  # type: ignore
        self.cur = self.cur.parent[0].win2  # type: ignore

    def accept_cmd_goto_by_id(self, arg: str):
        try:
            win_id = int(arg)
        except:
            return
        if win_id in self.win_ids:
            if isinstance(new := self.win_ids[win_id], Buffer):
                self.cur = new

    def accept_cmd_resize_h(self, arg: str):
        if not isinstance(self.cur, Buffer):
            return
        try:
            if arg[0] == '+':
                self.cur.resize_bottomup(self.cur.h + int(arg[1:]), self.cur.w)
            elif arg[0] == '-':
                self.cur.resize_bottomup(self.cur.h - int(arg[1:]), self.cur.w)
            else:
                self.cur.resize(int(arg), self.cur.w)
        except:
            pass

    def accept_cmd_resize_w(self, arg: str):
        if not isinstance(self.cur, Buffer):
            return
        try:
            if arg[0] == '+':
                self.cur.resize_bottomup(self.cur.h, self.cur.w + int(arg[1:]))
            elif arg[0] == '-':
                self.cur.resize_bottomup(self.cur.h, self.cur.w - int(arg[1:]))
            else:
                self.cur.resize_bottomup(self.cur.h, int(arg))
        except:
            pass

    def open_explorer(self, arg: str):
        self.gwin.split(VSplit, FileExplorer, self.w - 1 - max(30, self.w // 5), arg)
        if isinstance(self.gwin, Split):
            self.gwin.revert()
            # self.gwin.win1.resize_bottomup(self.gwin.win1.h, max(30, self.w // 5))

    def key_winmove_right(self, *_):
        if not isinstance(self.cur, Buffer):
            return
        if (win := self.cur.find_right(self.cur.cursor_real_pos()[0])):
            self.cur = win

    def key_winmove_left(self, *_):
        if not isinstance(self.cur, Buffer):
            return
        if (win := self.cur.find_left(self.cur.cursor_real_pos()[0])):
            self.cur = win

    def key_winmove_up(self, *_):
        if not isinstance(self.cur, Buffer):
            return
        if (win := self.cur.find_up(self.cur.cursor_real_pos()[1])):
            self.cur = win

    def key_winmove_down(self, *_):
        if not isinstance(self.cur, Buffer):
            return
        if (win := self.cur.find_down(self.cur.cursor_real_pos()[1])):
            self.cur = win

    def cmd_insert(self, key: str):
        self.cur_cmd = self.cur_cmd[:self.cmd_pos] + \
            key + self.cur_cmd[self.cmd_pos:]
        self.cmd_pos += len(key)

    def accept_cmd_close_window(self, force, *_):
        if not isinstance(self.cur, Buffer):
            return
        if isinstance(self.cur, TextBuffer) and not self.cur.textinputer.is_saved() and not force:
            self.send_message('Cannot close, file not saved')
            return
        if self.cur.parent:
            parent = self.cur.parent[0]
            new_cur = parent.win1 if self.cur.parent[1] else parent.win2
            new_cur.resize(parent.h, parent.w)
            new_cur.move(parent.top, parent.left)
            if parent.parent:
                if parent.parent[1]:
                    parent.parent[0].win2 = new_cur
                    new_cur.parent = parent.parent[0], True
                else:
                    parent.parent[0].win1 = new_cur
                    new_cur.parent = parent.parent[0], False
            else:
                self.gwin = new_cur
                new_cur.parent = None
            new_cur = new_cur.find_buffer()
            parent.close()
            self.cur.close()
            if not new_cur:
                if not (new_cur := self.gwin.find_buffer()):
                    self.quit_editor()
                    return
                else:
                    self.cur = new_cur
            else:
                self.cur = new_cur
        else:
            self.quit_editor()
            return

    def accept_cmd_set_theme(self, arg: str):
        if arg in themes:
            self.theme = Theme(themes[arg])

    def accept_cmd_selectheme(self, *_):
        self.theme_selector.hide = False
        self.cur = self.theme_selector

    def add_tags(self, arg: str, root: str | None = None):
        if os.path.exists(arg) and os.path.isfile(arg):
            self.tagsfile.append(arg)
            merge_tags(self.tags, parse_tags_file(arg, root))

    def accept_cmd_add_tags(self, arg: str):
        self.add_tags(arg)

    def accept_cmd_clear_tags(self, *_):
        self.tagsfile.clear()
        self.tags.clear()

    def accept_cmd_tagbar(self, *_):
        self.gwin.split(VSplit, TagBar, reserve=self.w - 1 - max(30, self.w // 5))

    def accept_cmd_reload_tags(self, *_):
        self.tags = {}
        for tagsfile in self.tagsfile:
            if os.path.exists(tagsfile) and os.path.isfile(tagsfile):
                merge_tags(self.tags, parse_tags_file(tagsfile))

    def accept_cmd_system(self, arg: str):
        reset_term()
        os.system(arg)
        init_term()
        self.screen.update_all()

    def accept_cmd_fuzzytags(self, *_):
        self.cur = FuzzyTags(self)
        self.floatwins.append(self.cur)

    def accept_cmd_fuzzyfiles(self, *_):
        self.cur = FuzzyFiles(self)
        self.floatwins.append(self.cur)

    def start_tagselect(self, tags: list[TagEntry]):
        self.tag_selector.start(tags)
        self.cur = self.tag_selector

    def quit_editor_checked(self, *_):
        for buf in self.win_ids.values():
            if isinstance(buf, TextBuffer) and not buf.textinputer.is_saved():
                self.send_message('Cannot close, file not saved')
                return
        self.quit_editor()

    def quit_editor(self, *_):
        self.running = False

    def alloc_id(self, win: WindowLike):
        new_id = 1
        while new_id in self.win_ids:
            new_id += 1
        self.win_ids[new_id] = win
        return new_id

    def send_message(self, msg: str):
        self.message = msg
        self.msgtime = time.time()

    def cmd_cmp_update(self, menu: list[str], func: list[Callable]):
        if self.cmp_select == -1 or self.cmp_menu[self.cmp_select] not in menu:
            self.cmp_select = -1
        else:
            self.cmp_select = menu.index(self.cmp_menu[self.cmp_select])
        self.cmp_menu = menu
        self.cmp_func = func

    def gen_cmp_func(self, ndel: int, ins: str):
        def func():
            self.cur_cmd = self.cur_cmd[:self.cmd_pos - ndel] + ins + self.cur_cmd[self.cmd_pos:]
            self.cmd_pos = self.cmd_pos - ndel + len(ins)

        return func

    def cmd_fill_cmp(self):
        menu = []
        func = []
        if self.cmd_pos == len(self.cur_cmd):
            if ' ' not in (cmd := self.cur_cmd[1:].lstrip()):
                words = list(self.cmdmap.keys()) + list(self.cur.cmdmap.keys())
                menu = list(filter(lambda x: x[:len(cmd)] == cmd and len(x) > len(cmd), words))
                menu.sort()
                func = [self.gen_cmp_func(len(cmd), x) for x in menu]
            else:
                cmd = self.cur_cmd[1:].strip()
                split_pos = cmd.find(" ")
                if split_pos == -1:
                    split_pos = len(cmd)
                head = cmd[:split_pos]
                tail = cmd[split_pos + 1:]
                menu, ndels = [], []
                if head in self.cur.cmdmap:
                    if head in self.cur.cmdcmp:
                        menu, ndels = self.cur.cmdcmp[head](tail)
                elif head in self.cmdmap:
                    if head in self.cmdcmp:
                        menu, ndels = self.cmdcmp[head](tail)
                func = [self.gen_cmp_func(d, s) for d, s in zip(ndels, menu)]

        self.cmd_cmp_update(menu, func)

    def get_menu_height(self, y: int) -> tuple[int, bool]:
        need_h = min(self.cmp_maxshow, len(self.cmp_menu)) + self.cmp_border
        real_h = y
        if self.h - real_h - 1 < need_h and real_h > self.h - real_h - 1:
            return min(need_h - self.cmp_border, real_h), True
        return min(need_h - self.cmp_border, self.h - real_h - 1), False

    def set_menu_scroll(self, menu_h: int):
        cmp_select = max(self.cmp_select, 0)
        if cmp_select + 1 > self.cmp_scroll + menu_h:
            self.cmp_scroll = cmp_select + 1 - menu_h
        if cmp_select < self.cmp_scroll:
            self.cmp_scroll = cmp_select

    def cmdcmp_themes(self, arg: str):
        words = themes.keys()
        menu = list(filter(lambda x: x[:len(arg)] == arg and len(x) > len(arg), words))
        menu.sort()
        ndels = [len(arg) for _ in menu]
        return menu, ndels
    
    def hook_file_upd(self, file: str):
        if self.tagsgen.update(file):
            self.accept_cmd_reload_tags()

    def draw(self):
        self.debug_points = []

        mode = self.get_mode()

        if self.message and time.time() - self.msgtime > self.MSGLAST:
            self.message = ""

        if mode == "COMMAND":
            line = self.cur_cmd
        elif mode == "INSERT" or self.mode == "VISUAL":
            line = f"-- {mode} --"
            self.message = ""
        elif self.message:
            line = self.message
        else:
            line = ""
        nlines = 1
        w_sum = 0
        for ch in line:
            ch_w = get_width(ch)
            if w_sum + ch_w > self.w:
                nlines += 1
                w_sum = 0
            w_sum += ch_w
        if mode == "COMMAND" and w_sum == self.w:
            nlines += 1

        sh = 0
        ln = 0
        set_cursor = None
        for i, ch in enumerate(line):
            ch_w = get_width(ch)
            if sh + ch_w > self.w:
                sh = 0
                ln += 1
            self.screen.change(self.h - nlines + ln, sh, ch,
                               self.theme.get("text", False))
            if mode == "COMMAND" and i == self.cmd_pos:
                self.screen.set_cursor(self.h - nlines + ln, sh)
                set_cursor = self.h - nlines + ln, sh
            sh += ch_w
        if sh == self.w:
            sh = 0
            ln += 1
        if mode == "COMMAND" and not set_cursor:
            self.screen.set_cursor(self.h - nlines + ln, sh)
            set_cursor = self.h - nlines + ln, sh
        while sh < self.w:
            self.screen.change(self.h - nlines + ln, sh, " ",
                               self.theme.get("text", False))
            sh += 1

        if mode != 'COMMAND':
            keyecho = "".join(self.keyreader.key_seq)
            kew = sum(map(get_width, keyecho))
            draw_text(self.gwin, self.h - 1, self.w - 1 - kew - 5, kew, keyecho, "text", 1)

        if mode == 'COMMAND' and self.cmp_menu:
            y, x = set_cursor  # type: ignore
            menu_h, menu_dir = self.get_menu_height(y)
            self.set_menu_scroll(menu_h)
            menu_w = max(self.cmp_minwidth,
                         min(self.cmp_maxwidth, max(map(lambda x: sum(map(get_width, x)), self.cmp_menu))))
            if x + menu_w + 1 > self.w:
                menu_left = self.w - menu_w
            else:
                menu_left = x + 1
            if menu_dir:
                self.cmp_win.move(y - menu_h, menu_left)
            else:
                self.cmp_win.move(y + 1, menu_left)
            self.cmp_win.resize(menu_h + self.cmp_border * 2, menu_w + self.cmp_border * 2)
            for i in range(menu_h):
                self.cmp_win.draw_text(i, 0,
                                       self.cmp_menu[i + self.cmp_scroll] if i + self.cmp_scroll < len(self.cmp_menu) else "",
                                       "completion" if i + self.cmp_scroll != self.cmp_select else 'completion_selected')
            self.cmp_win.hide = False
        else:
            self.cmp_win.hide = True

        for i in self.floatwins:
            i.draw()

        try:
            self.gwin.resize(self.h - nlines, self.w)
        except WinResizeError:
            pass
        self.gwin.draw()
        # utils.gotoxy(self.h + 1, 1)
        # print((self.cur.h, self.cur.w), end="")
        self.screen.update_debug_points(self.debug_points)
        self.screen.refresh()
        flush()

    def resize(self, h: int, w: int):
        self.h, self.w = h, w
        self.screen.update_size(h, w)
        self.gwin.resize(h - 1, w)

    def update_size(self):
        if (self.w, self.h) != (new_size := get_terminal_size()):
            self.resize(new_size[1], new_size[0])
            self.draw()
        else:
            need_update = False
            for win in self.fb_maps.values():
                for win in win:
                    if not self.reader_queue.empty():
                        return
                    if win.renderer.check_update():
                        need_update = True
                        break
                    break
            if need_update and self.reader_queue.empty():
                self.draw()

    def async_getch(self) -> str:
        while self.reader_queue.empty():
            self.update_size()
        return self.reader_queue.get()

    def mainloop(self):
        global running
        self.running = True
        need_cmp = False
        running = True
        self.reader.start()

        while self.running:
            if need_cmp and isinstance(self.cur, TextBuffer):
                self.cur.fill_cmp_menu()
            elif isinstance(self.cur, TextBuffer):
                self.cur.clear_cmp_menu()
            if self.mode == 'COMMAND':
                self.cmd_fill_cmp()
            else:
                self.cmp_menu = []
                self.cmp_func = []
                self.cmp_select = -1

            if self.reader_queue.empty():
                self.draw()

            # keyseq = self.read_keyseq(self.async_getch)
            keyseq = self.keyreader.read_key(self.async_getch())
            if keyseq:
                # import utils
                # utils.gotoxy(self.h + 1, 1)
                # print(keyseq, self.mode, self.get_mode(), end="")
                mode = self.get_mode()
                if isinstance(keyseq, tuple):
                    nrep, k, keys = keyseq
                    if callable(k):
                        if nrep == -1:
                            k()
                        else:
                            k(nrep)
                        if len(keys) == 1 and keys[0] not in ("<C-n>", "<C-p>", "<tab>", "<bs>"):
                            need_cmp = False
                elif mode == "INSERT" and len(keyseq) == len(keyseq[0]) == 1:
                    if isinstance(self.cur, TextBuffer):
                        self.cur.insert(keyseq[0])
                        need_cmp = True
                    elif isinstance(self.cur, InputBox):
                        self.cur.insert(keyseq[0])
                        need_cmp = False
                elif mode == "COMMAND" and len(keyseq) == len(keyseq[0]) == 1:
                    self.cmd_insert(keyseq[0])
                    need_cmp = False

            if not self.winmove_seq or self.cur != self.winmove_seq[-1]:
                self.winmove_seq.append(self.cur.id)

        running = False
