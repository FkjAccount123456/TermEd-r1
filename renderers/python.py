from renderer import Renderer
from enum import Enum, unique
import keyword

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
    AfterDef = 5
    AfterClass = 6


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
    Other = 7
    Class = 8
    Func = 9


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
]

pyKwSet = set(keyword.kwlist) | set(keyword.softkwlist) | {"self", "cls"}

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
        self.buf: list[list[PyTok]] = [[] for _ in range(len(self.text))]

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

    def render_line(self, ln: int):
        if ln > 0:
            st = self.sts[ln - 1]
        else:
            st = PyLnSt.Null
        assert st != PyLnSt.Unknown
        self.buf[ln] = []
        s = self.text[ln]
        res = self.buf[ln]
        x = 0

        if PyLnSt.StrPass.value <= st.value <= PyLnSt.Str2Long.value:
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
            st = PyLnSt.Null

        # 词进式，每次一个单词
        while x < len(s):
            if s[x].isalnum() or s[x] == "_":
                q = ""
                while x < len(s) and (s[x].isalnum() or s[x] == "_"):
                    q += s[x]
                    x += 1
                if st == PyLnSt.AfterDef:
                    idtp = PyTok.Func
                    st = PyLnSt.Null
                elif st == PyLnSt.AfterClass:
                    idtp = PyTok.Class
                    st = PyLnSt.Null
                elif q in pyKwSet:
                    idtp = PyTok.Keyword
                    if q == "def":
                        st = PyLnSt.AfterDef
                    elif q == "class":
                        st = PyLnSt.AfterClass
                elif q.isdecimal():
                    idtp = PyTok.Num
                elif q in pyClassSet:
                    idtp = PyTok.Class
                elif q in pyFuncSet:
                    idtp = PyTok.Func
                else:
                    idtp = PyTok.Id
                for i in range(len(q)):
                    res.append(idtp)
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
                st = PyLnSt.Null
            elif s[x] in pyOpSet:
                x += 1
                res.append(PyTok.Op)
                st = PyLnSt.Null
            elif s[x] == "#":
                while x < len(s):
                    x += 1
                    res.append(PyTok.Comment)
                st = PyLnSt.Null
            else:
                x += 1
                res.append(PyTok.Other)
        return st

    def render(self, target: int):
        assert target < len(self.text)
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
        self.render(y)
        return pyTokDict[self.buf[y][x].value]
