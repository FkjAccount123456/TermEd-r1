"""
不要说了，我知道drawer是抽屉的意思（
"""

from screen import Screen
import screen
from utils import get_width, gotoxy, clear, flush
from renderer import *


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
        self.full_w = w
        self.shh, self.shw, self.h, self.w = shh, shw, h, w
        self.scry, self.scrys = 0, 0
        self.scrline = 0
        self.linum = linum

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

    def draw(self, render: Renderer, y, x, selb=None, sele=None):
        if self.linum:
            self.linum_w = max(len(str(len(self.text))), 2) + 1
            self.w = self.full_w - self.linum_w
        y, ys = y, self.get_line_h(self.text[y][:x]) - 1
        if (y, ys) < (self.scry, self.scrys):
            self.scry, self.scrys = y, ys
        elif (nxt := self.scroll(y, ys, self.moveup, self.h - 1)) > (
            self.scry,
            self.scrys,
        ):
            self.scry, self.scrys = nxt
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
                            self.screen.change(self.shh + scrcnt, self.shw + cursh, ch, self.theme.get("num", False, False))
                            cursh += 1
                    else:
                        while cursh < self.linum_w:
                            self.screen.change(self.shh + scrcnt, self.shw + cursh, " ", self.theme.get("num", False, False))
                            cursh += 1
                i = -1
                for i in range(curln[cys], curln[cys + 1]):
                    if selb is not None and sele is not None:
                        insel = selb <= (cy, i) <= sele
                    else:
                        insel = False
                    color = self.theme.get(render.get(cy, i), insel, (y, x) == (cy, i))
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
                    self.theme.get("text", False, not isend and (y, x) == (cy, i)),
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
