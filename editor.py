from renderer import Theme, default_theme
from renderers.renderers import get_renderer
from screen import Screen
from utils import ed_getch, flush, get_file_ext, get_width, gotoxy
from drawer import Drawer
from threading import Thread
from pyperclip import copy, paste
from buffer import BufferBase
from ederrors import *
import os
import utils


def get_terminal_size():
    w, h = os.get_terminal_size()
    # h -= 1
    return w, h


HSplit, VSplit = False, True


class Window:
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: "tuple[Split, bool] | None"):
        self.top, self.left, self.h, self.w = top, left, h, w
        self.editor, self.parent = editor, parent
        self.id = self.editor.alloc_id(self)

    def close(self):
        del self.editor.win_ids[self.id]

    def find_buffer(self) -> "Buffer | None":
        ...

    def resize(self, h: int, w: int):
        if h < 10 or w < 20:
            raise WinResizeError()

    def check_resize(self, h: int, w: int) -> bool:
        ...

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

    def draw(self):
        ...

    # 新窗口在右下
    def split(self, sp_tp: bool, buf_tp = None, *args):
        if self.h < 20 and sp_tp == HSplit or self.w < 40 and sp_tp == VSplit:
            return
        if buf_tp is None:
            buf_tp = Buffer
        if sp_tp == HSplit:
            upper_h = self.h // 2
            new_sp = Split(self.top, self.left, self.h, self.w,
                           self.editor, self.parent, sp_tp, upper_h)
            self.resize(upper_h, self.w)
            new_buf = buf_tp(self.top + upper_h, self.left, self.h - upper_h, self.w,
                             self.editor, (new_sp, True), *args)
        else:
            left_w = (self.w - 1) // 2
            new_sp = Split(self.top, self.left, self.h, self.w,
                           self.editor, self.parent, sp_tp, left_w + 1)
            self.resize(self.h, left_w)
            new_buf = buf_tp(self.top, self.left + left_w + 1, self.h, self.w - left_w - 1,
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


class Buffer(Window, BufferBase):
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: "tuple[Split, bool] | None"):
        Window.__init__(self, top, left, h, w, editor, parent)
        BufferBase.__init__(self)
        self.file: str | None = None
        self.drawer = Drawer(editor.screen, self.text, self.left, self.top,
                             self.h - 1, self.w, editor.theme, True)

    def close(self):
        super().close()
        if self.file:
            self.editor.fb_maps[os.path.abspath(self.file)].remove(self)
        # 2025-4-20 要干什么来着？
        # 这里貌似没有什么要改的了

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
            self.drawer.text = self.textinputer.text
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

    def insert_tab(self, *_):
        self.y, self.x = self.textinputer.insert(self.y, self.x,
                                                 " " * self.editor.tabsize)
        self.ideal_x = self.x

    def paste_before_cursor(self, n: int = 1):
        for _ in range(n):
            self.textinputer.insert(self.y, self.x, paste())

    def paste_after_cursor(self, n: int = 1):
        for _ in range(n):
            self.y, self.x = self.textinputer.insert(self.y, self.x, paste())
            self.ideal_x = self.x

    # 使用Vim命名
    def select_yank(self, *_):
        copy(self.textinputer.get(self.sely, self.selx, self.y, self.x))
        self.editor.mode = "NORMAL"

    def select_cut(self, *_):
        copy(self.textinputer.get(self.sely, self.selx, self.y, self.x))
        self.y, self.x = self.textinputer.delete(self.sely, self.selx, self.y, self.x)
        self.editor.mode = "NORMAL"

    def select_del(self, *_):
        self.y, self.x = self.textinputer.delete(self.y, self.x, self.sely, self.selx)
        self.editor.mode = "NORMAL"

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

    def cursor_real_pos(self):
        self.drawer.scroll_buffer(self.y, self.x)
        cursor = self.drawer.draw_cursor(self.y, self.x)
        return cursor[0] + self.top, cursor[1] + self.left

    def draw(self):
        self.drawer.scroll_buffer(self.y, self.x)
        if self.editor.mode == "VISUAL":
            if (self.y, self.x) < (self.sely, self.selx):
                self.drawer.draw(self.renderer, (self.y, self.x), (self.sely, self.selx))
            else:
                self.drawer.draw(self.renderer, (self.sely, self.selx), (self.y, self.x))
        else:
            self.drawer.draw(self.renderer)
        if self.editor.cur == self and self.editor.mode != "COMMAND":
            cursor = self.drawer.draw_cursor(self.y, self.x)
            cursor_real_pos = cursor[0] + self.top, cursor[1] + self.left
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
        shw = 0
        for ch in modeline:
            self.editor.screen.change(self.top + self.h - 1, self.left + shw, ch,
                                      self.editor.theme.get("modeline", False))
            shw += 1
            for _ in range(1, get_width(ch)):
                self.editor.screen.change(self.top + self.h - 1, self.left + shw, " ",
                                          self.editor.theme.get("modeline", False))
                shw += 1
        while shw < self.w:
            self.editor.screen.change(self.top + self.h - 1, self.left + shw, " ",
                                      self.editor.theme.get("modeline", False))
            shw += 1

        # self.editor.debug_points.extend([(self.top, self.left),
        #                                  (self.top + self.h - 1, self.left + self.w - 1)])


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
                             self.h - 1, self.w, editor.theme, True)

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
            shw += 1
            for _ in range(1, get_width(ch)):
                self.editor.screen.change(self.top + self.h - 1, self.left + shw, " ",
                                          self.editor.theme.get("modeline", False))
                shw += 1
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
        self.win1.draw()
        self.win2.draw()
        if self.sp_tp == VSplit:
            for i in range(self.top, self.top + self.h):
                self.editor.screen.change(i, self.left + self.sp_pos - 1, "|",
                                          self.editor.theme.get("text", False))


