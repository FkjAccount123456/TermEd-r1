from textinputer import TextInputer, History, HistoryType
from copy import deepcopy
from renderers.renderers import get_renderer
from utils import getch
from pyperclip import paste, copy
from utils import get_char_type
from typing import Callable
from renderer import Renderer


class BufferBase:
    def __init__(self):
        self.textinputer = TextInputer(self)
        self.text = self.textinputer.text
        self.renderer: Renderer = get_renderer()(self, self.text)
        self.y, self.x, self.ideal_x = 0, 0, 0
        self.sely, self.selx = 0, 0
        self.mode = "NORMAL"
        self.find_str = ""

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

    def proc_indentcmd(self, cmd: list[str]):
        for i in cmd:
            if i[0] == 'i':
                self.insert(i[1:])
            else:
                y, x = i.split(',')
                self.y = int(y)
                self.x = self.ideal_x = int(x)

    def get_range_to(self, move_fn: Callable, *args):
        y, x, ideal_x = self.y, self.x, self.ideal_x
        move_fn(*args)
        y1, x1 = self.y, self.x
        if (y1, x1) < (y, x):
            y1, x1, y, x = y, x, y1, x1
        self.y, self.x, self.ideal_x = y, x, ideal_x
        return (y, x), (y1, x1)

    def gen_rangeto_fn(self, move_fn: Callable, *args):
        return lambda *n: self.get_range_to(move_fn, *args, *n)

    def delete_to(self, move_fn: Callable, *args):
        (y, x), (y1, x1) = self.get_range_to(move_fn, *args)
        self.textinputer.delete(y, x, y1, x1)

    def delete_in(self, range_fn: Callable, n=1):
        for _ in range(n):
            r = range_fn()
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

    def yank_in(self, range_fn: Callable, *_):
        r = range_fn()
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
        self.proc_indentcmd(self.renderer.get_indent(self.y, len(self.text[self.y])))

    def key_normal_O(self, *_):
        self.mode = "INSERT"
        self.x = self.ideal_x = 0
        if self.y:
            self.y -= 1
            self.x = self.ideal_x = len(self.text[self.y])
            self.proc_indentcmd(self.renderer.get_indent(self.y, self.x))
        else:
            self.insert('\n')
            self.y = 0
            self.x = self.ideal_x = 0

    def key_normal_s(self, n=1):
        self.mode = "INSERT"
        for _ in range(n):
            if self.x < len(self.text[self.y]):
                self.textinputer.delete(self.y, self.x, self.y, self.x)

    def key_normal_S(self, *_):
        self.key_normal_I()
        if self.x != len(self.text[self.y]):
            self.textinputer.delete(self.y, self.x, self.y, len(self.text[self.y]) - 1)

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
        self.x = min(len(self.text[self.y]), self.x)
        self.ideal_x = self.x

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

    def del_word_before_cursor(self, *_):
        if self.x:
            if self.x == 1 or get_char_type(self.text[self.y][self.x - 1]) != get_char_type(self.text[self.y][self.x - 2]):
                self.del_before_cursor()
                return
            self.x -= 1
            self.delete_to(self.cursor_prev_word)
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

    def get_range_cur_line(self, *_) -> None | tuple[tuple[int, int], tuple[int, int]]:
        return (self.y, 0), (self.y, len(self.text[self.y]))

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

    def get_range_match(self, ch: str, inrange=False):
        """
        改了好几版终于弄明白思路了
        先向后找第一个抵消后出现的rch，再从找到的位置向前找match的ch
        """
        rch = {
            '(': ')',
            '{': '}',
            '[': ']',
            '<': '>',
        }.get(ch, None)
        if not rch:
            return
        y, x = self.y, self.x
        tp = None
        if not (x < len(self.text[y]) and self.text[y][x] == rch):
            k = int(x < len(self.text[y]) and self.text[y][x] == ch)
            pos0 = None
            if k:
                tp = self.renderer.get(self.y, self.x)
            while (y, x) < (len(self.text) - 1, len(self.text[y])):
                y, x = self.get_next_pos(y, x)
                if x >= len(self.text[y]):
                    continue
                if not tp and self.text[y][x] in (ch, rch):
                    tp = self.renderer.get(y, x)
                if self.text[y][x] == ch and self.renderer.get(y, x) == tp:
                    k += 1
                elif self.text[y][x] == rch and self.renderer.get(y, x) == tp:
                    k -= 1
                    if k == 0 and not pos0:
                        pos0 = y, x
                    if k == -1:
                        break
            else:
                if pos0:
                    y, x = pos0
                    k = -1
                else:
                    return None
        else:
            k = -1
        end = y, x
        while (y, x) > (0, 0):
            y, x = self.get_prev_pos(y, x)
            if x >= len(self.text[y]):
                continue
            if self.text[y][x] == ch and self.renderer.get(y, x) == tp:
                k += 1
                if k == 0:
                    return ((y, x), end) if not inrange else (self.get_next_pos(y, x), self.get_prev_pos(*end))
            elif self.text[y][x] == rch and self.renderer.get(y, x) == tp:
                k -= 1

    def find_match(self, y: int, x: int) -> None | tuple[int, int]:
        lparens = "([{"
        rparens = ")]}"
        if not (x < len(self.text[y]) and self.text[y][x] in (lparens + rparens)):
            while (y, x) < (len(self.text) - 1, len(self.text[-1])):
                y, x = self.get_next_pos(y, x)
                if x < len(self.text[y]) and self.text[y][x] in (lparens + rparens):
                    break
            else:
                return
        if self.text[y][x] in lparens:
            k = 1
            while (y, x) < (len(self.text) - 1, len(self.text[-1])):
                y, x = self.get_next_pos(y, x)
                if x >= len(self.text[y]):
                    continue
                if self.text[y][x] in lparens:
                    k += 1
                elif self.text[y][x] in rparens:
                    k -= 1
                    if k == 0:
                        return y, x
        else:
            k = 1
            while (y, x) > (0, 0):
                y, x = self.get_prev_pos(y, x)
                if x >= len(self.text[y]):
                    continue
                if self.text[y][x] in rparens:
                    k += 1
                elif self.text[y][x] in lparens:
                    k -= 1
                    if k == 0:
                        return y, x

    def goto_match(self, *_):
        if res := self.find_match(self.y, self.x):
            self.y, self.x = res
            self.ideal_x = self.x

    def cursor_prev_paragragh(self, n: int = 1):
        for _ in range(n):
            if self.y == 0:
                break
            self.y -= 1
            while self.y > 0 and not self.text[self.y].strip():
                self.y -= 1
            while self.y > 0 and self.text[self.y - 1].strip():
                self.y -= 1
            self.x = 0
        self.ideal_x = self.x

    def cursor_next_paragragh(self, n: int = 1):
        for _ in range(n):
            if self.y == len(self.text) - 1:
                break
            self.y += 1
            while self.y < len(self.text) - 1 and not self.text[self.y].strip():
                self.y += 1
            while self.y < len(self.text) - 1 and self.text[self.y].strip():
                self.y += 1
            while self.y < len(self.text) - 1 and not self.text[self.y].strip():
                self.y += 1
            self.x = 0
        self.ideal_x = self.x

    def get_range_paragraph(self, inrange=False) -> None | tuple[tuple[int, int], tuple[int, int]]:
        if not self.text[self.y].strip():
            return
        y = endy = self.y
        while y > 0 and self.text[y - 1].strip():
            y -= 1
        while endy < len(self.text) - 1 and self.text[endy + 1].strip():
            endy += 1
        if not inrange:
            y = max(0, y - 1)
            endy = min(len(self.text) - 1, endy + 1)
        return (y, 0), (endy, len(self.text[endy]))

    def replace(self, text: str, r: None | tuple[tuple[int, int], tuple[int, int]]):
        if r:
            self.textinputer.delete(*r[0], *r[1])
            self.y, self.x = self.textinputer.insert(*r[0], text)
        else:
            self.y, self.x = self.textinputer.insert(self.y, self.x, text)
        self.ideal_x = self.x

    def start_find(self, arg: str):
        self.find_str = arg
        self.find_next()

    def parse_substitute(self, arg: str) -> tuple[str, str]:
        fr = ""
        i = 0
        while i < len(arg):
            if arg[i] == '\\':
                i += 1
                if i < len(arg):
                    fr += arg[i]
            elif arg[i] == '/':
                i += 1
                break
            else:
                fr += arg[i]
            i += 1
        return fr, arg[i:]

    def start_substitute(self, arg: str):
        fr, to = self.parse_substitute(arg)
        from_text = deepcopy(self.text)
        for i, line in enumerate(self.text):
            self.text[i] = line.replace(fr, to)
        self.textinputer.cur_history = self.textinputer.cur_history.add(
            History(HistoryType.Refill, (self.y, self.x), (0, 0), "",
                    (from_text, deepcopy(self.text))))
        self.renderer.render_all()

    def find_next(self):
        # 有点Rust的意思了（
        if not self.find_str:
            return
        if res := self._find_next(self.find_str):
            self.y, self.x = res
            self.ideal_x = self.x

    def find_prev(self):
        if not self.find_str:
            return
        if res := self._find_prev(self.find_str):
            self.y, self.x = res
            self.ideal_x = self.x

    def _find_next(self, arg: str, start: tuple[int, int] | None = None) -> None | tuple[int, int]:
        if not start:
            starty, startx = self.y, self.x
        else:
            starty, startx = start
        if (res := self.text[starty].find(arg, startx + 1)) != -1:
            return starty, res
        for y in range(starty + 1, len(self.text)):
            if (res := self.text[y].find(arg)) != -1:
                return y, res
        for y in range(0, starty + 1):
            if (res := self.text[y].find(arg)) != -1:
                return y, res
        return None

    def _find_prev(self, arg: str, start: tuple[int, int] | None = None) -> None | tuple[int, int]:
        if not start:
            starty, startx = self.y, self.x
        else:
            starty, startx = start
        if (res := self.text[starty].rfind(arg, 0, startx)) != -1:
            return starty, res
        for y in range(starty - 1, -1, -1):
            if (res := self.text[y].rfind(arg)) != -1:
                return y, res
        for y in range(len(self.text) - 1, starty - 1, -1):
            if (res := self.text[y].rfind(arg)) != -1:
                return y, res
        return None
