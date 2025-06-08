import keyword

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

# 奇妙bitmask
AfterImport = 1 << 0
AfterDef = 1 << 1
AfterClass = 1 << 2
AfterDot = 1 << 3
AfterThArrow = 1 << 4
AfterThColon = 1 << 5
AfterTh = 3 << 4
# 6w层够了吧（
ParenLv = 0xFFFF << 6
BrcktLv = 0xFFFF << 22
BraceLv = 0xFFFF << 38
AnyParen = 0xFFFFFFFFFFFF << 6
# 完了这些忘了
StrLong = 1 << 54
Str2Long = 1 << 55
StrCont = 1 << 56
Str2Cont = 1 << 57
AnyStr = 0xF << 54
AnyStrLong = 0x3 << 54
AnyStrCont = 0x3 << 56

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
