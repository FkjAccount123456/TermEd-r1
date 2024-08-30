from renderer import Renderer
from enum import Enum, unique

"""
带2的是"
"""


@unique
class PyLnSt(Enum):
    Unknown = -1
    Null = 0
    StrPass = 1
    Str2Pass = 2
    StrLong = 3
    Str2Long = 4


@unique
class PyTok(Enum):
    Unknown = -1
    Id = 0
    Num = 1
    Const = 2
    Keyword = 3
    Str = 4
    Comment = 5
    Op = 6
    Other = 8


pyTokDict = [
    "text",
    "id",
    "num",
    "const",
    "kw",
    "str",
    "comment",
    "op",
    "text",
]


class PythonRenderer(Renderer):
    # 看来我还是喜欢抽象命名（
    # 三字符想必是最好的，意义明确还好打
    # 就像use let pub之类（
    def __init__(self, text: list[str]):
        super().__init__(text)
        self.sts = [PyLnSt.Unknown for _ in range(len(self.text))]  # States
        self.buf: list[list[PyTok]] = []

    def change(self, ln: int):
        super().change(ln)
        self.sts[ln] = PyLnSt.Unknown

    def add(self, begin: int, end: int):
        super().add(begin, end)
        self.sts = (
            self.sts[:begin]
            + [PyLnSt.Unknown for _ in range(begin, end + 1)]
            + self.sts[begin:]
        )
    
    def rem(self, begin: int, end: int):
        super().rem(begin, end)
        if end + 1 < len(self.sts):
            self.sts[end + 1] = PyLnSt.Unknown
        del self.sts[begin : end + 1]

    def render_line(self, ln: int):
        if ln > 0:
            st = self.sts[ln - 1]
        else:
            st = PyLnSt.Null
        assert st != PyLnSt.Unknown

    def render(self, target: int):
        assert target < len(self.text)
        while target >= self.ukb and self.ukb < len(self.text):
            old_st = self.sts[self.ukb]
            self.render_line(self.ukb)
            # 上一行尾状态不变且本行未改变
            while self.sts[self.ukb] == old_st\
                    and not self.chs[self.ukb]\
                    and self.ukb < len(self.text) - 1:
                self.ukb += 1
            self.ukb += 1

    def get(self, x: int, y: int) -> str: ...
