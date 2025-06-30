"""
2025-3-25
暂时正确，可惜不知道还能再正确多久
2025-5-1
终究是不行了啊
至少得来一次大规模的改写
"""

from renderer import Renderer
import keyword

"""
带2的是"
"""


class PyLnSt:
    Unknown = -1
    Null = 0
    StrPass = 1
    Str2Pass = 2
    StrLong = 3
    Str2Long = 4
    # 经典bitmask
    AfterDef = 0b1000
    AfterClass = 0b10000
    AfterFrom = 0b100000
    AfterDot = 0b1000000


class PyTok:
    Unknown = -1
    Id = 0
    Num = 1
    Const = 2
    Keyword = 3
    Str = 4
    Comment = 5
    Op = 6
    Other = 7
    Class = 8
    Func = 9
    Module = 10
    Field = 11
    Param = 12


pyTokDict = [
    "id",
    "num",
    "const",
    "kw",
    "str",
    "comment",
    "op",
    "text",
    "class",
    "func",
    "module",
    "field",
    "param",
]

pyKwSet = set(keyword.kwlist) | set(keyword.softkwlist)

pyOpSet = set("~!%^&*()-+=[{}]|;:,.<>")

pyFuncSet = {
    "abs",
    "all",
    "any",
    "ascii",
    "bin",
    "breakpoint",
    "callable",
    "chr",
    "compile",
    "copyright",
    "credits",
    "delattr",
    "dir",
    "divmod",
    "eval",
    "exec",
    "exit",
    "format",
    "getattr",
    "globals",
    "hasattr",
    "hash",
    "help",
    "hex",
    "id",
    "input",
    "isinstance",
    "issubclass",
    "iter",
    "len",
    "license",
    "locals",
    "max",
    "min",
    "next",
    "oct",
    "open",
    "ord",
    "pow",
    "print",
    "quit",
    "repr",
    "round",
    "setattr",
    "sum",
    "vars",
}


pyClassSet = {
    "str",
    "int",
    "float",
    "complex",
    "bool",
    "list",
    "tuple",
    "dict",
    "set",
    "frozenset",
    "bytes",
    "bytearray",
    "memoryview",
    "object",
    "type",
    "enumerate",
    "range",
    "zip",
    "map",
    "filter",
    "reversed",
    "slice",
    "staticmethod",
    "classmethod",
    "property",
    "super",

    "Exception",
    "BaseException",
    "SystemExit",
    "KeyboardInterrupt",
    "GeneratorExit",
    "StopIteration",
    "StopAsyncIteration",
    "ArithmeticError",
    "FloatingPointError",
    "OverflowError",
    "ZeroDivisionError",
    "AssertionError",
    "AttributeError",
    "BufferError",
    "EOFError",
    "ImportError",
    "ModuleNotFoundError",
    "LookupError",
    "IndexError",
    "KeyError",
    "MemoryError",
    "NameError",
    "UnboundLocalError",
    "OSError",
    "BlockingIOError",
    "ChildProcessError",
    "ConnectionError",
    "BrokenPipeError",
    "ConnectionAbortedError",
    "ConnectionRefusedError",
    "ConnectionResetError",
    "FileExistsError",
    "FileNotFoundError",
    "InterruptedError",
    "IsADirectoryError",
    "NotADirectoryError",
    "PermissionError",
    "ProcessLookupError",
    "TimeoutError",
    "ReferenceError",
    "RuntimeError",
    "NotImplementedError",
    "RecursionError",
    "SyntaxError",
    "IndentationError",
    "TabError",
    "SystemError",
    "TypeError",
    "ValueError",
    "UnicodeError",
    "UnicodeDecodeError",
    "UnicodeEncodeError",
    "UnicodeTranslateError",
    "Warning",
    "UserWarning",
    "DeprecationWarning",
    "PendingDeprecationWarning",
    "SyntaxWarning",
    "RuntimeWarning",
    "FutureWarning",
    "ImportWarning",
    "UnicodeWarning",
    "BytesWarning",
    "ResourceWarning",
}


