def draw(self, renderer, y: int, x: int):
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
