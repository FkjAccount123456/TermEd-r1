from textinputer import TextInputer
from renderers.renderers import get_renderer
from utils import getch
from pyperclip import paste, copy
from utils import get_char_type
from typing import Callable


class BufferBase:
    def __init__(self):
        self.textinputer = TextInputer(self)
        self.text = self.textinputer.text
        self.renderer = get_renderer()(self.text)
        self.y, self.x, self.ideal_x = 0, 0, 0
        self.sely, self.selx = 0, 0
        self.mode = "NORMAL"

        self.tabsize = 4

        self.textinputer.save()

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

    def insert(self, s: str):
        self.y, self.x = self.textinputer.insert(self.y, self.x, s)
        self.ideal_x = self.x

    def insert_tab(self, *_):
        self.y, self.x = self.textinputer.insert(self.y, self.x,
                                                 " " * self.tabsize)
        self.ideal_x = self.x

    def get_range_to(self, move_fn: Callable, *args):
        y, x, ideal_x = self.y, self.x, self.ideal_x
        move_fn(*args)
        y1, x1 = self.y, self.x
        if (y1, x1) < (y, x):
            y1, x1, y, x = y, x, y1, x1
        self.y, self.x, self.ideal_x = y, x, ideal_x
        return (y, x), (y1, x1)

    def gen_rangeto_fn(self, move_fn: Callable, *args):
        return lambda: self.get_range_to(move_fn, *args)

    def delete_to(self, move_fn: Callable, *args):
        (y, x), (y1, x1) = self.get_range_to(move_fn, *args)
        self.textinputer.delete(y, x, y1, x1)

    def delete_in(self, range_fn: Callable, *args):
        r = range_fn(*args)
        if r:
            self.y, self.x = self.textinputer.delete(*r[0], *r[1])
            self.ideal_x = self.x

    def change_to(self, move_fn: Callable, *args):
        self.delete_to(move_fn, *args)
        self.mode = "INSERT"

    def change_in(self, range_fn: Callable, *args):
        self.delete_in(range_fn, *args)
        self.mode = "INSERT"

    def yank_to(self, move_fn: Callable, *args):
        (y, x), (y1, x1) = self.get_range_to(move_fn, *args)
        copy(self.textinputer.get(y, x, y1, x1))

    def yank_in(self, range_fn: Callable, *args):
        r = range_fn(*args)
        if r:
            copy(self.textinputer.get(*r[0], *r[1]))

    def select_in(self, range_fn: Callable, *args):
        r = range_fn(*args)
        if r:
            begin, end = r
            self.sely, self.selx = begin
            self.y, self.x = end
            self.ideal_x = self.x

    def key_normal_a(self, *_):
        if self.x < len(self.text[self.y]):
            self.x += 1
            self.ideal_x = self.x
        self.mode = "INSERT"

    def key_normal_A(self, *_):
        self.x = self.ideal_x = len(self.text[self.y])
        self.mode = "INSERT"

    def key_normal_I(self, *_):
        self.mode = "INSERT"
        self.cursor_start()

    def key_normal_o(self, *_):
        self.key_normal_A()
        self.insert("\n")

    def key_normal_O(self, *_):
        self.key_normal_I()
        self.insert("\n")
        self.cursor_prev_char()

    def key_normal_s(self, n=1):
        self.mode = "INSERT"
        for _ in range(n):
            if self.x < len(self.text[self.y]):
                self.textinputer.delete(self.y, self.x, self.y, self.x)

    def key_normal_S(self, *_):
        self.key_normal_I()
        self.textinputer.delete(self.y, 0, self.y, len(self.text[self.y]) - 1)

    def key_normal_x(self, n=1):
        for _ in range(n):
            self.textinputer.delete(self.y, self.x, self.y, self.x)

    def key_normal_D(self, *_):
        self.textinputer.delete(self.y, self.x, self.y, len(self.text[self.y]) - 1)

    def key_normal_C(self, *_):
        self.textinputer.delete(self.y, self.x, self.y, len(self.text[self.y]) - 1)
        self.mode = "INSERT"

    def key_del_line(self, n=1):
        for _ in range(n):
            if self.y < len(self.text):
                self.textinputer.delete(self.y, 0, self.y, len(self.text[self.y]))
            else:
                break

    def key_yank_line(self, n=1):
        res = "\n".join(self.text[self.y: self.y + n])
        if self.y + n < len(self.text):
            res += "\n"
        copy(res)

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

    def paste_before_cursor(self, n: int = 1):
        for _ in range(n):
            self.textinputer.insert(self.y, self.x, paste())

    # 使用Vim命名
    def select_yank(self, *_):
        copy(self.textinputer.get(self.sely, self.selx, self.y, self.x))
        self.mode = "NORMAL"

    def select_cut(self, *_):
        copy(self.textinputer.get(self.sely, self.selx, self.y, self.x))
        self.y, self.x = self.textinputer.delete(self.sely, self.selx, self.y, self.x)
        self.mode = "INSERT"

    def select_del(self, *_):
        self.y, self.x = self.textinputer.delete(self.y, self.x, self.sely, self.selx)
        self.mode = "NORMAL"

    def paste_after_cursor(self, n: int = 1):
        for _ in range(n):
            self.y, self.x = self.textinputer.insert(self.y, self.x, paste())
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
            if self.y >= len(self.text) - 1 and self.x >= len(self.text[self.y]) - 1:
                break
            if self.x >= len(self.text[self.y]):
                self.y += 1
                self.x = 0
                continue
            cur_tp = get_char_type(self.text[self.y][self.x])
            self.x += 1
            while self.x < len(self.text[self.y]) and get_char_type(self.text[self.y][self.x]) == cur_tp:
                self.x += 1
        self.ideal_x = self.x

    def cursor_next_word_end(self, n: int = 1):
        for _ in range(n):
            if self.y >= len(self.text) - 1 and self.x >= len(self.text[self.y]) - 1:
                break
            if self.x >= len(self.text[self.y]):
                self.y += 1
                self.x = 0
                continue
            self.x += 1
            cur_tp = get_char_type(self.text[self.y][self.x])
            while self.x + 1 < len(self.text[self.y]) and get_char_type(self.text[self.y][self.x + 1]) == cur_tp:
                self.x += 1
        self.ideal_x = self.x

    def cursor_prev_word(self, n: int = 1):
        for _ in range(n):
            if self.x == self.y == 0:
                break
            if self.x == 0:
                self.y -= 1
                self.x = len(self.text[self.y])
                continue
            cur_tp = get_char_type(self.text[self.y][self.x - 1])
            self.x -= 1
            while self.x > 0 and get_char_type(self.text[self.y][self.x - 1]) == cur_tp:
                self.x -= 1
        self.ideal_x = self.x

    def get_next_pos(self, y: int, x: int):
        if x >= len(self.text[y]):
            if y < len(self.text) - 1:
                return y + 1, 0
            else:
                return y, len(self.text[y])
        else:
            return y, x + 1

    def get_prev_pos(self, y: int, x: int):
        if x == 0:
            if y > 0:
                return y - 1, len(self.text[y - 1])
            else:
                return y, 0
        else:
            return y, x - 1

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

    def get_range_cur_word(self) -> None | tuple[tuple[int, int], tuple[int, int]]:  # 闭区间
        y, x = self.y, self.x
        if len(self.text[self.y]) == 0:
            return None
        if x >= len(self.text[y]):
            x = len(self.text[y]) - 1
        cur_tp = get_char_type(self.text[y][x])
        x0 = x
        while x0 > 0 and get_char_type(self.text[y][x0 - 1]) == cur_tp:
            x0 -= 1
        x1 = x
        while x1 < len(self.text[y]) - 1 and get_char_type(self.text[y][x1 + 1]) == cur_tp:
            x1 += 1
        return (y, x0), (y, x1)

    def get_range_last_word(self) -> None | tuple[tuple[int, int], tuple[int, int]]:
        y, x = self.y, self.x
        if len(self.text[self.y]) == 0 or self.x == 0:
            return None
        x -= 1
        cur_tp = get_char_type(self.text[y][x])
        x0 = x
        while x0 > 0 and get_char_type(self.text[y][x0 - 1]) == cur_tp:
            x0 -= 1
        return (y, x0), (y, x)

    def replace(self, text: str, r: None | tuple[tuple[int, int], tuple[int, int]]):
        if r:
            self.textinputer.delete(*r[0], *r[1])
            self.y, self.x = self.textinputer.insert(*r[0], text)
        else:
            self.y, self.x = self.textinputer.insert(self.y, self.x, text)
        self.ideal_x = self.x
