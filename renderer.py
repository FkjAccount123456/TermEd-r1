from colorama import Fore, Back, Style

from utils import colorcvt, cvt_truecolor


class Renderer:
    def __init__(self, text: list[str]):
        self.text = text
        self.ukb = 0  # Unknown-begin [0, ukb)
        self.chs = [False for _ in range(len(self.text))]  # Changes
        self.sts = []

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
        for i in self.d:
            self.d[i] = colorcvt(self.d[i][0]), colorcvt(self.d[i][1])

    def format(self, base, text):
        return cvt_truecolor(text[1], base[0])

    def get(self, token: str, insel: bool, incursor: bool):
        if incursor:
            if self.d[token] == self.d["cursor"]:
                return self.format(self.d["cursor"], self.d["bg"])
            return self.format(self.d["cursor"], self.d[token])
        if insel:
            if self.d[token] == self.d["sel"]:
                return self.format(self.d["sel"], self.d["bg"])
            return self.format(self.d["sel"], self.d[token])
        return self.format(self.d["bg"], self.d[token])


# 懒得写了
# gruvbox_theme = {
#     "bg": (0x282828, 0x000000),
#     "text": (0x282828, 0xEBDBB2),
#     "id": (0x282828, 0xEBDBB2),
#     "sel": (0x3C3836, 0x000000),
#     "cursor": (0xEBDBB2, 0xEBDBB2),
#     "linum": (0x282828, 0x928374),
#     "num": (0x282828, 0xD3869B),
#     "kw": (0x282828, 0xFB4934),
#     "str": (0x282828, 0xB8BB26),
#     "const": (0x282828, 0xFABD2F),
#     "comment": (0x282828, 0x928374),
#     "op": (0x282828, 0xEBDBB2),
# }

onedark_theme = {
    "bg": (0x282C34, 0x000000),
    "text": (0x282C34, 0xABB2BF),
    "id": (0x282C34, 0xABB2BF),
    "sel": (0x3E4452, 0x000000),
    "cursor": (0x528BFF, 0x528BFF),
    "linum": (0x282C34, 0x495162),
    "num": (0x282C34, 0xD19A66),
    "kw": (0x282C34, 0xC678DD),
    "str": (0x282C34, 0x98C379),
    "const": (0x282C34, 0xD19A66),
    "comment": (0x282C34, 0x5C6370),
    "op": (0x282C34, 0xABB2BF),
    "func": (0x282C34, 0x61AFEF),
    "class": (0x282C34, 0xE5C07B),
    "module": (0x282C34, 0xE5C07B),
    "field": (0x282C34, 0xE06C75),
    "param": (0x282C34, 0xD19A66),
}

default_theme = onedark_theme
