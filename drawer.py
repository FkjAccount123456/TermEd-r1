"""
不要说了，我知道drawer是抽屉的意思（
"""

from screen import Screen
import screen
from utils import get_width, gotoxy, clear


"""
专用于渲染代码区，与行号和modeline无关
"""
class Drawer:
    def __init__(self, screen: Screen, shh: int, shw: int, h: int, w: int):
        self.screen = Screen(h, w - 1)
        self.shh, self.shw, self.h, self.w = shh, shw, h, w
        self.scroll = 0
        self.scrline = 0

    def get_line_h(self, line: str):
        w = 0
        h = 0
        for ch in line:
            ch_w = get_width(ch)
            if w + ch_w > self.screen.w:
                h += 1
                w = 0
            w += ch_w
        return h

    def draw(self, text: list[str], renderer, y: int, x: int):
        yy, xx = y, x
        # 计算scroll
        pos_h = self.get_line_h(text[y][:x])
        yc, hc = y, pos_h
        if (self.scroll, self.scrline) > (yc, hc):
            self.scroll, self.scrline = yc, hc
        else:
            for _ in range(self.w):
                if hc == 0:
                    if yc > 0:
                        yc -= 1
                    else:
                        break
                    hc = self.get_line_h(text[yc])
                else:
                    hc -= 1
            if (yc, hc) > (self.scroll, self.scrline):
                self.scroll, self.scrline = yc, hc
        # 绘制
        y, hc = self.scroll, 0
        w = 0
        x = 0
        while x < len(text[y]) and hc < self.scrline:
            ch = text[y][x]
            ch_w = get_width(ch)
            if w + ch_w > self.w:
                hc += 1
                w = 0
            w += ch_w
            x += 1
        shh = self.shh
        w = 0
        for _ in range(self.w):
            if y >= len(text):
                break
            while x < len(text[y]) and w < self.w:
                ch_w = get_width(text[y][x])
                color = renderer(y, x)
                if y == yy and x == xx:
                    color += '\033[1;47m'
                self.screen.change(y + hc, w, text[y][x], color)
                for i in range(w + 1, w + ch_w):
                    self.screen.change(y + hc, i, '', color)
                w += ch_w
                x += 1
            if y == yy and x == xx:
                self.screen.change(y + hc, w, ' ', '\033[1;47m')
            if x == len(text[y]):
                y += 1
                hc = 0
            else:
                hc += 1
            w = 0

        self.screen.refresh()
