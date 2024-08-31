"""
简单才高效
"""

from utils import gotoxy
from enum import Enum, unique
from typing import NamedTuple


@unique
class HistoryType(Enum):
    Delete = 0
    Insert = 1


class History(NamedTuple):
    tp: HistoryType
    begin: tuple[int, int]
    end: tuple[int, int]
    text: str


class TextInputer:
    def __init__(self, parent):
        self.text = [""]  # 不可进行重新整体赋值
        self.parent = parent
        # 论undo-redo system到底多好写
        self.history: list[History] = []
        self.hs_pos = 0

    def undo(self):
        if self.hs_pos > 0:
            self.hs_pos -= 1
            hs = self.history[self.hs_pos]
            if hs.tp == HistoryType.Delete:
                return self.insert(*hs.begin, hs.text, True)
            else:
                return self.delete(*hs.begin, *hs.end, True)
    
    def redo(self):
        if self.hs_pos < len(self.history):
            hs = self.history[self.hs_pos]
            self.hs_pos += 1
            if hs.tp == HistoryType.Insert:
                return self.insert(*hs.begin, hs.text, True)
            else:
                return self.delete(*hs.begin, *hs.end, True)

    def clear(self):
        self.text.clear()
        self.text.append("")
        self.history = []
        self.hs_pos = 0

    def insert(self, y: int, x: int, text: str, is_do=False):
        assert y < len(self.text) and x <= len(self.text[y])
        if not is_do:
            begin = y, x
        yb = y
        tmp = ""
        self.parent.renderer.change(yb)
        for ch in text:
            if ch == "\n":
                self.text.insert(y + 1, self.text[y][x:])
                self.text[y] = self.text[y][:x] + tmp
                y += 1
                x = 0
                tmp = ""
            elif ch == "\r":
                pass
            else:
                tmp += ch
        self.parent.renderer.add(yb + 1, y)
        # gotoxy(20, 1)
        # print(yb + 1, y)
        self.text[y] = self.text[y][:x] + tmp + self.text[y][x:]
        x += len(tmp)
        # print(y, x, tmp)
        if not is_do:
            end = [y, x]
            if end[1]:
                end[1] -= 1
            else:
                end[0] -= 1
                end[1] = len(self.text[end[0]])
            del self.history[self.hs_pos:]
            self.history.append(History(HistoryType.Insert, begin, tuple(end), text))
            self.hs_pos += 1
        return y, x

    def delete(self, y: int, x: int, q: int, p: int, is_do=False):
        if (y, x) > (q, p):
            y, x, q, p = q, p, y, x
        assert q < len(self.text) and p <= len(self.text[q])
        if not is_do:
            del self.history[self.hs_pos:]
            self.history.append(History(HistoryType.Delete, (y, x), (q, p), self.get(y, x, q, p)))
            self.hs_pos += 1
        self.parent.renderer.change(y)
        self.parent.renderer.rem(y + 1, q)
        if y == q:
            if p == len(self.text[y]):
                self.text[y] = self.text[y][:x]
                if y + 1 < len(self.text):
                    self.text[y] += self.text[y + 1]
                    del self.text[y + 1]
            else:
                self.text[y] = self.text[y][:x] + self.text[y][p + 1 :]
            # gotoxy(5, 1)
            # print(1)
        else:
            # 目前总结的区间删除最简模型
            # 写这里的时候脑子里是随时想着文本变动的
            self.text[y] = self.text[y][:x]
            del self.text[y + 1 : q]
            if p == len(self.text[y + 1]):
                del self.text[y + 1]
            else:
                self.text[y + 1] = self.text[q][p + 1 :]
            if y + 1 < len(self.text):
                self.text[y] += self.text[y + 1]
                del self.text[y + 1]
        return y, x

    def get(self, y: int, x: int, q: int, p: int):
        if (y, x) > (q, p):
            y, x, q, p = q, p, y, x
        assert q < len(self.text) and p <= len(self.text[q])
        if y == q:
            if q != len(self.text) - 1 and p == len(self.text[y]):
                return self.text[y][x:] + "\n"
            else:
                return self.text[y][x : p + 1]
        else:
            res = self.text[y][x:] + "\n"
            if q != y + 1:
                res += "\n".join(self.text[y + 1 : q]) + "\n"
            res += self.text[q][: p + 1]
            if q != len(self.text) - 1 and p == len(self.text[q]):
                res += "\n"
            return res
