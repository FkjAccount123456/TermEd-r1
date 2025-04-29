from textinputer import TextInputer
from renderers.renderers import get_renderer
from msvcrt import getwch as getch


class BufferBase:
    def __init__(self):
        self.textinputer = TextInputer(self)
        self.text = self.textinputer.text
        self.renderer = get_renderer()(self.text)
        self.y, self.x, self.ideal_x = 0, 0, 0
        self.sely, self.selx = 0, 0
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
