"""
暂时使用全文高亮
反正迟早得换Tree-sitter
1000行，30KB以内时间可控
直接用之前写的pyhl
"""
from renderer import Renderer
import ctypes
import keyword
import os

pyKwSet = set(keyword.kwlist)
pySoftKwSet = set(keyword.softkwlist)
pySelfSet = {"self", "cls"}
pyConstSet = {"True", "False", "None"}

pyOpSet = set("~!%^&*()-+=[{}]|/;:,.<>")

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
    Escape = 13
    Error = 14


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
    "escape",
    "error",
]


def ispynum(s: str):
    if s[:2] == '00':
        return False
    if s[:2] in {'0b', '0o', '0x'}:
        return all(map(lambda x: x.isdecimal() or x == '.' or ord('A') <= ord(x) <= ord('F') or ord('a') <= ord(x) <= ord('f'), s[2:]))
    return all(map(lambda x: x.isdigit() or x == '.', s))


def render(code: str):
    def find_after(c='('):
        p = pos
        while p < len(code) and (code[p].isspace() or code[p] == '\\'):
            if code[p] == '\n' and not sum(braclv):
                return False
            if code[p] == '\\':
                if p + 1 < len(code) and code[p + 1] == '\n':
                    p += 1
            p += 1
        return code[p] == c

    pos = 0
    buf: list[tuple[int, str]] = []
    braclv = [0, 0, 0]
    after_th = None
    after_dot = False
    after_class = False
    after_def = False
    after_import = False

    while pos < len(code):
        cur_token = ""
        if code[pos].isspace():
            while pos < len(code) and code[pos].isspace():
                cur_token += code[pos]
                if code[pos] == '\n' and not sum(braclv):
                    after_th = None
                    after_class = False
                    after_def = False
                    after_import = False
                pos += 1
            buf.append((PyTok.Other, cur_token))
            after_dot = False
        elif code[pos].isdigit():
            while pos < len(code) and (code[pos].isalnum() or code[pos] == "."):
                cur_token += code[pos]
                pos += 1
            if ispynum(cur_token):
                buf.append((PyTok.Num, cur_token))
            else:
                buf.append((PyTok.Error, cur_token))
            after_dot = False
        elif code[pos].isalpha() or code[pos] == "_":
            while pos < len(code) and (code[pos].isalnum() or code[pos] == "_"):
                cur_token += code[pos]
                pos += 1
            if cur_token in pyConstSet:
                tp = PyTok.Const
            elif cur_token in pyKwSet:
                tp = PyTok.Keyword
                if cur_token == "class" and braclv == [0, 0, 0]:
                    after_class = True
                elif cur_token == "def" and braclv == [0, 0, 0]:
                    after_def = True
                elif cur_token == "from" and braclv == [0, 0, 0]:
                    after_import = True
                elif cur_token == "import" and braclv == [0, 0, 0]:
                    after_import = not after_import
            elif find_after('=') and braclv[0] > 0:
                tp = PyTok.Param
            elif after_import:
                tp = PyTok.Module
            elif after_th or after_class:
                tp = PyTok.Class
            elif after_def and (find_after('=') or find_after(')')
                                or find_after(',') or find_after(':')):
                tp = PyTok.Param
            elif after_def:
                tp = PyTok.Func
            elif after_dot:
                if find_after():
                    if ord('A') <= ord(cur_token[0]) <= ord('Z') and '_' not in cur_token:
                        tp = PyTok.Class
                    else:
                        tp = PyTok.Func
                else:
                    tp = PyTok.Field
            elif cur_token in pyClassSet:
                tp = PyTok.Class
            elif cur_token in pyFuncSet:
                tp = PyTok.Func
            elif find_after():
                if ord('A') <= ord(cur_token[0]) <= ord('Z') and '_' not in cur_token:
                    tp = PyTok.Class
                else:
                    tp = PyTok.Func
            elif cur_token in pySelfSet:
                tp = PyTok.Param
            elif cur_token in pySoftKwSet:
                tp = PyTok.Keyword
            else:
                tp = PyTok.Id
            buf.append((tp, cur_token))
            after_dot = False
        elif code[pos] in "\"'":
            qc = code[pos]
            pos += 1
            cur_token += qc
            if pos < len(code) and code[pos] == qc:
                cur_token += qc
                pos += 1
                if pos < len(code) and code[pos] == qc:
                    cur_token += qc
                    pos += 1
                else:
                    buf.append((PyTok.Str, cur_token))
                    continue
            qc = cur_token
            while pos < len(code) and code[pos: pos + len(qc)] != qc:
                if code[pos] == "\\":
                    cur_token += code[pos]
                    pos += 1
                if pos < len(code):
                    cur_token += code[pos]
                    pos += 1
            if pos < len(code):
                cur_token += code[pos: pos + len(qc)]
                pos += len(qc)
            buf.append((PyTok.Str, cur_token))
            after_dot = False
        elif code[pos] in pyOpSet:
            while pos < len(code) and code[pos] in pyOpSet:
                if code[pos] == '(':
                    braclv[0] += 1
                elif code[pos] == ')' and braclv[0] > 0:
                    braclv[0] -= 1
                elif code[pos] == '[':
                    braclv[1] += 1
                elif code[pos] == ']' and braclv[1] > 0:
                    braclv[1] -= 1
                elif code[pos] == '{':
                    braclv[2] += 1
                elif code[pos] == '}' and braclv[2] > 0:
                    braclv[2] -= 1
                cur_token += code[pos]
                pos += 1
            buf.append((PyTok.Op, cur_token))
            if cur_token.endswith("->") and braclv == [0, 0, 0]:
                after_th = "->"
            elif cur_token.endswith(":") and braclv in ([0, 0, 0], [1, 0, 0]):
                after_th = ":"
            elif cur_token.endswith(":") and braclv == [0, 0, 0]:
                after_class = after_def = False
            elif cur_token.endswith(",") and after_th == ":" and braclv == [1, 0, 0]:
                after_th = None
            elif cur_token.endswith("=") and after_th == ":" and braclv in ([0, 0, 0], [1, 0, 0]):
                after_th = None
            elif cur_token.endswith(":") and after_th == "->" and braclv == [0, 0, 0]:
                after_th = None
            if cur_token.endswith(".") or cur_token.endswith("...."):
                after_dot = True
            else:
                after_dot = False
        elif code[pos] == "#":
            while pos < len(code) and code[pos] != "\n":
                cur_token += code[pos]
                pos += 1
            buf.append((PyTok.Comment, cur_token))
            after_dot = False
        elif code[pos] == '\\':
            if pos + 1 < len(code) and code[pos + 1] == '\n':
                pos += 2
                buf.append((PyTok.Other, '\\\n'))
            else:
                buf.append((PyTok.Error, '\\'))
                pos += 1
            after_dot = False
        else:
            cur_token += code[pos]
            pos += 1
            buf.append((PyTok.Error, cur_token))

    return buf


