from os import get_terminal_size
from drawer import Drawer
from screen import Screen
from textinputer import TextInputer
from msvcrt import getwch as getch, kbhit


class Editor:
    def __init__(self, h: int, w: int):
        self.screen = Screen(h, w - 1)
        self.h, self.w = h, w
        self.text_h = h - 2
        self.text_w = h - 1
        self.drawer = Drawer(self.screen, 0, 0, self.text_h, self.text_w)

        self.textinputer = TextInputer()
        self.text = self.textinputer.text
        self.y = 0
        self.x = self.ideal_x = 0

        self.mode = "NORMAL"

        self.keymaps = {
            "NORMAL": {
                "i": lambda: setattr(self, "mode", "INSERT"),
                "\x03": lambda: setattr(self, "need_quit", True),
            },
            "INSERT": {
                "\x1b": lambda: setattr(self, "mode", "NORMAL"),
            },
            "SELECT": {

            }
        }

        self.need_quit = False

    def move_cursor(self, d: str):
        if d == 'left':
            if self.x:
                self.x -= 1
                self.ideal_x = self.x
        elif d == 'right':
            if self.x < len(self.text[self.y]):
                self.x += 1
                self.ideal_x = self.x
        elif d == 'up':
            if self.y:
                self.y -= 1
                self.x = min(len(self.text[self.y]), self.ideal_x)
        elif d == 'down':
            if self.y + 1 < len(self.text):
                self.y += 1
                self.x = min(len(self.text[self.y]), self.ideal_x)
        elif d == 'home':
            self.x = 0
        elif d == 'end':
            self.x = len(self.text[self.y])
        elif d == 'pageup':

    def basic_renderer(self, y, x):
        return ""

    def mainloop(self):
        while not self.need_quit:
            self.drawer.draw(self.text,self.basic_renderer, self.y, self.x)
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
            elif self.mode == "INSERT" and key == '\r':
                self.y, self.x = self.textinputer.insert(self.y, self.x, key)
                self.ideal_x = self.x


editor = Editor(get_terminal_size().lines, get_terminal_size().columns - 1)
editor.mainloop()
