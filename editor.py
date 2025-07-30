from typing import Callable, NamedTuple
from renderer import Theme, themes
from renderers.renderers import get_renderer
from screen import Screen, VScreen
from utils import ed_getch, flush, get_char_type, get_file_ext, get_width
from drawer import Drawer
from threading import Thread
from buffer import BufferBase
from ederrors import *
from tagparse import parse_tags_file, tags_navigate, merge_tags, TagEntry
import os


def get_terminal_size():
    w, h = os.get_terminal_size()
    # h -= 1
    return w, h


HSplit, VSplit = False, True
PrioBuffer = 0


# 又是可恶的徒手绘图（
# 要不然封装一下吧
def draw_text(self: "WindowLike", top: int, left: int, width: int, text: str, tp: str, prio=0, rev=False):
    # print(f"draw_text{(type(self).__name__, top, left, width, len(text), tp, prio)}")
    shw = 0
    color = self.editor.theme.get(tp, False)
    start = 0
    if (sumw := sum(map(get_width, text))) > width and rev:
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


class FileBase(BufferBase):
    def __init__(self, editor: "Editor"):
        super().__init__()
        self.editor = editor

    def reset_drawer(self):
        ...

    def reset_scroll(self):
        ...

    def reopen(self):
        assert self.file
        with open(self.file, "r", encoding="utf-8") as f:
            text = f.read()
        self.textinputer.clear()
        self.textinputer.insert(0, 0, text)
        self.y = self.ideal_x = self.x = 0
        self.textinputer.save()
        self.renderer = get_renderer(get_file_ext(self.file))(self.text)

    def open_file(self, arg: str, force=False):
        arg = arg.strip()
        old = self.file
        if not arg:
            if self.file and force and not self.textinputer.is_saved() and os.path.exists(self.file):
                self.reopen()
            return
        if arg:
            if self.file and os.path.abspath(self.file) == os.path.abspath(arg):
                if force and not self.textinputer.is_saved() and os.path.exists(self.file):
                    self.reopen()
                return
            self.file = arg
        if self.file and (path := os.path.abspath(self.file)) in self.editor.fb_maps\
                and self.editor.fb_maps[path]:
            # 大换血啊（
            #
            model = self.editor.fb_maps[path].pop()
            self.editor.fb_maps[path].add(model)
            self.textinputer = model.textinputer
            self.renderer = model.renderer
            self.reset_drawer()
            self.text = self.textinputer.text
        elif self.file:
            if not os.path.exists(self.file):
                self.textinputer.clear()
                self.y = self.ideal_x = self.x = 0
                self.textinputer.save()
                self.renderer = get_renderer(get_file_ext(self.file))(self.text)
            else:
                with open(self.file, "r", encoding="utf-8") as f:
                    text = f.read()
                self.textinputer.clear()
                self.textinputer.insert(0, 0, text)
                self.y = self.ideal_x = self.x = 0
                self.reset_scroll()
                self.textinputer.save()
                self.renderer = get_renderer(get_file_ext(self.file))(self.text)
        if old is not None:
            self.editor.fb_maps[os.path.abspath(old)].remove(self)
        if self.file is not None:
            if os.path.abspath(self.file) not in self.editor.fb_maps:
                self.editor.fb_maps[os.path.abspath(self.file)] = set()
            self.editor.fb_maps[os.path.abspath(self.file)].add(self)

    def save_file(self, arg: str):
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
                    if not old_file or get_file_ext(self.file) != get_file_ext(old_file):
                        self.renderer = get_renderer(get_file_ext(self.file))(self.text)
                except:
                    self.file = old_file
            if old_file is not None and old_file != self.file and os.path.exists(old_file):
                if os.path.abspath(old_file) in self.editor.fb_maps:
                    self.editor.fb_maps[os.path.abspath(old_file)].pop()
                if self.file is not None:
                    self.editor.fb_maps[os.path.abspath(self.file)].add(self)


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
        self.id: int

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
        with open(self.options[self.selected]["path"], "r", encoding="utf-8") as f:
            lines = f.readlines()
        if res := tags_navigate(self.options[self.selected], lines):
            _, (y, _) = res
            dstart = max(0, y - displayh // 2) - 1
            self.v_screen.change(1, optionsw, "|", self.editor.theme.get("border", False))
            draw_text(self, self.v_screen.top, dleft, displayw,
                      self.options[self.selected]["path"], "text", self.get_prio(), rev=True)
            for i in range(1, displayh):
                self.v_screen.change(i, optionsw, "|", self.editor.theme.get("border", False))
                draw_text(self, self.v_screen.top + i, dleft, displayw,
                          "" if dstart + i >= len(lines) else lines[dstart + i].replace("\n", "").replace("\r", ""),
                          "completion_selected" if dstart + i == y else "text", self.get_prio())

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
    def split(self, sp_tp: bool, buf_tp = None, *args):
        if self.h < 20 and sp_tp == HSplit or self.w < 40 and sp_tp == VSplit:
            return
        if buf_tp is None:
            buf_tp = TextBuffer
        if sp_tp == HSplit:
            upper_h = self.h // 2
            new_sp = Split(self.top, self.left, self.h, self.w,
                           self.editor, self.parent, sp_tp, upper_h)
            self.resize(upper_h, self.w)
            new_buf = buf_tp(self.top + upper_h, self.left, self.h - upper_h, self.w,
                             self.editor, (new_sp, True), *args)
        else:
            # log(("split", self.h, self.w, (self.w - 1) // 2))
            left_w = (self.w - 1) // 2
            new_sp = Split(self.top, self.left, self.h, self.w,
                           self.editor, self.parent, sp_tp, left_w + 1)
            new_w = self.w - left_w - 1
            self.resize(self.h, left_w)
            new_buf = buf_tp(self.top, self.left + left_w + 1, self.h, new_w,
                             self.editor, (new_sp, True), *args)

        new_sp.win1, new_sp.win2 = self, new_buf
        self.parent = new_sp, False
        if new_sp.parent:
            if not new_sp.parent[1]:
                new_sp.parent[0].win1 = new_sp
            else:
                new_sp.parent[0].win2 = new_sp
        else:
            new_sp.editor.gwin = new_sp


class Buffer(Window, KeyHolder):
    def __init__(self, top: int, left: int, h: int, w: int,
                    editor: "Editor", parent: "tuple[Split, bool] | None"):
        KeyHolder.__init__(self)
        Window.__init__(self, top, left, h, w, editor, parent)

    def find_buffer(self) -> "Buffer | None":
        return self


class FileExplorer(Buffer):
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: "tuple[Split, bool] | None", path=None):
        Buffer.__init__(self, top, left, h, w, editor, parent)
        self.expanded = set()
        self.root = os.path.abspath(os.curdir if not path or not os.path.exists(path) or not os.path.isdir(path) else path)
        self.file_tree = self.build_tree(self.root)
        self.scroll = 0
        self.y = 0
        self.buffer = self.gen_buffer(self.file_tree)

        self.keymap = {
            "INSERT": {},
            "NORMAL": {
                "j": self.cursor_down,
                "k": self.cursor_up,
                "<down>": self.cursor_down,
                "<up>": self.cursor_up,
                "R": self.update,
                "g": {
                    "g": self.cursor_head,
                },
                "G": self.cursor_tail,
                "<pageup>": self.cursor_pageup,
                "<pagedown>": self.cursor_pagedown,
                "o": self.proc_open,
                "<cr>": self.proc_open,
                "<tab>": self.proc_open,
                "c": self.proc_change_root,
                "p": self.proc_change_to_parent,
            },
            "VISUAL": {},
            "COMMAND": {},
        }
        self.cmdmap = {
            "cd": self.change_root,
        }

    def resize(self, h: int, w: int):
        Window.resize(self, self.h, self.w)
        self.h, self.w = h, w

    def move(self, top: int, left: int):
        self.left, self.top = left, top

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

    def scroll_buffer(self, y: int):
        if y < self.scroll:
            self.scroll = y
        elif y - self.h + 2 > self.scroll:
            self.scroll = y - self.h + 2

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