class Editor:
    def __init__(self, h: int, w: int):
        self.win_ids = {}
        self.fb_maps: dict[str, set[Buffer]] = {}
        self.h, self.w = h, w
        self.screen = Screen(self.h, self.w)
        self.theme = Theme(default_theme)
        self.linum = True
        self.async_update_size = False
        self.cur: Buffer = Buffer(0, 0, self.h - 1, self.w, self, None)
        self.gwin: Window = self.cur
        self.running = False
        self.cur_key: str = ""
        # self.getch_thread = Thread(target=self.getch, args=(), daemon=True)

        # 记得手动注册<cr> <tab> <space>
        self.keymap = {
            "INSERT": {
                "<esc>": self.mode_normal,

                "<up>": lambda *n: self.cur.cursor_up(*n),
                "<down>": lambda *n: self.cur.cursor_down(*n),
                "<left>": lambda *n: self.cur.cursor_left(*n),
                "<right>": lambda *n: self.cur.cursor_right(*n),
                "<pageup>": lambda *n: self.cur.cursor_pageup(*n),
                "<pagedown>": lambda *n: self.cur.cursor_pagedown(*n),
                "<home>": lambda *n: self.cur.cursor_home(*n),
                "<end>": lambda *n: self.cur.cursor_end(*n),

                "<bs>": lambda *n: self.cur.del_before_cursor(*n),
                "<tab>": lambda *n: self.cur.insert_tab(*n),
                "<cr>": lambda *n: self.cur.insert("\n"),
                "<space>": lambda *n: self.cur.insert(" "),
            },
            "NORMAL": {
                "i": self.mode_insert,
                "v": self.mode_select,
                ":": lambda *_: self.mode_command(":"),

                "P": lambda *n: self.cur.paste_before_cursor(*n),
                "p": lambda *n: self.cur.paste_after_cursor(*n),
                "u": lambda *n: self.cur.undo(*n),
                "<C-r>": lambda *n: self.cur.redo(*n),

                "h": lambda *n: self.cur.cursor_left(*n),
                "j": lambda *n: self.cur.cursor_down(*n),
                "k": lambda *n: self.cur.cursor_up(*n),
                "l": lambda *n: self.cur.cursor_right(*n),
                "<up>": lambda *n: self.cur.cursor_up(*n),
                "<down>": lambda *n: self.cur.cursor_down(*n),
                "<left>": lambda *n: self.cur.cursor_left(*n),
                "<right>": lambda *n: self.cur.cursor_right(*n),
                "<pageup>": lambda *n: self.cur.cursor_pageup(*n),
                "<pagedown>": lambda *n: self.cur.cursor_pagedown(*n),
                "<home>": lambda *n: self.cur.cursor_home(*n),
                "<end>": lambda *n: self.cur.cursor_end(*n),
                "0": lambda *n: self.cur.cursor_home(*n),
                "$": lambda *n: self.cur.cursor_end(*n),
                "^": lambda *n: self.cur.cursor_start(*n),
                "g": {
                    "g": lambda *n: self.cur.cursor_head(*n),
                },
                "G": lambda *n: self.cur.cursor_tail(*n),
                "w": lambda *n: self.cur.cursor_next_word(*n),
                "b": lambda *n: self.cur.cursor_prev_word(*n),
                "<space>": lambda *n: self.cur.cursor_next_char(*n),
                "<bs>": lambda *n: self.cur.cursor_prev_char(*n),
                "f": lambda *n: self.cur.cursor_fnxt_char(*n),
                "F": lambda *n: self.cur.cursor_fprv_char(*n),

                "<C-up>": self.key_resize_h_sub,
                "<C-down>": self.key_resize_h_add,
                "<C-left>": self.key_resize_v_sub,
                "<C-right>": self.key_resize_v_add,

                ";": {
                    "h": self.key_winmove_left,
                    "l": self.key_winmove_right,
                    "k": self.key_winmove_up,
                    "j": self.key_winmove_down,
                },
            },
            "VISUAL": {
                "<esc>": self.mode_normal,

                "y": lambda *n: self.cur.select_yank(*n),
                "c": lambda *n: self.cur.select_cut(*n),
                "d": lambda *n: self.cur.select_del(*n),
                "x": lambda *n: self.cur.select_del(*n),
                "s": lambda *n: self.cur.select_del(*n),

                "h": lambda *n: self.cur.cursor_left(*n),
                "j": lambda *n: self.cur.cursor_down(*n),
                "k": lambda *n: self.cur.cursor_up(*n),
                "l": lambda *n: self.cur.cursor_right(*n),
                "<up>": lambda *n: self.cur.cursor_up(*n),
                "<down>": lambda *n: self.cur.cursor_down(*n),
                "<left>": lambda *n: self.cur.cursor_left(*n),
                "<right>": lambda *n: self.cur.cursor_right(*n),
                "<pageup>": lambda *n: self.cur.cursor_pageup(*n),
                "<pagedown>": lambda *n: self.cur.cursor_pagedown(*n),
                "<home>": lambda *n: self.cur.cursor_home(*n),
                "<end>": lambda *n: self.cur.cursor_end(*n),
                "0": lambda *n: self.cur.cursor_home(*n),
                "$": lambda *n: self.cur.cursor_end(*n),
                "^": lambda *n: self.cur.cursor_start(*n),
                "g": {
                    "g": lambda *n: self.cur.cursor_head(*n),
                },
                "G": lambda *n: self.cur.cursor_tail(*n),
                "w": lambda *n: self.cur.cursor_next_word(*n),
                "b": lambda *n: self.cur.cursor_prev_word(*n),
                "<space>": lambda *n: self.cur.cursor_next_char(*n),
                "<bs>": lambda *n: self.cur.cursor_prev_char(*n),
                "f": lambda *n: self.cur.cursor_fnxt_char(*n),
                "F": lambda *n: self.cur.cursor_fprv_char(*n),
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
            "o": lambda *n: self.cur.open_file(*n),
            "o!": lambda *n: self.cur.open_file(*n, force=True),
            "e": lambda *n: self.cur.open_file(*n),
            "e!": lambda *n: self.cur.open_file(*n, force=True),
            "w": lambda *n: self.cur.save_file(*n),
            "sp": self.accept_cmd_hsplit,
            "vsp": self.accept_cmd_vsplit,

            "su": self.accept_cmd_select_parent,
            "sc": self.accept_cmd_select_cur,
            "s1": self.accept_cmd_split_1,
            "s2": self.accept_cmd_split_2,
            "ss": self.accept_cmd_set_cur,
            "so": self.accept_cmd_select_sibling,  # 令我想起Emacs
            "sg": self.accept_cmd_goto_by_id,
            "wh": self.accept_cmd_resize_h,
            "wv": self.accept_cmd_resize_v,
        }
        self.mode = "NORMAL"
        self.cur_cmd = ""
        self.cmd_pos = 0
        self.message = ""

        self.tabsize = 4
        self.selected_win: Window = self.cur

        self.debug_points: list[tuple[int, int]] = []

        # self.gwin.split(True, TextWindow, "Debug Window")
        # self.debug_win: TextWindow = self.gwin.win2
        # self.gwin.change_pos(self.w // 4 * 3)

    def mode_normal(self, *_):
        self.mode = "NORMAL"
        self.cur_cmd = ""
        self.cmd_pos = 0

    def mode_select(self, *_):
        self.mode = "VISUAL"
        self.cur.sely, self.cur.selx = self.cur.y, self.cur.x

    def mode_insert(self, *_):
        self.mode = "INSERT"

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
        self.mode_normal()

    def accept_cmd_hsplit(self, *_):
        self.selected_win.split(HSplit)

    def accept_cmd_vsplit(self, *_):
        self.selected_win.split(VSplit)

    def accept_cmd_select_parent(self, *_):
        if self.selected_win.parent:
            self.selected_win = self.selected_win.parent[0]

    def accept_cmd_select_cur(self, *_):
        self.selected_win = self.cur

    def accept_cmd_split_1(self, *_):
        if isinstance(self.selected_win, Split):
            self.selected_win = self.selected_win.win1

    def accept_cmd_split_2(self, *_):
        if isinstance(self.selected_win, Split):
            self.selected_win = self.selected_win.win2

    def accept_cmd_set_cur(self, *_):
        if isinstance(self.selected_win, Buffer):
            self.cur = self.selected_win

    def accept_cmd_select_sibling(self, *_):
        if self.cur.parent:
            if self.cur.parent[1] and isinstance(self.cur.parent[0].win1, Buffer):
                self.cur = self.selected_win = self.cur.parent[0].win1
            elif isinstance(self.cur.parent[0].win2, Buffer):
                self.cur = self.selected_win = self.cur.parent[0].win2

    def accept_cmd_goto_by_id(self, arg: str):
        try:
            win_id = int(arg)
        except:
            return
        if win_id in self.win_ids:
            self.selected_win = self.win_ids[win_id]
            if isinstance(self.selected_win, Buffer):
                self.cur = self.selected_win

    def accept_cmd_resize_h(self, arg: str):
        try:
            if arg[0] == '+':
                self.cur.resize_bottomup(self.cur.h + int(arg[1:]), self.cur.w)
            elif arg[0] == '-':
                self.cur.resize_bottomup(self.cur.h - int(arg[1:]), self.cur.w)
            else:
                self.cur.resize(int(arg), self.cur.w)
        except WinResizeError:
            pass

    def accept_cmd_resize_v(self, arg: str):
        try:
            if arg[0] == '+':
                self.cur.resize(self.cur.h, self.cur.w + int(arg[1:]))
            elif arg[0] == '-':
                self.cur.resize(self.cur.h, self.cur.w - int(arg[1:]))
            else:
                self.cur.resize(self.cur.h, int(arg))
        except WinResizeError:
            pass

    def key_resize_h_add(self, n=1):
        try:
            self.cur.resize_bottomup(self.cur.h + n, self.cur.w)
        except WinResizeError:
            pass

    def key_resize_h_sub(self, n=1):
        try:
            self.cur.resize_bottomup(self.cur.h - n, self.cur.w)
        except WinResizeError:
            pass

    def key_resize_v_add(self, n=1):
        try:
            self.cur.resize_bottomup(self.cur.h, self.cur.w + n)
        except WinResizeError:
            pass

    def key_resize_v_sub(self, n=1):
        try:
            self.cur.resize_bottomup(self.cur.h, self.cur.w - n)
        except WinResizeError:
            pass

    def key_winmove_right(self, *_):
        if (win := self.cur.find_right(self.cur.cursor_real_pos()[0])):
            self.cur = self.selected_win = win

    def key_winmove_left(self, *_):
        if (win := self.cur.find_left(self.cur.cursor_real_pos()[0])):
            self.cur = self.selected_win = win

    def key_winmove_up(self, *_):
        if (win := self.cur.find_up(self.cur.cursor_real_pos()[1])):
            self.cur = self.selected_win = win

    def key_winmove_down(self, *_):
        if (win := self.cur.find_down(self.cur.cursor_real_pos()[1])):
            self.cur = self.selected_win = win

    def cmd_insert(self, key: str):
        self.cur_cmd = self.cur_cmd[:self.cmd_pos] + \
            key + self.cur_cmd[self.cmd_pos:]
        self.cmd_pos += 1

    def accept_cmd_close_window(self, *_):
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
        self.selected_win = self.cur

    def quit_editor(self, *_):
        self.running = False

    def alloc_id(self, win: Window):
        new_id = 1
        while new_id in self.win_ids:
            new_id += 1
        self.win_ids[new_id] = win
        return new_id

    def draw(self):
        self.debug_points = []

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

    def mainloop(self):
        self.running = True

        while self.running:
            self.draw()

            key = self.async_getch()
            self.message = ""
            nrep = -1
            if self.mode not in ("COMMAND", "INSERT") and len(key) == 1 and key.isdigit():
                num = key
                key = self.async_getch()
                while len(key) == 1 and key.isdigit():
                    num += key
                    key = self.async_getch()
                nrep = int(num)
            if key in self.keymap[self.mode]:
                k = self.keymap[self.mode][key]
                while isinstance(k, dict):
                    key = self.async_getch()
                    if key in k:
                        k = k[key]
                    else:
                        break
                if callable(k):
                    if nrep == -1:
                        k()
                    else:
                        k(nrep)
            elif self.mode == "INSERT" and len(key) == 1:
                self.cur.insert(key)
            elif self.mode == "COMMAND" and len(key) == 1:
                self.cmd_insert(key)
