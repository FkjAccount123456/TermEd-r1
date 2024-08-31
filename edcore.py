from os import get_terminal_size
from drawer import Drawer
from screen import Screen
from textinputer import TextInputer
from msvcrt import getwch, kbhit
from renderer import *
from renderers.plaintext import PlainTextRenderer
from renderers.python import PythonRenderer
from utils import clear, flush, get_width, gotoxy
import sys
from pyperclip import copy, paste

# Windows控制台主机适配
if sys.platform == "win32":
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


def getch():
    key = getwch()
    if key == "\x00" or key == "\xe0":
        return "\x00"
    return key


class Editor:
    def __init__(self, h: int, w: int):
        self.screen = Screen(h, w)

        self.textinputer = TextInputer(self)
        self.text = self.textinputer.text
        self.y = 0
        self.x = self.ideal_x = 0
        self.sely = self.selx = 0

        self.theme = Theme(default_theme)
        self.renderer = PythonRenderer(self.text)

        self.h, self.w = h, w
        self.text_h = h - 2
        self.text_w = w - 1
        self.drawer = Drawer(
            self.screen, self.text, 0, 0, self.text_h, self.text_w, self.theme, True,
        )
        # self.linum_w = 2

        self.minibuf = ""
        self.minibuf_h = 1

        self.mode = "NORMAL"

        self.keymaps = {
            "NORMAL": {
                "i": lambda: setattr(self, "mode", "INSERT"),
                "\x03": lambda: setattr(self, "need_quit", True),
                "P": lambda: self.textinputer.insert(self.y, self.x, paste()),
                "p": self.paste_after_cursor,
                "v": self.mode_select,
                "h": lambda: self.move_cursor("left"),
                "j": lambda: self.move_cursor("down"),
                "k": lambda: self.move_cursor("up"),
                "l": lambda: self.move_cursor("right"),
                "0": lambda: self.move_cursor("home"),
                "$": lambda: self.move_cursor("end"),
                "^": lambda: self.move_cursor("start"),
                "g": {
                    "g": lambda: self.move_cursor("head"),
                },
                "G": lambda: self.move_cursor("tail"),
                "\x00": {
                    "H": lambda: self.move_cursor("up"),
                    "P": lambda: self.move_cursor("down"),
                    "K": lambda: self.move_cursor("left"),
                    "M": lambda: self.move_cursor("right"),
                    "I": lambda: self.move_cursor("pageup"),
                    "Q": lambda: self.move_cursor("pagedown"),
                    "G": lambda: self.move_cursor("home"),
                    "O": lambda: self.move_cursor("end"),
                },
            },
            "INSERT": {
                "\x1b": lambda: setattr(self, "mode", "NORMAL"),
                "\x08": self.del_before_cursor,
                "\x00": {
                    "H": lambda: self.move_cursor("up"),
                    "P": lambda: self.move_cursor("down"),
                    "K": lambda: self.move_cursor("left"),
                    "M": lambda: self.move_cursor("right"),
                    "I": lambda: self.move_cursor("pageup"),
                    "Q": lambda: self.move_cursor("pagedown"),
                    "G": lambda: self.move_cursor("home"),
                    "O": lambda: self.move_cursor("end"),
                },
            },
            "SELECT": {
                "\x1b": lambda: setattr(self, "mode", "NORMAL"),
                "y": self.select_yank,
                "c": self.select_cut,
                "d": self.select_del,
                "x": self.select_del,
                "s": self.select_del,
                "h": lambda: self.move_cursor("left"),
                "j": lambda: self.move_cursor("down"),
                "k": lambda: self.move_cursor("up"),
                "l": lambda: self.move_cursor("right"),
                "0": lambda: self.move_cursor("home"),
                "$": lambda: self.move_cursor("end"),
                "^": lambda: self.move_cursor("start"),
                "g": {
                    "g": lambda: self.move_cursor("head"),
                },
                "G": lambda: self.move_cursor("tail"),
                "\x00": {
                    "H": lambda: self.move_cursor("up"),
                    "P": lambda: self.move_cursor("down"),
                    "K": lambda: self.move_cursor("left"),
                    "M": lambda: self.move_cursor("right"),
                    "I": lambda: self.move_cursor("pageup"),
                    "Q": lambda: self.move_cursor("pagedown"),
                    "G": lambda: self.move_cursor("home"),
                    "O": lambda: self.move_cursor("end"),
                },
            },
        }

        self.need_quit = False

    def paste_after_cursor(self):
        self.y, self.x = self.textinputer.insert(self.y, self.x, paste())
        self.ideal_x = self.x

    def mode_select(self):
        self.mode = "SELECT"
        self.sely, self.selx = self.y, self.x

    # 使用Vim命名
    def select_yank(self):
        copy(self.textinputer.get(self.sely, self.selx, self.y, self.x))
        self.mode = "NORMAL"

    def select_cut(self):
        copy(self.textinputer.get(self.sely, self.selx, self.y, self.x))
        self.y, self.x = self.textinputer.delete(self.sely, self.selx, self.y, self.x)
        self.mode = "NORMAL"

    def select_del(self):
        self.y, self.x = self.textinputer.delete(self.y, self.x, self.sely, self.selx)
        self.mode = "NORMAL"

    def del_before_cursor(self):
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

    def del_at_cursor(self):
        self.y, self.x = self.textinputer.delete(self.y, self.x, self.y, self.x)

    def move_cursor(self, d: str):
        if d == "left":
            if self.x:
                self.x -= 1
                self.ideal_x = self.x
        elif d == "right":
            if self.x < len(self.text[self.y]):
                self.x += 1
                self.ideal_x = self.x
        elif d == "up":
            if self.y:
                self.y -= 1
                self.x = min(len(self.text[self.y]), self.ideal_x)
        elif d == "down":
            if self.y + 1 < len(self.text):
                self.y += 1
                self.x = min(len(self.text[self.y]), self.ideal_x)
        elif d == "home":
            self.x = 0
        elif d == "end":
            self.x = len(self.text[self.y])
        elif d == "pageup":
            self.y, _ = self.drawer.scroll(
                self.y,
                self.drawer.get_line_h(self.text[self.y][: self.x]) - 1,
                self.drawer.moveup,
                self.h - 3,
            )
            self.x = min(len(self.text[self.y]), self.ideal_x)
        elif d == "pagedown":
            self.y, _ = self.drawer.scroll(
                self.y,
                self.drawer.get_line_h(self.text[self.y][: self.x]) - 1,
                self.drawer.movedown,
                self.h - 3,
            )
            self.x = min(len(self.text[self.y]), self.ideal_x)
        elif d == "start":
            self.x = 0
            while (
                self.x < len(self.text[self.y]) and self.text[self.y][self.x].isspace()
            ):
                self.x += 1
            self.ideal_x = self.x
        elif d == "head":
            self.x = self.y = self.ideal_x = 0
        elif d == "tail":
            self.y = len(self.text) - 1
            self.ideal_x = self.x = len(self.text[self.y])

    # 注意顺序问题，先渲染文本区（需要计算滚动）
    def draw(self):
        # minibuf
        self.drawer.w = self.w - 1
        self.minibuf_h = self.drawer.get_line_h(self.minibuf)
        starth = self.h - 1 - self.minibuf_h
        curh = 1
        curw = 0
        for ch in self.minibuf:
            chw = get_width(ch)
            if curw + chw > self.w:
                curh += 1
                curw = 0
            self.screen.change(
                starth + curh, curw, ch, self.theme.get("text", False, False)
            )
            curw += 1
            for _ in range(chw - 1):
                self.screen.change(
                    starth + curh, curw, " ", self.theme.get("text", False, False)
                )
                curw += 1
        while curw < self.w:
            self.screen.change(
                starth + curh, curw, " ", self.theme.get("text", False, False)
            )
            curw += 1

        # self.linum_w = max(len(str(len(self.text))) + 1, 2)

        # text
        # self.drawer.w = self.text_w - self.linum_w
        # self.drawer.h = self.h - 1 - self.minibuf_h
        # self.drawer.shw = self.linum_w
        if self.mode == "SELECT" and (self.sely, self.selx) <= (self.y, self.x):
            self.drawer.draw(
                self.renderer,
                self.y,
                self.x,
                (self.sely, self.selx),
                (self.y, self.x),
            )
        elif self.mode == "SELECT" and (self.sely, self.selx) > (self.y, self.x):
            self.drawer.draw(
                self.renderer,
                self.y,
                self.x,
                (self.y, self.x),
                (self.sely, self.selx),
            )
        else:
            self.drawer.draw(self.renderer, self.y, self.x)
        self.screen.refresh()
        flush()

        # modeline
        gotoxy(self.h - self.minibuf_h, 1)
        print(" " * self.w, end="")
        gotoxy(self.h - self.minibuf_h, 1)
        print(
            f" {self.mode}  ln: {self.y + 1} col: {self.x + 1} scroll: {self.drawer.scry + 1}+{self.drawer.scrys}"
        )

        # 或许可以和text一块绘制
        """# linum
        movecnt = 0
        # y, ys = self.drawer.scry, self.drawer.scrys
        # if ys == 0:
        #     numstr = f"%{self.linum_w - 1}d "%(y + 1)
        #     for x, ch in enumerate(numstr):
        #         self.screen.change(movecnt, x, ch, self.theme.get("num", False, False))
        for y, ys in self.drawer.movedown(self.drawer.scry, self.drawer.scrys):
            if movecnt >= self.text_h:
                break
            if ys == 0:
                numstr = f"%{self.linum_w - 1}d " % (y + 1)
                for x, ch in enumerate(numstr):
                    self.screen.change(
                        movecnt, x, ch, self.theme.get("num", False, False)
                    )
            else:
                for i in range(self.linum_w):
                    self.screen.change(
                        movecnt, i, " ", self.theme.get("text", False, False)
                    )
            movecnt += 1
        while movecnt < self.text_h - 1:
            for i in range(self.linum_w):
                self.screen.change(
                    movecnt, i, " ", self.theme.get("text", False, False)
                )
            movecnt += 1"""

    def mainloop(self):
        while not self.need_quit:
            self.draw()
            key = getch()
            if key in self.keymaps[self.mode]:
                x = self.keymaps[self.mode][key]
                while isinstance(x, dict):
                    key = getch()
                    if key in x:
                        x = x[key]
                    else:
                        break
                if callable(x):
                    x()
            elif self.mode == "INSERT" and key.isprintable():
                self.y, self.x = self.textinputer.insert(self.y, self.x, key)
                self.ideal_x = self.x
            elif self.mode == "INSERT" and (key == "\r" or key == "\n"):
                self.y, self.x = self.textinputer.insert(self.y, self.x, "\n")
                self.ideal_x = self.x


print("\033[?25l")
clear()
editor = Editor(get_terminal_size().lines, get_terminal_size().columns - 1)
editor.mainloop()
# print(editor.text)
print("\033[?25h")
