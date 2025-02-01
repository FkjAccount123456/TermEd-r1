"""
简单才高效
2025-2-1 虽然但是，感觉不如Rope或者链表
"""

from enum import Enum, unique
from typing import NamedTuple
import time

from utils import log


EDIT_DELAY = 0.2


@unique
class HistoryType(Enum):
    Delete = 0
    Insert = 1
    Null = 2  # 仅允许一个作为Root


class History:
    def __init__(self, tp: HistoryType,
                 begin: tuple[int, int],
                 end: tuple[int, int],  # 闭区间
                 text: str):
        self.tp, self.begin, self.end, self.text = tp, begin, end, text

    def __str__(self):
        return f"History({self.tp}, {self.begin}, {self.end}, {repr(self.text)})"
    
    __repr__ = __str__


# 字段多到一定程度，以至于插入一个字符所增加的内存是其本身的数十倍
class UndoTree:
    def __init__(self, parent: "UndoTree | None", id: int):
        self.parent = parent
        self.cur: History = History(HistoryType.Null, (0, 0), (0, 0), "")
        self.chs: list[UndoTree] = []
        self.id = id
        # 所以要连续编辑
        self.t = time.time()

    def add(self, his: History):
        # log(f"{self.cur} {his} {time.time() - self.t}")
        if his.tp == self.cur.tp == HistoryType.Insert and time.time() - self.t <= EDIT_DELAY\
                and self.cur.end[0] == his.begin[0] and self.cur.end[1] == his.begin[1] - 1:
            # log("SeqEdit")
            self.t = time.time()
            self.cur.text += his.text
            self.cur.end = his.end
            return self
        if his.tp == self.cur.tp == HistoryType.Delete and time.time() - self.t <= EDIT_DELAY\
                and self.cur.begin[0] == his.end[0] and self.cur.begin[1] == his.end[1] + 1:
            self.t = time.time()
            self.cur.text = his.text + self.cur.text
            self.cur.begin = his.begin
            return self
        self.t = time.time()
        self.chs.append(UndoTree(self, len(self.chs)))
        self.chs[-1].cur = his
        return self.chs[-1]
    
    def __str__(self):
        return f"UndoTree({self.id}, {self.cur}, {self.parent})"
    
    __repr__ = __str__


class TextInputer:
    def __init__(self, parent):
        self.text = [""]  # 不可进行重新整体赋值
        self.parent = parent
        # 论undo-redo system到底多好写
        # 2025-2-1 虽然但是，现在要写UndoTree了
        #          仍然不难写
        # self.history: list[History] = []
        self.history: UndoTree = UndoTree(None, 0)
        self.cur_history: UndoTree = self.history
        self.save_ver = self.cur_history
        self.root = self.history

    def save(self):
        self.save_ver = self.cur_history

    def set_root(self):
        self.root = self.cur_history

    def is_saved(self):
        # log(f"{id(self.save_ver)} {id(self.cur_history)}")
        # log(id(self.save_ver) == id(self.cur_history))
        return id(self.save_ver) == id(self.cur_history)

    def undo(self):
        # log(str(self.cur_history))
        if self.cur_history.cur.tp != HistoryType.Null\
                and self.cur_history.parent:
            hs = self.cur_history.cur
            self.cur_history = self.cur_history.parent
            if hs.tp == HistoryType.Delete:
                return self.insert(*hs.begin, hs.text, True)
            else:
                return self.delete(*hs.begin, *hs.end, True)

    def redo(self):
        if self.cur_history.chs:
            hs = self.cur_history.chs[-1].cur
            self.cur_history = self.cur_history.chs[-1]
            if hs.tp == HistoryType.Insert:
                return self.insert(*hs.begin, hs.text, True)
            else:
                return self.delete(*hs.begin, *hs.end, True)

    def clear(self):
        self.text.clear()
        self.text.append("")
        self.history = UndoTree(None, 0)
        self.cur_history = self.history
        self.save_ver = self.cur_history

    def insert(self, y: int, x: int, text: str, is_do=False):
        assert y < len(self.text) and x <= len(self.text[y])
        begin = 0, 0
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
            self.cur_history = self.cur_history.add(
                History(HistoryType.Insert, begin, (end[0], end[1]), text))
        return y, x

    def delete(self, y: int, x: int, q: int, p: int, is_do=False):
        if (y, x) > (q, p):
            y, x, q, p = q, p, y, x
        assert q < len(self.text) and p <= len(self.text[q])
        if not is_do:
            self.cur_history = self.cur_history.add(
                History(HistoryType.Delete, (y, x), (q, p), self.get(y, x, q, p)))
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
