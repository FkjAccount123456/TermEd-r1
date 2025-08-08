import ctypes
import os
import weakref


libfzf = ctypes.cdll.LoadLibrary(os.path.dirname(__file__) + "/csrc/libfzf.so")

SizeList = ctypes.POINTER(ctypes.c_size_t)

libfzf.fuzzy_find.restype = SizeList
libfzf.fuzzy_find.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_wchar_p), ctypes.c_size_t]
libfzf.free_list.argtypes = [SizeList]


def fuzzy_find(pat: str, lst: list[str]):
    arg = (ctypes.c_wchar_p * len(lst))()
    for i, s in enumerate(lst):
        arg[i] = s
    res = libfzf.fuzzy_find(pat, arg, len(lst))
    weakref.finalize(res, libfzf.free_list, res)
    return res