class TextBuffer(Buffer, FileBase):
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: "tuple[Split, bool] | None"):
        Buffer.__init__(self, top, left, h, w, editor, parent)
        FileBase.__init__(self, editor)
        self.prio = PrioBuffer
        self.file: str | None = None
        self.drawer = Drawer(editor.screen, self.text, self.left, self.top,
                             self.h - 1, self.w, editor, True, self.prio)

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

                "d": self.merge_dict(self.gen_readpos_keymap(self.delete_to, self.delete_in), {
                    "d": lambda *n: self.key_del_line(*n),
                }),
                "c": self.gen_readpos_keymap(self.change_to, self.change_in),
                "y": self.merge_dict(self.gen_readpos_keymap(self.yank_to, self.yank_in), {
                    "y": lambda *n: self.key_yank_line(*n),
                }),

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
                    "\"": lambda *n: self.select_in(lambda: self.get_range_match("\"", True), *n),
                    "'": lambda *n: self.select_in(lambda: self.get_range_match("'", True), *n),
                    "`": lambda *n: self.select_in(lambda: self.get_range_match("`", True), *n),
                },
                "a": {
                    "w": lambda *n: self.select_in(self.get_range_cur_word, *n),
                    "p": lambda *n: self.select_in(lambda: self.get_range_paragraph(), *n),
                    "(": lambda *n: self.select_in(lambda: self.get_range_match("("), *n),
                    "[": lambda *n: self.select_in(lambda: self.get_range_match("["), *n),
                    "{": lambda *n: self.select_in(lambda: self.get_range_match("{"), *n),
                    "<": lambda *n: self.select_in(lambda: self.get_range_match("<"), *n),
                    "\"": lambda *n: self.select_in(lambda: self.get_range_match("\""), *n),
                    "'": lambda *n: self.select_in(lambda: self.get_range_match("'"), *n),
                    "`": lambda *n: self.select_in(lambda: self.get_range_match("`"), *n),
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

    def close(self):
        super().close()
        if self.file:
            self.editor.fb_maps[os.path.abspath(self.file)].remove(self)
        # 2025-4-20 要干什么来着？
        # 这里貌似没有什么要改的了

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

    def gen_readpos_keymap(self, fn_to: Callable, fn_in: Callable):
        return {
            "h": lambda *n: fn_to(self.cursor_left, *n),
            "l": lambda *n: fn_to(self.cursor_right, *n),
            "k": lambda *n: fn_to(self.cursor_up, *n),
            "j": lambda *n: fn_to(self.cursor_down, *n),
            "<up>": lambda *n: fn_to(self.cursor_up, *n),
            "<down>": lambda *n: fn_to(self.cursor_down, *n),
            "<left>": lambda *n: fn_to(self.cursor_left, *n),
            "<right>": lambda *n: fn_to(self.cursor_right, *n),
            "<pageup>": lambda *n: fn_to(self.cursor_pageup, *n),
            "<pagedown>": lambda *n: fn_to(self.cursor_pagedown, *n),
            "<home>": lambda *n: fn_to(self.cursor_home, *n),
            "<end>": lambda *n: fn_to(self.cursor_end, *n),
            "w": lambda *n: fn_to(self.cursor_next_word_end, *n),
            "e": lambda *n: fn_to(self.cursor_next_word_end, *n),
            "b": lambda *n: fn_to(self.cursor_prev_word, *n),
            "g": {
                "g": lambda *n: fn_to(self.cursor_head, *n),
            },
            "G": lambda *n: fn_to(self.cursor_tail, *n),
            "0": lambda *n: fn_to(self.cursor_head, *n),
            "$": lambda *n: fn_to(self.cursor_tail, *n),
            "^": lambda *n: fn_to(self.cursor_start, *n),
            " ": lambda *n: fn_to(self.cursor_next_char, *n),
            "<bs>": lambda *n: fn_to(self.cursor_prev_char, *n),
            "f": lambda *n: fn_to(self.cursor_fnxt_char, *n),
            "F": lambda *n: fn_to(self.cursor_fprv_char, *n),
            "n": lambda *n: fn_to(self.find_next, *n),
            "N": lambda *n: fn_to(self.find_prev, *n),
            "%": lambda *n: fn_to(self.goto_match, *n),
            "{": lambda *n: fn_to(self.cursor_prev_paragragh, *n),
            "}": lambda *n: fn_to(self.cursor_next_paragragh, *n),
            "(": lambda *n: fn_to(self.cursor_prev_paragragh, *n),
            ")": lambda *n: fn_to(self.cursor_next_paragragh, *n),

            "i": {
                "w": lambda *n: fn_in(self.get_range_cur_word, *n),
                "(": lambda *n: fn_in(lambda: self.get_range_match("(", True), *n),
                "[": lambda *n: fn_in(lambda: self.get_range_match("[", True), *n),
                "{": lambda *n: fn_in(lambda: self.get_range_match("{", True), *n),
                "<": lambda *n: fn_in(lambda: self.get_range_match("<", True), *n),
                "\"": lambda *n: fn_in(lambda: self.get_range_match("\"", True), *n),
                "'": lambda *n: fn_in(lambda: self.get_range_match("'", True), *n),
                "`": lambda *n: fn_in(lambda: self.get_range_match("`", True), *n),
            },
            "a": {
                "w": lambda *n: fn_in(self.get_range_cur_word, *n),
                "(": lambda *n: fn_in(lambda: self.get_range_match("("), *n),
                "[": lambda *n: fn_in(lambda: self.get_range_match("["), *n),
                "{": lambda *n: fn_in(lambda: self.get_range_match("{"), *n),
                "<": lambda *n: fn_in(lambda: self.get_range_match("<"), *n),
                "\"": lambda *n: fn_in(lambda: self.get_range_match("\""), *n),
                "'": lambda *n: fn_in(lambda: self.get_range_match("'"), *n),
                "`": lambda *n: fn_in(lambda: self.get_range_match("`"), *n),
            },
        }

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

    def key_enter(self, *_):
        if self.cmp_menu:
            self.cmp_menu_accept()
        else:
            self.insert("\n")
            self.insert(self.renderer.get_indent(self.y - 1))

    def key_tab(self, *_):
        if self.cmp_menu:
            self.cmp_select_next()
        else:
            self.insert_tab()

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

    def goto_tag(self, tag: TagEntry):
        if res := tags_navigate(tag):
            file, (y, x) = res
            self.open_file(file)
            if os.path.abspath(self.file) == os.path.abspath(file):
                self.y = y
                self.x = self.ideal_x = x

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
        menu = []
        func = []
        cw_range = self.get_range_last_word()
        if cw_range:
            cur_word = self.textinputer.get(*cw_range[0], *cw_range[1])
            for i in sorted(self.get_all_words()):
                if i[:len(cur_word)] == cur_word and len(i) > len(cur_word):
                    menu.append(i)
                    func.append(self.gen_cmp_func(i))
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
                self.drawer.draw(self.renderer, (self.y, self.x), (self.sely, self.selx))
            else:
                self.drawer.draw(self.renderer, (self.sely, self.selx), (self.y, self.x))
        else:
            self.drawer.draw(self.renderer)
        cursor_real_pos = self.cursor_real_pos()
        if self.editor.cur == self and self.editor.mode != "COMMAND":
            self.editor.screen.set_cursor(*cursor_real_pos)

        if self.file:
            file = self.file
        else:
            file = "untitled"
        saved = self.textinputer.is_saved()
        file = f"[{self.id}] {'[+]' if not saved else ''} {file}"
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
        self.renderer = get_renderer()(self.text)
        self.drawer = Drawer(editor.screen, self.text, self.left, self.top,
                             self.h - 1, self.w, editor, True, 0)

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
        self.drawer.draw(self.renderer)

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
        win1size = self.win1.h, self.win1.w
        win2size = self.win2.h, self.win2.w
        win1pos = self.win1.top, self.win1.left
        win2pos = self.win2.top, self.win2.left
        self.win1.resize(*win2size)
        self.win2.resize(*win1size)
        self.win1.move(*win2pos)
        self.win2.move(*win1pos)
        self.win1.parent = self, True
        self.win2.parent = self, False
        self.win1, self.win2 = self.win2, self.win1
        self.sp_pos = self.win1.h if self.sp_tp == HSplit else self.win1.w + 1

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


class Editor:
    def __init__(self, h: int, w: int):
        self.win_ids = {}
        self.fb_maps: dict[str, set[FileBase]] = {}
        self.h, self.w = h, w
        self.screen = Screen(self.h, self.w)
        self.theme_name = "tokyonight-storm"
        self.theme = Theme(themes[self.theme_name])
        self.linum = True
        self.async_update_size = False
        self.cur: KeyHolder = TextBuffer(0, 0, self.h - 1, self.w, self, None)
        self.gwin: Window = self.cur
        self.running = False
        self.cur_key: str = ""
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

                "<cr>": self.accept_cmd,
                "<bs>": self.cmd_backspace,
                "<space>": lambda *_: self.cmd_insert(" "),
            },
        }
        self.cmdmap = {
            "q": self.accept_cmd_close_window,
            "qa": self.quit_editor,
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
        }
        self.mode: None | str = None  # BufferHold/EditorHold
        self.cur_cmd = ""
        self.cmd_pos = 0
        self.message = ""
        self.floatwins: list[FloatWin] = []

        self.tagsfile = []
        self.tags = {}

        self.debug_points: list[tuple[int, int]] = []

        self.winmove_seq: list[int] = [self.cur.id]

        self.theme_selector = ThemeSelector(self)
        self.tag_selector = TagSelector(self)

        self.floatwins.append(self.theme_selector)
        self.floatwins.append(self.tag_selector)

        self.accept_cmd_add_tags("tags")
        # self.accept_cmd_add_tags(r"D:\msys64\clang64\include\tags")

        # self.gwin.split(True, TextWindow, "Debug Window")
        # self.debug_win: TextWindow = self.gwin.win2
        # self.gwin.change_pos(self.w // 4 * 3)

        # self.gwin.floatwins.append(FloatWin(5, 10, 5, 5, self, self.gwin))

    def remove_id(self, id: int):
        del self.win_ids[id]
        self.winmove_seq = list(filter(lambda x: x != id, self.winmove_seq))

    def get_mode(self):
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

    def accept_cmd(self, *_):
        self.cur_cmd = self.cur_cmd[1:].strip()
        split_pos = self.cur_cmd.find(" ")
        if split_pos == -1:
            split_pos = len(self.cur_cmd)
        head = self.cur_cmd[:split_pos]
        tail = self.cur_cmd[split_pos + 1:]
        if head in self.cmdmap:
            self.cmdmap[head](tail)
        if head in self.cur.cmdmap:
            self.cur.cmdmap[head](tail)
        self.mode_normal()

    def accept_cmd_hsplit(self, *_):
        if not isinstance(self.cur, Buffer):
            return
        self.cur.split(HSplit)

    def accept_cmd_vsplit(self, *_):
        if not isinstance(self.cur, Buffer):
            return
        self.cur.split(VSplit)

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

    def open_explorer(self, *_):
        self.gwin.split(VSplit, FileExplorer)
        if isinstance(self.gwin, Split):
            self.gwin.revert()
            self.gwin.win1.resize_bottomup(self.gwin.win1.h, max(30, self.w // 5))

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
        self.cmd_pos += 1

    def accept_cmd_close_window(self, *_):
        if not isinstance(self.cur, Buffer):
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

    def accept_cmd_add_tags(self, arg: str):
        if os.path.exists(arg) and os.path.isfile(arg):
            self.tagsfile.append(arg)
            merge_tags(self.tags, parse_tags_file(arg))

    def accept_cmd_clear_tags(self, *_):
        self.tagsfile.clear()
        self.tags.clear()

    def start_tagselect(self, tags: list[TagEntry]):
        self.tag_selector.start(tags)
        self.cur = self.tag_selector

    def quit_editor(self, *_):
        self.running = False

    def alloc_id(self, win: WindowLike):
        new_id = 1
        while new_id in self.win_ids:
            new_id += 1
        self.win_ids[new_id] = win
        return new_id

    def draw(self):
        self.debug_points = []

        for i in self.floatwins:
            i.draw()

        if self.mode == "COMMAND":
            line = self.cur_cmd
        elif self.message:
            line = self.message
        elif self.mode == "INSERT" or self.mode == "VISUAL":
            line = f"-- {self.mode} --"
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
        if self.mode == "COMMAND" and w_sum == self.w:
            nlines += 1

        sh = 0
        ln = 0
        set_cursor = False
        for i, ch in enumerate(line):
            ch_w = get_width(ch)
            if sh + ch_w > self.w:
                sh = 0
                ln += 1
            self.screen.change(self.h - nlines + ln, sh, ch,
                               self.theme.get("text", False))
            if self.mode == "COMMAND" and i == self.cmd_pos:
                self.screen.set_cursor(self.h - nlines + ln, sh)
                set_cursor = True
            sh += ch_w
        if sh == self.w:
            sh = 0
            ln += 1
        if self.mode == "COMMAND" and not set_cursor:
            self.screen.set_cursor(self.h - nlines + ln, sh)
        while sh < self.w:
            self.screen.change(self.h - nlines + ln, sh, " ",
                               self.theme.get("text", False))
            sh += 1

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

    def getch(self):
        self.cur_key = ed_getch()

    def async_getch(self) -> str:
        if self.async_update_size:
            self.cur_key = ""
            getch_thread = Thread(target=self.getch, args=(), daemon=True)
            getch_thread.start()

            while not self.cur_key:
                self.update_size()
            return self.cur_key
        else:
            self.update_size()
            return ed_getch()

    def read_keyseq(self, source: Callable) -> list[str] | tuple[int, Callable, list[str]]:
        key = source()
        nrep = -1
        mode = self.get_mode()
        if mode not in ("COMMAND", "INSERT") and len(key) == 1 and key.isdigit() and key != '0':
            num = key
            key = source()
            while len(key) == 1 and key.isdigit():
                num += key
                key = source()
            nrep = int(num)
        keys = [key]
        if key in self.keymap[mode] or key in self.cur.keymap[mode]:
            if key in self.keymap[mode]:
                k = self.keymap[mode][key]
            else:
                k = None
            if key in self.cur.keymap[mode]:
                ck = self.cur.keymap[mode][key]
            else:
                ck = None
            while isinstance(k, dict) or isinstance(ck, dict):
                key = source()
                keys.append(key)
                if k and key in k:
                    k = k[key]
                    if callable(k):
                        return nrep, k, keys
                    elif not isinstance(k, dict):
                        k = None
                else:
                    k = None
                if ck and key in ck:
                    ck = ck[key]
                    if callable(ck):
                        return nrep, ck, keys
                    elif not isinstance(ck, dict):
                        ck = None
                else:
                    ck = None
            if callable(k):
                return nrep, k, keys
            elif callable(ck):
                return nrep, ck, keys
        return keys

    def mainloop(self):
        self.running = True
        need_cmp = False

        while self.running:
            if need_cmp and isinstance(self.cur, TextBuffer):
                self.cur.fill_cmp_menu()
            elif isinstance(self.cur, TextBuffer):
                self.cur.clear_cmp_menu()
            self.draw()

            self.message = ""
            keyseq = self.read_keyseq(self.async_getch)
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
            elif mode == "COMMAND" and len(keyseq) == len(keyseq[0]) == 1:
                self.cmd_insert(keyseq[0])
                need_cmp = False

            if not self.winmove_seq or self.cur != self.winmove_seq[-1]:
                self.winmove_seq.append(self.cur.id)
