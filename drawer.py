"""
不要说了，我知道drawer是抽屉的意思（
"""

from screen import Screen
from utils import get_width
from renderer import *


# 2025-3-14
# Legacy，完全的Legacy
# 恐怕要永远受它拖累了
# 记得当初刚写的时候还洋洋得意呢（
# 可恶，那已经是六个月前了
# 或者更疯狂一点，重新写一个？
class Drawer:
    """
    专用于渲染代码区，与modeline无关
    """

    def __init__(self, screen: Screen, text: list[str],
                 top: int, left: int, h: int, w: int,
                 theme: Theme, linum: bool, prio: int):
        self.screen, self.text = screen, text
        self.top, self.left = top, left
        self.theme, self.linum = theme, linum
        self.prio = prio
        self.update_size(h, w)

        self.scry, self.scrys = 0, 0

    def update_size(self, h: int, w: int):
        self.full_w = w
        self.h, self.w = h, w
        if self.linum:
            self.linum_w = max(len(str(len(self.text))), 2) + 1
            self.w = self.full_w - self.linum_w

    def move(self, top: int, left: int):
        self.top, self.left = top, left

    def get_line_hw(self, line: str, rg: range | None = None) -> tuple[int, int]:
        rg = rg if rg is not None else range(len(line))
        w = 0
        h = 1
        for i in rg:
            ch_w = get_width(line[i])
            if w + ch_w > self.w:
                h += 1
                w = 0
            w += ch_w
        return h, w

    def scroll_up(self, y: int, ys: int, nmove: int):
        assert nmove > 0
        while nmove > 0:
            if ys > nmove:
                return y, ys - nmove
            elif 0 < ys <= nmove:
                nmove -= ys
                ys = 0
            else:
                if y == 0:
                    return -1, -nmove + 1
                else:
                    y -= 1
                    ys = self.get_line_hw(self.text[y])[0] - 1
                    nmove -= 1
        return y, ys

    def scroll_down(self, y: int, ys: int, nmove: int):
        assert nmove > 0
        curline_h = self.get_line_hw(self.text[y])[0] - 1
        while nmove > 0:
            if curline_h - ys > nmove:
                return y, ys + nmove
            elif 0 < curline_h - ys <= nmove:
                nmove -= curline_h - ys
                ys = curline_h
            else:
                if y + 1 < len(self.text):
                    y += 1
                    ys = 0
                    curline_h = self.get_line_hw(self.text[y])[0] - 1
                    nmove -= 1
                else:
                    return y + 1, nmove - 1
        return y, ys

    def process_line(self, line: str):
        res = [0]
        w = 0
        for i, ch in enumerate(line):
            ch_w = get_width(ch)
            if w + ch_w > self.w:
                res.append(i)
                w = 0
            w += ch_w
        res.append(len(line))
        return res

    # 懒得写什么复杂但只快一点的了
    # 反正一次绘制只需要一次绘制光标
    def calc_diff(self, y: int, ys: int):
        assert (y, ys) >= (self.scry, self.scrys)
        i = 0
        cy, cys = self.scry, self.scrys
        curline_h = self.get_line_hw(self.text[cy])[0] - 1
        while (cy, cys) < (y, ys):
            if cys == curline_h:
                if cy < len(self.text) - 1:
                    cy += 1
                    cys = 0
                    curline_h = self.get_line_hw(self.text[cy])[0] - 1
                else:
                    raise RuntimeError("calc_diff: out of range", y, ys, self.text,
                                       self.scry, self.scrys)
            else:
                cys += 1
            i += 1
        return i

    def scroll_buffer(self, y: int, x: int):
        ys, _ = self.get_line_hw(self.text[self.scry])
        if self.scrys >= ys:
            self.scrys = ys - 1
        ys, x = self.get_line_hw(self.text[y], range(x))
        if x < self.w:
            ys -= 1
        if (y, ys) < (self.scry, self.scrys):
            self.scry, self.scrys = y, ys
        elif (nxt := self.scroll_up(y, ys, self.h - 1)) > (self.scry, self.scrys):
            self.scry, self.scrys = nxt

    # 2025-3-16
    # 显然并不能做出太大的改变，不过能改一点是一点
    def draw(self, render: Renderer,
             selb: tuple[int, int] | None = None, sele: tuple[int, int] | None =None):
        target_ln = min(self.scroll_down(self.scry, self.scrys, self.h - 1)[0], len(self.text) - 1)
        render.render(target_ln, len(self.text[target_ln]) - 1)
        scrcnt = 0
        cy, cys = self.scry, self.scrys
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
                            self.screen.change(self.top + scrcnt, self.left + cursh,
                                               ch, self.theme.get("linum", False), self.prio)
                            cursh += 1
                    else:
                        while cursh < self.linum_w:
                            self.screen.change(self.top + scrcnt, self.left + cursh,
                                               " ", self.theme.get("linum", False), self.prio)
                            cursh += 1

                i = -1
                for i in range(curln[cys], curln[cys + 1]):
                    if selb is not None and sele is not None:
                        insel = selb <= (cy, i) <= sele
                    else:
                        insel = False
                    color = self.theme.get(render.get(cy, i), insel)
                    self.screen.change(self.top + scrcnt, self.left + cursh,
                                    (ch := self.text[cy][i]), color, self.prio)
                    cursh += 1
                    for _ in range(get_width(ch) - 1):
                        self.screen.change(self.top + scrcnt, self.left + cursh,
                                        "", color, self.prio)
                        cursh += 1

            if i is not None:
                i += 1
            while cursh < self.full_w:
                self.screen.change(self.top + scrcnt, self.left + cursh,
                                   " ", self.theme.get("text", False), self.prio)
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

    def draw_cursor(self, y: int, x: int):
        ys, x = self.get_line_hw(self.text[y][:x])
        ys -= 1
        if x == self.w:
            return self.calc_diff(y, ys) + 1, self.linum_w
        return self.calc_diff(y, ys), x + self.linum_w

