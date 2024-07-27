"""
简单才高效
"""
class TextInputer:
    def __init__(self):
        self.text = [""]  # 不可进行重新整体赋值

    def clear(self):
        self.text.clear()
        self.text.append("")

    def insert(self, y: int, x: int, text: str):
        assert y < len(self.text) and x <= len(self.text[y])
        tmp = ""
        for ch in text:
            if ch == '\n':
                self.text[y] = self.text[y][:x] + tmp + self.text[y][x:]
                self.text.insert(y + 1, "")
                y += 1
                x = 0
                tmp = ''
            elif ch == '\r':
                pass
            else:
                tmp += ch
        self.text[y] = tmp + self.text[y]
        x = len(tmp)
        return y, x

    def delete(self, y: int, x: int, q: int, p: int):
        if (y, x) > (q, p):
            y, x, q, p = q, p, y, x
        assert q < len(self.text) and p <= len(self.text[q])
        if y == q:
            if p == len(self.text[y]):
                self.text[y] = self.text[y][:x]
                if y + 1 < len(self.text):
                    self.text[y] += self.text[y+1]
                    del self.text[y+1]
            else:
                self.text[y] = self.text[y][:x] + self.text[y][p+1:]
        else:
            # 目前总结的区间删除最简模型
            # 写这里的时候脑子里是随时想着文本变动的
            self.text[y] = self.text[y][:x]
            del self.text[y+1:q]
            if p == len(self.text[y+1]):
                del self.text[y+1]
            else:
                self.text[y+1] = self.text[q][p+1:]
            if y + 1 < len(self.text):
                self.text[y] += self.text[y+1]
                del self.text[y+1]
        return y, x

    def get(self, y: int, x: int, q: int, p: int):
        if (y, x) > (q, p):
            y, x, q, p = q, p, y, x
        assert q < len(self.text) and p <= len(self.text[q])
        if y == q:
            if p == len(self.text[y]):
                return self.text[y][x:] + '\n'
            else:
                return self.text[y][x:p+1]
        else:
            res = self.text[y][x:] + '\n'
            if q != y + 1:
                res += "\n".join(self.text[y+1:q]) + '\n'
            res += self.text[y+1][:p+1]
            if p == len(self.text[q]):
                res += '\n'
            return res
