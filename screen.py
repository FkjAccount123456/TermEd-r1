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
        self.data = [[" " for i in range(w)] for j in range(h)]
        self.color = [["" for i in range(w)] for j in range(h)]
        self.prio = [[0 for i in range(w)] for j in range(h)]

    def change(self, y: int, x: int, ch: str, color: str, prio=0):
        if y < 0 or x < 0 or y >= self.h or x >= self.w:
            return
        if prio < self.prio[y][x]:
            return
        if self.data[y][x] != ch or self.color[y][x] != color:
            self.changed.add((y, x))
            self.data[y][x] = ch
            self.color[y][x] = color
        self.prio[y][x] = prio

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

        self.prio = [[0 for i in range(self.w)] for j in range(self.h)]
