from colorama import Fore, Back, Style
from renderers.plaintext import PlainTextRenderer
from renderers.python import PythonRenderer


class Renderer:
    def __init__(self, text: list[str]):
        self.text = text
        self.ukb = 0  # Unknown-begin [0, ukb)
        self.chs = [False for _ in range(len(self.text))]  # Changes

    def change(self, ln: int):
        self.chs[ln] = True
        self.ukb = min(self.ukb, ln)
        self.chs[ln] = True

    # [begin, end]
    def add(self, begin: int, end: int):
        assert begin <= len(self.sts)
        self.ukb = min(self.ukb, begin)
        self.chs = (
            self.chs[:begin] + [True for _ in range(begin, end + 1)] + self.chs[begin:]
        )

    def rem(self, begin: int, end: int):
        assert end < len(self.sts)
        self.ukb = min(self.ukb, begin + 1)
        del self.chs[begin : end + 1]

    def render(self, target: int): ...

    def get(self, y: int, x: int) -> str:
        return "text"


class Theme:
    def __init__(self, d: dict):
        self.d = d

    def format(self, bg, fg):
        if use_darker:
            return f"\033[0;3{fg};4{bg}m"
        else:
            return f"\033[1;3{fg};4{bg}m"

    def get(self, token: str, insel: bool, incursor: bool):
        if incursor:
            if self.d[token] == self.d["cursor"]:
                return self.format(self.d["cursor"], self.d["bg"])
            return self.format(self.d["cursor"], self.d[token])
        if insel:
            if self.d[token] == self.d["sel"]:
                return self.format(self.d["sel"], self.d["bg"])
            return self.format(self.d["sel"], self.d[token])
        if self.d["bg"] == 0 and self.d[token] == 7:
            return ""
        return self.format(self.d["bg"], self.d[token])


default_theme = {
    "bg": 0,
    "text": 7,
    "id": 7,
    "sel": 4,
    "cursor": 7,
    "linum": 3,
    "num": 3,
    "kw": 5,
    "str": 2,
    "const": 4,
    "comment": 2,
    "op": 6,
}

textmate_theme = {
    "bg": 7,
    "text": 0,
    "id": 0,
    "sel": 4,
    "cursor": 0,
    "linum": 0,
    "num": 4,
    "kw": 4,
    "str": 2,
    "const": 4,
    "comment": 2,
    "op": 0,
}

default_theme = textmate_theme

use_darker = True

renderers = {
    "py": PythonRenderer,
}


def getRenderer(ft: str):
    return renderers.get(ft, PlainTextRenderer)
