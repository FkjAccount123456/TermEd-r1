from msvcrt import getwch as getch
from renderer import Renderer, Theme, default_theme
from renderers.renderers import get_renderer
from screen import Screen
from utils import ed_getch, flush, get_file_ext, get_width
from textinputer import TextInputer
from drawer import Drawer
from threading import Thread
from pyperclip import copy, paste
import os


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
        ...

    def move(self, top: int, left: int):
        ...

    def draw(self):
        ...

    # 新窗口在右下
    def split(self, sp_tp: bool, buf_tp = None, *args):
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


class Buffer(Window):
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: "tuple[Split, bool] | None"):
        super().__init__(top, left, h, w, editor, parent)
        self.textinputer = TextInputer(self)
        self.text = self.textinputer.text
        self.renderer = get_renderer()(self.text)
        self.file: str | None = None
        self.drawer = Drawer(editor.screen, self.text, self.left, self.top,
                             self.h - 1, self.w, editor.theme, True)
        self.y, self.x, self.ideal_x = 0, 0, 0
        self.sely, self.selx = 0, 0
        self.textinputer.save()

    def close(self):
        super().close()
        if self.file:
            self.editor.fb_maps[os.path.abspath(self.file)].remove(self)

    def undo(self, n: int = 1):
        for _ in range(n):
            ret = self.textinputer.undo()
            if ret:
                self.y, self.x = ret
                self.ideal_x = self.x

    def redo(self, n: int = 1):
        for _ in range(n):
            ret = self.textinputer.redo()
            if ret:
                self.y, self.x = ret
            self.ideal_x = self.x

    def open_file(self, arg: str):
        old = self.file
        if arg != "":
            self.file = arg
        if self.file and (path := os.path.abspath(self.file)) in self.editor.fb_maps\
                and self.editor.fb_maps[path]:
            # 大换血啊（
            for model in self.editor.fb_maps[path]:
                break
            self.textinputer = model.textinputer
            self.renderer = model.renderer
            self.drawer.text = self.textinputer.text
            self.text = self.textinputer.text
        elif isinstance(self.file, str):
            try:
                with open(self.file, "r", encoding="utf-8") as f:
                    text = f.read()
                self.textinputer.clear()
                self.textinputer.insert(0, 0, text)
                self.y = self.ideal_x = self.x = 0
                self.textinputer.save()
                self.renderer = get_renderer(get_file_ext(self.file))(self.text)
            except FileNotFoundError:
                self.file = old
        if old is not None and os.path.exists(old):
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
                except FileNotFoundError:
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

    def insert(self, s: str):
        self.y, self.x = self.textinputer.insert(self.y, self.x, s)
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

    def del_before_cursor(self, *_):
        if self.x:
            self.y, self.x = self.textinputer.delete(
                self.y, self.x - 1, self.y, self.x - 1
            )
        elif self.y:
            self.y, self.x = self.textinputer.delete(
                self.y - 1,
                len(self.text[self.y - 1]),
                self.y - 1,
                len(self.text[self.y - 1]),
            )
        self.ideal_x = self.x

    def del_at_cursor(self, n: int = 1):
        for _ in range(n):
            self.y, self.x = self.textinputer.delete(self.y, self.x, self.y, self.x)
            self.ideal_x = self.x

    def cursor_left(self, n: int = 1):
        for _ in range(n):
            if self.x:
                self.x -= 1
            else:
                break
        self.ideal_x = self.x

    def cursor_right(self, n: int = 1):
        for _ in range(n):
            if self.x < len(self.text[self.y]):
                self.x += 1
            else:
                break
        self.ideal_x = self.x

    def cursor_up(self, n: int = 1):
        for _ in range(n):
            if self.y:
                self.y -= 1
            else:
                break
        self.x = min(len(self.text[self.y]), self.ideal_x)

    def cursor_down(self, n: int = 1):
        for _ in range(n):
            if self.y + 1 < len(self.text):
                self.y += 1
            else:
                break
        self.x = min(len(self.text[self.y]), self.ideal_x)

    def cursor_home(self, *_):
        self.x = self.ideal_x = 0

    def cursor_end(self, *_):
        self.x = len(self.text[self.y])

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

    def cursor_start(self, *_):
        self.x = 0
        while (
            self.x < len(self.text[self.y]) and self.text[self.y][self.x].isspace()
        ):
            self.x += 1
        self.ideal_x = self.x

    def cursor_head(self, *_):
        self.x = self.y = self.ideal_x = 0

    def cursor_tail(self, n: int = -1):
        if n == -1:
            self.y = len(self.text) - 1
            self.ideal_x = self.x = len(self.text[self.y])
        else:
            self.y = min(len(self.text) - 1, n - 1)
            self.ideal_x = self.x = len(self.text[self.y])

    def cursor_next_word(self, n: int = 1):
        for _ in range(n):
            if self.x == len(self.text[self.y]):
                if self.y < len(self.text) - 1:
                    self.y += 1
                    self.x = 0
            elif self.text[self.y][self.x].isalnum() or self.text[self.y][self.x] == '_':
                while self.x < len(self.text[self.y]) and \
                        (self.text[self.y][self.x].isalnum() or
                         self.text[self.y][self.x] == '_'):
                    self.x += 1
            elif self.text[self.y][self.x].isspace():
                while self.x < len(self.text[self.y]) and self.text[self.y][self.x].isspace():
                    self.x += 1
            else:
                while self.x < len(self.text[self.y]) and \
                        not (self.text[self.y][self.x].isalnum() or
                             self.text[self.y][self.x].isspace()):
                    self.x += 1
        self.ideal_x = self.x

    def cursor_prev_word(self, n: int = 1):
        for _ in range(n):
            if self.x == 0:
                if self.y > 0:
                    self.y -= 1
                    self.x = len(self.text[self.y])
            elif self.text[self.y][self.x - 1].isalnum() or self.text[self.y][self.x - 1] == '_':
                while self.x > 0 and (self.text[self.y][self.x - 1].isalnum() or
                                      self.text[self.y][self.x - 1] == '_'):
                    self.x -= 1
            elif self.text[self.y][self.x - 1].isspace():
                while self.x > 0 and self.text[self.y][self.x - 1].isspace():
                    self.x -= 1
            else:
                while self.x > 0 and not (self.text[self.y][self.x - 1].isalnum() or
                                          self.text[self.y][self.x - 1].isspace()):
                    self.x -= 1
        self.ideal_x = self.x

    def cursor_next_char(self, n: int = 1):
        for _ in range(n):
            if self.x >= len(self.text[self.y]):
                if self.y < len(self.text) - 1:
                    self.y += 1
                    self.x = 0
                else:
                    break
            else:
                self.x += 1
        self.ideal_x = self.x

    def cursor_prev_char(self, n: int = 1):
        for _ in range(n):
            if self.x == 0:
                if self.y > 0:
                    self.y -= 1
                    self.x = len(self.text[self.y])
                else:
                    break
            else:
                self.x -= 1
        self.ideal_x = self.x

    def at_cursor(self):
        if self.x < len(self.text[self.y]):
            return self.text[self.y][self.x]
        elif self.y < len(self.text) - 1:
            return '\n'
        else:
            return None

    def nxt_eof(self):
        return self.y == len(self.text) - 1 and self.x == len(self.text[self.y])

    # 严重破坏代码逻辑，不过现在不知道怎么改
    def cursor_fnxt_char(self, n: int = 1):
        ch = getch()
        if not ch.isprintable() and ch not in ('\r', '\n', ' ', '\t'):
            return
        if ch == '\r':
            ch = '\n'
        for _ in range(n):
            self.cursor_next_char()
            while self.at_cursor() not in (ch, None):
                self.cursor_next_char()

    def cursor_fprv_char(self, n: int = 1):
        ch = getch()
        if ch == '\r':
            ch = '\n'
        for _ in range(n):
            self.cursor_prev_char()
            while self.at_cursor() != ch and not (self.y == self.x == 0):
                self.cursor_prev_char()

    def resize(self, h: int, w: int):
        self.h, self.w = h, w
        self.drawer.update_size(self.h - 1, self.w)

    def move(self, top: int, left: int):
        self.top, self.left = top, left
        self.drawer.move(self.top, self.left)

    def find_buffer(self) -> "Buffer | None":
        return self

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
            self.editor.screen.set_cursor(cursor[0] + self.top, cursor[1] + self.left)

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