class PythonRenderer(Renderer):
    # 看来我还是喜欢抽象命名（
    # 三字符想必是最好的，意义明确还好打
    # 就像use let pub之类（
    # 2025-2-2 得，现在不这么觉得了
    #          原来最大的痛苦就是阅读自己几个月前的代码
    def __init__(self, text: list[str]):
        super().__init__(text)
        self.sts = [PyLnSt.Unknown for _ in range(len(self.text))]  # States
        self.buf: list[list[int]] = [[] for _ in range(len(self.text))]

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
        self.buf = (
            self.buf[:begin] + [[] for _ in range(begin, end + 1)] + self.buf[begin:]
        )

    def rem(self, begin: int, end: int):
        super().rem(begin, end)
        del self.sts[begin : end + 1]
        del self.buf[begin : end + 1]

    def _check_lparen(self, ln: int, x: int) -> bool:
        while x < len(self.text[ln]) and self.text[ln][x].isspace():
            x += 1
        return x < len(self.text[ln]) and self.text[ln][x] == "("

    def render_line(self, ln: int):
        if ln > 0:
            st = self.sts[ln - 1]
        else:
            st = 0
        assert st != PyLnSt.Unknown
        self.buf[ln] = []
        s = self.text[ln]
        res = self.buf[ln]
        x = 0

        if PyLnSt.StrPass <= st <= PyLnSt.Str2Long:
            q = '"' if st in (PyLnSt.Str2Long, PyLnSt.Str2Pass) else "'"
            qcnt = 3 if st in (PyLnSt.StrLong, PyLnSt.Str2Long) else 1
            while x < len(s) and not (s[x: x+qcnt] == q * qcnt):
                if s[x] == "\\":
                    x += 1
                    res.append(PyTok.Str)
                    if x == len(s):
                        # 抽象的艺术
                        return (
                            (PyLnSt.StrLong if q == "'" else PyLnSt.Str2Long)
                            if qcnt == 3
                            else (PyLnSt.StrPass if q == "'" else PyLnSt.Str2Pass)
                        )
                    x += 1
                    res.append(PyTok.Str)
                else:
                    x += 1
                    res.append(PyTok.Str)
            if x >= len(s) and qcnt == 3:
                return PyLnSt.StrLong if q == "'" else PyLnSt.Str2Long
            if x < len(s):
                for _ in range(qcnt):
                    x += 1
                    res.append(PyTok.Str)
            st = 0

        # 词进式，每次一个单词
        while x < len(s):

            if s[x].isalnum() or s[x] == "_":
                q = ""
                while x < len(s) and (s[x].isalnum() or s[x] == "_"):
                    q += s[x]
                    x += 1
                if q in {"self", "cls"}:
                    idtp = PyTok.Param
                elif q in {"True", "False", "None"}:
                    idtp = PyTok.Const
                elif q in pyKwSet:
                    idtp = PyTok.Keyword
                    if q == "def":
                        st |= PyLnSt.AfterDef
                    elif q == "class":
                        st |= PyLnSt.AfterClass
                    elif q == "from":
                        st |= PyLnSt.AfterFrom
                    elif q == "import":
                        if st & PyLnSt.AfterFrom:
                            st &= ~PyLnSt.AfterFrom
                        else:
                            st |= PyLnSt.AfterFrom
                elif q.isdecimal():
                    idtp = PyTok.Num
                elif st:
                    if st & PyLnSt.AfterDef:
                        idtp = PyTok.Func
                        st = 0
                    elif st & PyLnSt.AfterClass:
                        idtp = PyTok.Class
                        st = 0
                    elif st & PyLnSt.AfterFrom:
                        idtp = PyTok.Module
                    elif st & PyLnSt.AfterDot:
                        idtp = PyTok.Field
                    else:
                        assert False
                    if self._check_lparen(ln, x):
                        if ord('A') <= ord(q[0]) <= ord('Z'):
                            idtp = PyTok.Class
                        else:
                            idtp = PyTok.Func
                elif q in pyClassSet:
                    idtp = PyTok.Class
                elif q in pyFuncSet:
                    idtp = PyTok.Func
                else:
                    idtp = PyTok.Id
                    if self._check_lparen(ln, x):
                        if ord('A') <= ord(q[0]) <= ord('Z'):
                            idtp = PyTok.Class
                        else:
                            idtp = PyTok.Func
                for _ in q:
                    res.append(idtp)
                st &= ~PyLnSt.AfterDot

            elif s[x] in "\"'":
                q = s[x]
                qcnt = 0
                while x < len(s) and qcnt < 3 and s[x] == q:
                    qcnt += 1
                    x += 1
                    res.append(PyTok.Str)
                if qcnt == 2:
                    continue
                while x < len(s) and not (s[x: x+qcnt] == q * qcnt):
                    if s[x] == "\\":
                        x += 1
                        res.append(PyTok.Str)
                        if x == len(s):
                            # 抽象的艺术
                            return (
                                (PyLnSt.StrLong if q == "'" else PyLnSt.Str2Long)
                                if qcnt == 3
                                else (PyLnSt.StrPass if q == "'" else PyLnSt.Str2Pass)
                            )
                        x += 1
                        res.append(PyTok.Str)
                    else:
                        x += 1
                        res.append(PyTok.Str)
                if x >= len(s) and qcnt == 3:
                    return PyLnSt.StrLong if q == "'" else PyLnSt.Str2Long
                if x < len(s):
                    for _ in range(qcnt):
                        x += 1
                        res.append(PyTok.Str)
                if not (st & PyLnSt.AfterFrom):
                    st = 0
                st &= ~PyLnSt.AfterDot

            elif s[x] in pyOpSet:
                if s[x] == ".":
                    st |= PyLnSt.AfterDot
                else:
                    if not (st & PyLnSt.AfterFrom):
                        st = 0
                    st &= ~PyLnSt.AfterDot
                x += 1
                res.append(PyTok.Op)
            elif s[x] == "#":
                while x < len(s):
                    x += 1
                    res.append(PyTok.Comment)
                return 0
            else:
                x += 1
                res.append(PyTok.Other)
        return 0

    def set_ukb(self):
        old_ukb = self.ukb
        self.ukb = 0
        while self.ukb < len(self.text) and (self.sts[self.ukb] != PyLnSt.Unknown
                                             or self.chs[self.ukb]):
            self.ukb += 1
        self.ukb = min(self.ukb, old_ukb)

    def render(self, target: int):
        # assert target < len(self.text)
        target = min(target, len(self.text) - 1)
        while target >= self.ukb and self.ukb < len(self.text):
            old_st = self.sts[self.ukb]
            self.sts[self.ukb] = self.render_line(self.ukb)
            self.chs[self.ukb] = False
            # 上一行尾状态不变且本行未改变
            while (
                self.sts[self.ukb] == old_st
                and not self.chs[self.ukb]
                and self.ukb < len(self.text) - 1
            ):
                old_st = self.sts[self.ukb]
                self.ukb += 1
            self.ukb += 1

    def get(self, y: int, x: int) -> str:
        assert y < len(self.text)
        return pyTokDict[self.buf[y][x]]
