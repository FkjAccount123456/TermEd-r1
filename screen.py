from utils import *


class Screen:
    def __init__(self, h: int, w: int):
        self.update_size(h, w)
        self.changed: set[Pos] = set()
        self.y, self.x = 0, 0

        gotoxy(1, 1)
        for _ in range(h):
            print(" " * self.w)

    def update_size(self, h: int, w: int):
        self.h, self.w = h, w
        self.data = [[" " for i in range(w)] for j in range(h)]
        self.color = [["" for i in range(w)] for j in range(h)]

    def change(self, y: int, x: int, ch: str, color: str):
        if y < 0 or x < 0 or y >= self.h or x >= self.w:
            return
        if self.data[y][x] != ch or self.color[y][x] != color:
            self.changed.add((y, x))
            self.data[y][x] = ch
            self.color[y][x] = color

    def fill(self, ch: str, color: str):
        for y in range(self.h):
            for x in range(self.w):
                self.change(y, x, ch, color)

    def set_cursor(self, y: int, x: int):
        self.y, self.x = y, x

    def refresh(self):
        print("\033[0m\033[?25l", end="")
        gotoxy(1, 1)
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
        self.changed = set()
        gotoxy(self.y + 1, self.x + 1)
        print("\033[0m\033[?25h", end="")