# Debug神器
class TextWindow(Window):
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


class Split(Window):
    def __init__(self, top: int, left: int, h: int, w: int,
                 editor: "Editor", parent: "tuple[Split, bool] | None",
                 sp_tp: bool, sp_pos: int):
        super().__init__(top, left, h, w, editor, parent)
        self.sp_tp, self.sp_pos = sp_tp, sp_pos
        self.win1: Window
        self.win2: Window

    def change_pos(self, pos: int):
        if self.sp_tp == HSplit:
            self.win1.resize(self.h, pos)
            self.win2.resize(self.h, self.w - pos - 1)
            self.win2.move(self.top, self.left + pos)
        else:
            self.win1.resize(pos, self.w)
            self.win2.resize(self.h - pos, self.w)
            self.win2.move(self.top + pos, self.left)
        self.sp_pos = pos

    def find_buffer(self) -> "Buffer | None":
        if (buf := self.win1.find_buffer()):
            return buf
        return self.win2.find_buffer()

    def resize(self, h: int, w: int):
        if self.sp_tp == HSplit:
            upper_h = self.sp_pos * h // self.h
            self.win1.resize(upper_h, w)
            self.win2.resize(h - upper_h, w)
            self.win2.move(self.top + upper_h, self.left)
            self.sp_pos = upper_h
        else:
            left_w = (self.sp_pos - 1) * w // self.w
            self.win1.resize(h, left_w)
            self.win2.resize(h, w - left_w - 1)
            self.win2.move(self.top, self.left + left_w + 1)
            self.sp_pos = left_w + 1
        self.h, self.w = h, w

    def move(self, top: int, left: int):
        self.win1.move(top, left)
        if self.sp_tp == HSplit:
            self.win2.move(top + self.sp_pos, left)
        else:
            self.win2.move(top, left + self.sp_pos + 1)
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
        }
        self.mode = "NORMAL"
        self.cur_cmd = ""
        self.cmd_pos = 0
        self.message = ""

        self.tabsize = 4
        self.selected_win: Window = self.cur

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

        self.gwin.resize(self.h - nlines, self.w)
        self.gwin.draw()
        self.screen.refresh()
        flush()

    def resize(self, h: int, w: int):
        self.h, self.w = h, w
        self.screen.update_size(h, w)
        self.cur.resize(h - 1, w)

    def update_size(self):
        if (self.w, self.h) != (new_size := os.get_terminal_size()):
            self.resize(new_size.lines, new_size.columns)
            self.draw()

    def getch(self):
        self.cur_key = ed_getch()

    def async_getch(self) -> str:
        self.cur_key = ""
        getch_thread = Thread(target=self.getch, args=(), daemon=True)
        getch_thread.start()

        while not self.cur_key:
            self.update_size()
        return self.cur_key

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
