from utils import *


class Screen:
    def __init__(self, h: int, w: int):
        self.update_size(h, w)
        self.changed: set[Pos] = set()
        self.y, self.x = 0, 0
        self.debug_points: list[tuple[int, int]] = []

        gotoxy(1, 1)
        for _ in range(h):
            print(" " * self.w)

    def update_size(self, h: int, w: int):
        self.h, self.w = h, w
        self.data = [[" " for _ in range(w)] for _ in range(h)]
        self.color = [["" for _ in range(w)] for _ in range(h)]
        self.prio = [[0 for _ in range(w)] for _ in range(h)]

    def update_all(self):
        for y in range(self.h):
            for x in range(self.w):
                self.changed.add((y, x))

    def change(self, y: int, x: int, ch: str, color: str, prio=0):
        if y < 0 or x < 0 or y >= self.h or x >= self.w:
            return
        if prio < self.prio[y][x]:
            return
        if ch == '\t':
            for i in range(0, TAB_WIDTH):
                if self.color[y][x + i] != color or self.data[y][x + i] != " ":
                    self.changed.add((y, x + i))
                self.data[y][x + i] = " "
                self.color[y][x + i] = color
                self.prio[y][x + i] = prio
        else:
            width = get_width(ch)
            if self.color[y][x] != color or self.data[y][x] != ch:
                self.changed.add((y, x))
            self.data[y][x] = ch
            self.color[y][x] = color
            self.prio[y][x] = prio
            for i in range(1, width):
                if self.color[y][x + i] != color or self.data[y][x + i] != "":
                    self.changed.add((y, x + i))
                self.data[y][x + i] = ""
                self.color[y][x + i] = color
                self.prio[y][x + i] = prio

    def fill(self, ch: str, color: str):
        for y in range(self.h):
            for x in range(self.w):
                self.change(y, x, ch, color)

    def set_cursor(self, y: int, x: int):
        self.y, self.x = y, x

    def update_debug_points(self, debug_points: list[tuple[int, int]]):
        self.debug_points = debug_points

    def refresh(self):
        print("\033[0m\033[?25l", end="")
        gotoxy(1, 1)
        if not self.debug_points:
            last = ""
            lastpos = 0, -1
            for y, x in sorted(self.changed):
                # print(y, x, end=' ')
                if y != lastpos[0] or x != lastpos[1] + 1:
                    gotoxy(y + 1, x + 1)
                if last == self.color[y][x]:
                    print(self.color[y][x] + self.data[y][x], end="")
                else:
                    print("\033[0m" + self.color[y][x] + self.data[y][x], end="")
                last = self.color[y][x]
                lastpos = y, x
        else:
            last = ""
            for y in range(self.h):
                gotoxy(y + 1, 1)
                for x in range(self.w):
                    if self.color[y][x] != last:
                        print(self.color[y][x] + self.data[y][x], end="")
                        last = self.color[y][x]
                    else:
                        print(self.data[y][x], end="")
        self.changed = set()

        for y, x in self.debug_points:
            gotoxy(y + 1, x + 1)
            print("\033[41m \033[0m", end="")

        if self.y != -1 and self.x != -1:
            gotoxy(self.y + 1, self.x + 1)
            print("\033[0m\033[?25h", end="")
            self.y = self.x = -1
        else:
            print("\033[0m", end="")

        for i in range(self.h):
            for j in range(self.w):
                self.prio[i][j] = 0


class VScreen:
    def __init__(self, top: int, left: int, h: int, w: int, screen: Screen, prio: int):
        self.top, self.left, self.h, self.w = top, left, h, w
        self.screen = screen
        self.prio = prio

    def change(self, y: int, x: int, ch: str, color: str):
        self.screen.change(self.top + y, self.left + x, ch, color, self.prio)

    def fill(self, ch: str, color: str):
        for y in range(self.h):
            for x in range(self.w):
                self.screen.change(self.top + y, self.left + x, ch, color, self.prio)

    def set_cursor(self, y: int, x: int):
        self.screen.set_cursor(self.top + y, self.left + x)
