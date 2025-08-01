from utils import colorcvt, cvt_truecolor, copy_structure, stylecvt, ed_getch
import copy


class Renderer:
    def __init__(self, text: list[str]):
        self.text = text
        self.change_points = []
        self.states: list[list[int]] = copy_structure(text, fill=-1)
        self.results: list[list[int]] = copy_structure(text, fill=-1)

    def insert(self, y: int, x: int, text: str):
        self.change_points.append((y, x))
        for data in (self.states, self.results):
            for ch in text:
                tmp = 0
                if ch == "\n":
                    data.insert(y + 1, data[y][x:])
                    data[y] = data[y][:x] + [-1] * tmp
                    y += 1
                    x = 0
                    tmp = 0
                elif ch == "\r":
                    pass
                else:
                    tmp += 1

    def delete(self, y: int, x: int, q: int, p: int):
        self.change_points.append((y, x))
        for data in (self.states, self.results):
            if y == q:
                if p == len(data[y]):
                    data[y] = data[y][:x]
                    if y + 1 < len(data):
                        data[y] += data[y + 1]
                        del data[y + 1]
                else:
                    data[y] = data[y][:x] + data[y][p + 1 :]
            else:
                data[y] = data[y][:x]
                del data[y + 1 : q]
                if p == len(data[y + 1]):
                    del data[y + 1]
                else:
                    data[y + 1] = data[q][p + 1 :]
                if y + 1 < len(data):
                    data[y] += data[y + 1]
                    del data[y + 1]

    def render(self, ln: int, col: int):
        ...

    def get(self, y: int, x: int) -> str:
        return "text"

    def clear(self):
        self.change_points = []
        self.states = [[]]
        self.results = [[]]

    def get_indent(self, y: int) -> str:
        return ""


class Theme:
    def __init__(self, d: dict):
        self.d = copy.deepcopy(d)
        for i in self.d:
            color = self.d[i]
            while isinstance(color, str):
                color = d[color]
            self.d[i] = colorcvt(color[0]), colorcvt(color[1]), [] if len(color) == 2 else stylecvt(color[2])

    def get(self, token: str, insel: bool):
        style = self.d[token][2]
        if insel:
            if self.d[token][1] == self.d["sel"][0]:
                return cvt_truecolor(self.d["sel"][0], self.d["bg"][1], style)
            return cvt_truecolor(self.d["sel"][0], self.d[token][1], style)
        if self.d[token][0] != 0:
            return cvt_truecolor(self.d[token][0], self.d[token][1], style)
        return cvt_truecolor(self.d["bg"][0], self.d[token][1], style)


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
    "kwfunc": (0x282C34, 0xC678DD),
    "kwclass": (0x282C34, 0xC678DD),
    "kwpreproc": (0x282C34, 0xC678DD),
    "kwcond": (0x282C34, 0xC678DD),
    "kwrepeat": (0x282C34, 0xC678DD),
    "kwreturn": (0x282C34, 0xC678DD),
    "kwcoroutine": (0x282C34, 0xC678DD),
    "kwexception": (0x282C34, 0xC678DD),
    "str": (0x282C34, 0x98C379),
    "escape": (0x282C34, 0x56B6C2),
    "const": (0x282C34, 0xD19A66),
    "comment": (0x282C34, 0x5C6370),
    "op": (0x282C34, 0xABB2BF),
    "func": (0x282C34, 0x61AFEF),
    "class": (0x282C34, 0xE5C07B),
    "module": (0x282C34, 0xE5C07B),
    "field": (0x282C34, 0xE06C75),
    "param": (0x282C34, 0xD19A66),
    "thisparam": (0x282C34, 0xD19A66),
    "error": (0xFF0000, 0xABB2BF),
    "modeline": (0x3E4452, 0xABB2BF),
    "completion": (0x242830, 0xABB2BF),
    "completion_selected": (0x3E4452, 0xABB2BF),
    "border": (0x282C34, 0xABB2BF),
}

tokyonight_storm_theme = {
    "bg": (0x24283B, 0x000000),
    "text": (0x24283B, 0xC0CAF5),
    "id": (0x24283B, 0xC0CAF5),
    "sel": (0x3D59A1, 0x000000),
    "cursor": (0x528BFF, 0x528BFF),
    "linum": (0x24283B, 0x495162),
    "num": (0x24283B, 0xFF9E64),
    "kw": (0X24283B, 0x9D7CD8, ["italic"]),
    "kwfunc": (0X24283B, 0xBB9AF7),
    "kwclass": "kw",
    "kwpreproc": (0x24283B, 0x7DCFFF),
    "kwcond": "kwfunc",
    "kwrepeat": "kwfunc",
    "kwreturn": "kw",
    "kwcoroutine": "kw",
    "kwexception": "kw",
    "str": (0x24283B, 0x9ECE6A),
    "escape": (0x24283B, 0xC099FF),
    "const": (0x24283B, 0xFF966C),
    "comment": (0x24283B, 0x565f89),
    "op": (0x24283B, 0x89DDFF),
    "func": (0x24283B, 0x7AA2F7),
    "class": (0x24283B, 0x2AC3DE),
    "module": (0x24283B, 0x82AAFF),
    "field": (0x24283B, 0x73DACA),
    "param": (0x24283B, 0xE0AF68),
    "thisparam": (0x24283B, 0xFF757F),
    "error": (0xFF0000, 0xC0CAF5),
    "modeline": (0x3B4261, 0xC0CAF5),
    "completion": (0x242830, 0xC0CAF5),
    "completion_selected": (0x3D59A1, 0xC0CAF5),
    "border": (0x24283B, 0xC0CAF5),
}

themes = {
    "onedark": onedark_theme,
    "tokyonight-storm": tokyonight_storm_theme,
}

default_theme = tokyonight_storm_theme
