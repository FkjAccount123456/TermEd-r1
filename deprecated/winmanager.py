"""
虽然但是，不得不把窗口和编辑放一个文件里
"""

from drawer import Drawer
from screen import Screen
from renderer import Theme, default_theme
from renderers.renderers import get_renderer
from pyperclip import copy, paste
from threading import Thread
from textinputer import TextInputer
from utils import getch, trans_getch
import copy
import os


class GSettings:
    def __init__(self, screen: Screen, theme: Theme,
                 tab_size: int):
        self.screen = screen
        self.theme = theme
        self.tab_size = tab_size


class Command:
    def __init__(self, head: str, arg: str):
        self.head, self.arg = head, arg


class Editor:
    def __init__(self):
        self.w, self.h = os.get_terminal_size()
        self.screen = Screen(self.h, self.w)
        self.settings = GSettings(self.screen, default_theme, 4)
        self.cur_win = EdBuffer(None, (0, 0), self.h - 1, self.w, self.settings, self)
        self.g_win = self.cur_win
        self.cur_input: str | None = None
        self.running = False
        self.mode = "NORMAL"

    def getch(self):
        while self.running:
            if not self.cur_input:
                self.cur_input = getch()

    def async_getch(self):
        self.cur_input = None
        while not self.cur_input:
            if (self.w, self.h) != (new_size := os.get_terminal_size()):
                self.w, self.h = new_size
                self.g_win.resize(self.h, self.w)

    def proc_key(self, key: str):
        ...
    
    def run(self):
        self.running = True
        self.getch_thread = Thread(target=self.getch, args=(), daemon=True)
        self.getch_thread.start()

        while self.running:
            key = self.async_getch()
            if not self.proc_key(key):
                self.cur_win.proc_key(self.mode, key)

        self.running = False


class EdWindow:
    def __init__(self,
                 parent: "EdWindow | None",
                 leftop: tuple[int, int],
                 h: int, w: int,
                 settings: GSettings
                 editor: Editor):
        self.parent, self.leftop, self.h, self.w = parent, leftop, h, w
        self.settings = settings

    def draw(self):
        ...

    def resize(self, h: int, w: int):
        ...

    def move(self, leftop: tuple[int, int]):
        ...

    # 默认分一半，本Window留在左上
    def split(self, d: bool):
        ...

    def proc_key(self, key: str) -> bool:
        ...

    def proc_cmd(self, cmd: Command):
        ...

    def change_mode(self, mode: str):
        ...


class EdSplit(EdWindow):
    def __init__(self,
                 parent: "EdWindow | None",
                 leftop: tuple[int, int],
                 h: int, w: int,
                 settings: GSettings,
                 sp_d: bool, sp_pos: int,
                 sp_1: EdWindow, sp_2: EdWindow,
                 editor: Editor):
        super().__init__(parent, leftop, h, w, settings)
        self.sp_d, self.sp_pos = sp_d, sp_pos  # T: WS F: AD
        self.sp_1, self.sp_2 = sp_1, sp_2

    def draw(self):
        self.sp_1.draw()
        self.sp_2.draw()

    # 倒是令我想起那个矩形旋转的三角函数实现
    def resize(self, h: int, w: int):
        if self.sp_d:  # 纵向等比例
            h1 = int(self.sp_1.h / (self.sp_1.h + self.sp_2.h) * h)
            self.sp_1.resize(h1, w)
            self.sp_2.resize(h - h1, w)
            self.sp_2.move((self.leftop[0] + h1, self.leftop[1]))
        else:  # 横向等比例
            w1 = int(self.sp_1.w / (self.sp_1.w + self.sp_2.w) * (w - 1))
            self.sp_1.resize(h, w1)
            self.sp_2.resize(h, w - w1)
            self.sp_2.move((self.leftop[0], self.leftop[1] + w1 + 1))

    def move(self, leftop: tuple[int, int]):
        sh = self.leftop[0] - leftop[0], self.leftop[1] - leftop[1]
        self.sp_1.move((self.sp_1.leftop[0] + sh[0],
                        self.sp_1.leftop[1] + sh[1]))
        self.sp_2.move((self.sp_2.leftop[0] + sh[0],
                        self.sp_2.leftop[1] + sh[1]))
        self.leftop = leftop

    def proc_key(self, key: str) -> bool:
        ...

    def proc_cmd(self, cmd: Command):
        ...

    def change_mode(self, mode: str):
        ...


# modeline也算高度
# 2025-2-17 开始复制+翻译、、、
# keymaps归顶层
class EdBuffer(EdWindow):
    # 虽然是leftop但是是先top后right
    def __init__(self, parent: "EdWindow | None",
                 leftop: tuple[int, int], h: int, w: int,
                 settings: GSettings,
                 editor: Editor):
        super().__init__(parent, leftop, h, w, settings)

        self.textinputer = TextInputer(self)
        self.text = self.textinputer.text
        self.y = self.x = self.ideal_x = 0
        self.sely = self.selx = 0

        self.renderer = get_renderer()(self.text)

        self.text_h = h - 1
        self.text_w = w
        self.drawer = Drawer(self.settings.screen,
                             self.text,
                             *self.leftop,
                             self.text_h, self.text_w,
                             self.settings.theme,
                             True)

        self.mode = "NORMAL"
        self.keyseq = ""
        self.tab_size = self.settings.tab_size

        self.save = None

    def draw(self):
        ...

    def resize(self, h: int, w: int):
        self.h, self.w = h, w

    def move(self, leftop: tuple[int, int]):
        self.leftop = leftop

    def proc_key(self, key: str) -> bool:
        ...

    def proc_cmd(self, cmd: Command):
        ...

    def change_mode(self, mode: str):
        if self.mode != mode:
            self.mode = mode
            self.keyseq = ""

