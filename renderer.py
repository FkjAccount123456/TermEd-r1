from utils import colorcvt, cvt_truecolor, copy_structure


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


class Theme:
    def __init__(self, d: dict):
        self.d = d
        for i in self.d:
            self.d[i] = colorcvt(self.d[i][0]), colorcvt(self.d[i][1])

    def get(self, token: str, insel: bool):
        if insel:
            if self.d[token][1] == self.d["sel"][0]:
                return cvt_truecolor(self.d["sel"][0], self.d["bg"][1])
            return cvt_truecolor(self.d["sel"][0], self.d[token][1])
        if self.d[token][0] != 0:
            return cvt_truecolor(self.d[token][0], self.d[token][1])
        return cvt_truecolor(self.d["bg"][0], self.d[token][1])


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
    "escape": (0x282C34, 0x56B6C2),
    "const": (0x282C34, 0xD19A66),
    "comment": (0x282C34, 0x5C6370),
    "op": (0x282C34, 0xABB2BF),
    "func": (0x282C34, 0x61AFEF),
    "class": (0x282C34, 0xE5C07B),
    "module": (0x282C34, 0xE5C07B),
    "field": (0x282C34, 0xE06C75),
    "param": (0x282C34, 0xD19A66),
    "error": (0xFF0000, 0xABB2BF),
    "modeline": (0x3E4452, 0xABB2BF),
    "completion": (0x282C34, 0xABB2BF),
    "completion_selected": (0x3E4452, 0xABB2BF),
}

default_theme = onedark_theme