libpyhl = ctypes.cdll.LoadLibrary(os.path.dirname(__file__) + "/libpyhl.so")


class PyTokList(ctypes.Structure):
    _fields_ = [
        ("len", ctypes.c_size_t),
        ("cap", ctypes.c_size_t),
        ("data", ctypes.POINTER(ctypes.c_char)),
    ]


class PyHLRes(ctypes.Structure):
    _fields_ = [
        ("len", ctypes.c_size_t),
        ("cap", ctypes.c_size_t),
        ("data", ctypes.POINTER(PyTokList)),
    ]


libpyhl.render.restype = PyHLRes
libpyhl.render.argtypes = [ctypes.c_wchar_p, ctypes.c_size_t]


class PythonRenderer(Renderer):
    def __init__(self, text: list[str]):
        self.buf = None
        self.text = text

    def change(self, ln: int): ...

    def add(self, begin: int, end: int): ...

    def rem(self, begin: int, end: int): ...

    def set_ukb(self): ...

    # def render(self, target: int):
    #     import time
    #     import utils
    #     t = time.time()
    #     res = render('\n'.join(self.text))
    #     utils.gotoxy(47, 1)
    #     print(f"render time: {time.time() - t:.3f}s", end="")
    #     self.buf = [[]]
    #     for tp, val in res:
    #         if '\n' in val:
    #             for i in val:
    #                 if i == '\n':
    #                     self.buf.append([])
    #                 else:
    #                     self.buf[-1].append(tp)
    #         else:
    #             self.buf[-1].extend([tp] * len(val))

    # def get(self, y: int, x: int) -> str:
    #     return pyTokDict[self.buf[y][x]]

    def render(self, *_):
        if self.buf is not None:
            libpyhl.PyHLRes_free(self.buf)
        # import time
        # import utils
        # t = time.time()
        text = '\n'.join(self.text)
        self.buf = libpyhl.render(text, len(text))
        # utils.gotoxy(47, 1)
        # print(f"render time: {time.time() - t:.3f}s", end="")
        # for i, ch in enumerate(text):
        #     if ch == '\n':
        #         self.buf.append("")
        #     else:
        #         self.buf[-1] += chr(ord(pyhl_res.data[i]))

    def get(self, y: int, x: int) -> str:
        assert self.buf is not None
        # print(ord(self.buf.data[y].data[x]), y, x, end=' ')
        # print(pyTokDict[ord(self.buf.data[y].data[x])])
        return pyTokDict[ord(self.buf.data[y].data[x])]
    
    def __del__(self):
        libpyhl.PyHLRes_free(self.buf)

    def insert(self, *_): ...

    def delete(self, *_): ...

    def clear(self): ...


libpyhl.init()

# for i in ["pyKwSet", "pySoftKwSet", "pySelfSet", "pyConstSet",
#           "pyOpSet", "pyFuncSet", "pyClassSet"]:
#     exec(f"""print("// {i}")
# for j in {i}:
#     print('TABLE_INS({i}, L"' + j +'", true);')""")

def finalize():
    libpyhl.finalize()
