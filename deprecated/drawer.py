"""
不要说了，我知道drawer是抽屉的意思（
"""

from screen import Screen
from utils import get_width
from renderer import *


# 2025-3-14
# Legacy，完全的Legacy
# 恐怕要永远受它拖累了
# 或者更疯狂一点，重新写一个？
class Drawer:
    """
    专用于渲染代码区，与行号和modeline无关
    """

    def __init__(
        self,
        screen: Screen,
        text: list[str],
        shh: int,
        shw: int,
        h: int,
        w: int,
        theme: Theme,
        linum: bool,
    ):
        self.screen = screen
        self.text = text
        self.theme = theme
        self.shh, self.shw = shh, shw
        self.scry, self.scrys = 0, 0
        self.scrline = 0
        self.linum = linum
        self.update_size(h, w)

    def update_size(self, h: int, w: int):
        self.full_w = w
        self.h, self.w = h, w
        if self.linum:
            self.linum_w = max(len(str(len(self.text))), 2) + 1
            self.w = self.full_w - self.linum_w

    def move(self, shh: int, shw: int):
        self.shh, self.shw = shh, shw

    def get_line_h(self, line):
        w = 0
        h = 1
        for ch in line:
            ch_w = get_width(ch)
            if w + ch_w > self.w:
                h += 1
                w = 0
            w += ch_w
        # gotoxy(self.h, 20)
        # print(line, h, " " * 20)
        return h

    def get_line_hw(self, line):
        w = 0
        h = 1
        for ch in line:
            ch_w = get_width(ch)
            if w + ch_w > self.w:
                h += 1
                w = 0
            w += ch_w
        # gotoxy(self.h, 20)
        # print(line, h, " " * 20)
        return h, w

    # 这里使用generator是个好想法
    # 这才叫优雅
    def moveup(self, y, ys):
        if y == 0 and ys == 0:
            return
        while not (y == 0 and ys == 0):
            if ys != 0:
                ys -= 1
            elif y != 0:
                y -= 1
                ys = self.get_line_h(self.text[y]) - 1
            else:
                return
            yield y, ys
        return

    def movedown(self, y, ys):
        curlnh = self.get_line_h(self.text[y])
        if y >= len(self.text) - 1 and ys >= curlnh - 1:
            return
        yield y, ys
        while not (y >= len(self.text) - 1 and ys >= curlnh - 1):
            if ys < curlnh - 1:
                ys += 1
            elif y < len(self.text) - 1:
                y += 1
                ys = 0
                curlnh = self.get_line_h(self.text[y])
            else:
                return
            # print(y, ys)
            yield y, ys
        return

    def scroll(self, y, ys, movefn, tgt):
        assert tgt > 0
        movecnt = 0
        # 你说得对，但是Python是函数作用域
        for y, ys in movefn(y, ys):
            movecnt += 1
            if movecnt == tgt:
                break
        return y, ys

    def process_line(self, line: str):
        res = [0]
        w = 0
        for i, ch in enumerate(line):
            ch_w = get_width(ch)
            if w + ch_w > self.w:
                res.append(i + 1)
                w = 0
            w += ch_w
        res.append(len(line))
        return res
    
    def scroll_buffer(self, y: int, x: int):
        y, ys = y, self.get_line_h(self.text[y][:x]) - 1
        if (y, ys) < (self.scry, self.scrys):
            self.scry, self.scrys = y, ys
        elif (nxt := self.scroll(y, ys, self.moveup, self.h - 1)) > (
            self.scry,
            self.scrys,
        ):
            self.scry, self.scrys = nxt

    # 2025-3-1
    # 这玩意或许已经算Legacy了
    # 改不动，根本改不动
    # 2025-3-10
    # 改，必须改，光标绘制怎么能交给Buffer
    def draw(self, render: Renderer, selb=None, sele=None):
        scrcnt = 0
        cy, cys = self.scry, self.scrys
        # gotoxy(self.h, 0)
        # print(cy, cys, y, ys, x)
        curln = self.process_line(self.text[cy])
        isend = False
        while scrcnt < self.h:
            cursh = 0
            i = None
            if not isend:
                if self.linum:
                    if cys == 0:
                        linum = f"%{self.linum_w - 1}d " % (cy + 1)
                        for ch in linum:
                            self.screen.change(self.shh + scrcnt, self.shw + cursh, ch, self.theme.get("linum", False))
                            cursh += 1
                    else:
                        while cursh < self.linum_w:
                            self.screen.change(self.shh + scrcnt, self.shw + cursh, " ", self.theme.get("linum", False))
                            cursh += 1
                i = -1
                for i in range(curln[cys], curln[cys + 1]):
                    if selb is not None and sele is not None:
                        insel = selb <= (cy, i) <= sele
                    else:
                        insel = False
                    color = self.theme.get(render.get(cy, i), insel)
                    self.screen.change(self.shh + scrcnt, self.shw + cursh, self.text[cy][i], color)
                    chw = get_width(self.text[cy][i])
                    cursh += 1
                    for _ in range(i + 1, i + chw):
                        self.screen.change(scrcnt, self.shw + cursh, "", color)
                        cursh += 1
            if i is not None:
                i += 1
            while cursh < self.screen.w:
                self.screen.change(
                    self.shh + scrcnt,
                    self.shw + cursh,
                    " ",
                    self.theme.get("text", False),
                )
                cursh += 1
                if not isend:
                    i = None
            if not isend:
                if cys == len(curln) - 2:
                    if cy == len(self.text) - 1:
                        isend = True
                    else:
                        cy += 1
                        cys = 0
                        curln = self.process_line(self.text[cy])
                else:
                    cys += 1
            scrcnt += 1

    # 2025-3-14 直接gotoxy，但并不能直接
    def draw_cursor(self, y: int, x: int):
        y, ys = y, self.get_line_h(self.text[y][:x]) - 1

