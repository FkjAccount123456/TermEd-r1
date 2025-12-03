from utils import colorcvt, cvt_truecolor, stylecvt, get_char_type
import copy
import indents


class Renderer:
    def __init__(self, parent, text: list[str], fill=None):
        self.parent = parent
        self.fill = fill
        self.text = text
        self.all_tochange = []
        self.ft = 'text'

    def render_all(self):
        ...

    def pre_insert(self, y: int, x: int, text: str):
        ...

    def pre_delete(self, y: int, x: int, q: int, p: int):
        ...

    def insert(self, y: int, x: int, q: int, p: int, text: str):
        if not text:
            return
        tp1 = get_char_type(text[0])
        tp2 = get_char_type(text[-1])
        oy, ox = y, x
        tmp = 0
        for ch in text:
            if ch == "\n":
                y += 1
                tmp = 0
            else:
                tmp += 1
        if tmp:
            x += tmp
        rx, ry = x, y
        for data in self.all_tochange:
            y, x = oy, ox
            if x > 0:
                if rx < len(self.text[ry]) and get_char_type(self.text[ry][rx]) == tp2\
                        and get_char_type(self.text[y][x - 1]) != tp1:
                    fill = data[y][x]
                else:
                    fill = data[y][x - 1]
            elif x < len(data[y]):
                fill = data[y][x]
            else:
                fill = self.fill
            tmp = 0
            for ch in text:
                if ch == "\n":
                    data.insert(y + 1, data[y][x:])
                    data[y] = data[y][:x] + [fill] * tmp
                    y += 1
                    x = 0
                    tmp = 0
                else:
                    tmp += 1
            if tmp:
                data[y] = data[y][:x] + [fill] * tmp + data[y][x:]
                x += tmp
        return y, x

    def delete(self, y: int, x: int, q: int, p: int):
        for data in self.all_tochange:
            if y == q:
                if p == len(data[y]):
                    data[y] = data[y][:x]
                    if y + 1 < len(data):
                        data[y] += data[y + 1]
                        del data[y + 1]
                else:
                    data[y] = data[y][:x] + data[y][p + 1:]
            else:
                data[y] = data[y][:x]
                del data[y + 1: q]
                if p == len(data[y + 1]):
                    del data[y + 1]
                else:
                    data[y + 1] = data[q][p + 1:]
                if y + 1 < len(data):
                    data[y] += data[y + 1]
                    del data[y + 1]

    def render(self, ln: int, col: int):
        ...

    def check_update(self) -> bool:
        return False

    def get(self, y: int, x: int) -> str:
        return "text"

    def clear(self):
        self.change_points = []
        for i in self.all_tochange:
            i.clear()
            i.append([])

    def get_one_indent(self):
        return ' ' * self.parent.settings.tab_width if self.parent.settings.expand_tab else '\t'

    def get_cur_indent(self, y: int):
        s = ""
        for i in self.text[y]:
            if i.isspace():
                s += i
            else:
                break
        return s

    def get_first_word(self, y: int):
        if not self.text[y]:
            return ''
        for i, ch in enumerate(self.text[y]):
            if not ch.isspace():
                break
        s = ""
        for i in range(i, len(self.text[y])):
            if ch.isalnum() or ch == '_':
                s += self.text[y][i]
            else:
                break
        return s

    def get_indent(self, y: int, x: int) -> list[str]:
        config = indents.indent_configs.get(
            self.ft, indents.indent_configs[''])
        if not config:
            return ['i\n']
        if config[0] == 'c':
            return self.cstyle_indent(y, x, *config[1:])
        if config[0] == 'lisp':
            return self.lisp_indent(y, x, *config[1:])
        return ['i\n']

    def lisp_indent(self, y: int, x: int, indent_kws: list[str]) -> list[str]:
        pairlevel = 0
        i = y
        for j in range(x - 1, -1, -1):
            if self.text[i][j] in ')]}':
                pairlevel += 1
            elif self.text[i][j] in '([{':
                pairlevel -= 1
                if pairlevel == -1:
                    break
        else:
            for i in range(y - 1, -1, -1):
                for j in range(len(self.text[i]) - 1, -1, -1):
                    if self.text[i][j] in ')]}':
                        pairlevel += 1
                    elif self.text[i][j] in '([{':
                        pairlevel -= 1
                        if pairlevel == -1:
                            break
            else:
                return ['i\n' + self.get_cur_indent(y)]
        word = ""
        for k in self.text[i][j + 1:]:
            if k.isalnum() or k == '_':
                word += k
            else:
                break
        if word in indent_kws:
            return ['i\n' + ' ' * j + self.get_one_indent()]
        return ['i\n' + ' ' * j + ' ']

    def cstyle_indent(self, y: int, x: int, indent_kws: list[str], indent_chs: str) -> list[str]:
        if x == 0:
            return ['i\n']
        if self.text[y][x - 1] in indent_chs:
            return ['i\n' + self.get_cur_indent(y) + self.get_one_indent()]
        if self.get_first_word(y) in indent_kws:
            return ['i\n' + self.get_cur_indent(y) + self.get_one_indent()]
        return ['i\n' + self.get_cur_indent(y)]


class Theme:
    def __init__(self, d: dict):
        self.d = copy.deepcopy(d)
        for i in self.d:
            color = self.d[i]
            while isinstance(color, str):
                color = d[color]
            self.d[i] = colorcvt(color[0]), colorcvt(
                color[1]), [] if len(color) == 2 else stylecvt(color[2])

    def __getitem__(self, item):
        return self.d.get(item, self.d["text"])

    def get(self, token: str, insel: bool, cursorline: bool = False):
        style = self[token][2]
        if insel:
            if self[token][1] == self["sel"][0]:
                return cvt_truecolor(self["sel"][0], self["bg"][1], style)
            return cvt_truecolor(self["sel"][0], self[token][1], style)
        if cursorline:
            if self[token][1] == self["cursorline"][0]:
                return cvt_truecolor(self["cursorline"][0], self["bg"][1], style)
            return cvt_truecolor(self["cursorline"][0], self[token][1], style)
        if self[token][0] != 0:
            return cvt_truecolor(self[token][0], self[token][1], style)
        return cvt_truecolor(self["bg"][0], self[token][1], style)


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


def trans_token(t: str):
    if t in ts_compat:
        return ts_compat[t]
    return t


ts_compat = {
    "keyword": "kw",
    "keyword.type": "kwclass",
    "keyword.function": "kwfunc",
    "keyword.operator": "op",
    "keyword.return": "kwreturn",
    "keyword.repeat": "kwrepeat",
    "keyword.coroutine": "kwcoroutine",
    "keyword.exception": "kwexception",
    "keyword.conditional": "kwcond",
    "keyword.directive": "kwpreproc",
    "keyword.directive.define": "kwpreproc",
    "keyword.import": "kwpreproc",
    "keyword.control": "kw",
    "keyword.control.import": "kwpreproc",
    "keyword.control.exception": "kwexception",
    "keyword.control.conditional": "kwcond",
    "keyword.control.return": "kwreturn",
    "keyword.control.repeat": "kwrepeat",
    "keyword.storage.type": "kw",
    "keyword.storage.modifier": "kw",
    "keyword.storage.class": "kwclass",
    "keyword.storage.function": "kwfunc",
    "keyword.storage.namespace": "kw",
    "namespace": "module",
    "module.builtin": "module",
    "punctuation.delimiter": "op",
    "punctuation.special": "op",
    "punctuation.bracket": "op",
    "operator": "op",
    "boolean": "const",
    "keyword.conditional.ternary": "kwcond",
    "string": "str",
    "string.escape": "escape",
    "constant.builtin": "const",
    "constant.numeric.integer": "num",
    "constant.numeric": "num",
    "constant.character": "str",
    "constant.character.escape": "escape",
    "constant.builtin.boolean": "const",
    "type.enum.variant": "const",
    "number": "num",
    "number.float": "num",
    "character": "str",
    "function.macro": "const",  # 待定
    "function.special": "func",
    "function.method": "func",
    "property": "field",
    "_parent": "field",
    "template_method": "func",
    "function_declarator": "func",
    "field_declaration": "field",
    "variable.member": "field",
    "variable.other.member": "field",
    "label": "id",
    "type": "class",
    "keyword.modifier": "kw",
    "type.definition": "class",
    "type.builtin": "class",
    "constant": "const",
    "variable.builtin": "thisparam",
    "function.builtin": "func",
    "constant.macro": "const",  # 待定
    "function.call": "func",
    "function.method.call": "func",
    "spell": "comment",
    "comment.documentation": "comment",
    "variable.parameter": "param",
    "attribute": "kw",
    "attribute.builtin": "kw",
    "function": "func",
    "character.special": "id",
    "constructor": "func",
    "variable": "id",
    "string.documentation": "str",
    "re": "str",
    "string.regexp": "str",
    "none": "text",
    "": "text",
}

onedark_theme = {
    "bg": (0x282C34, 0x000000),
    "text": (0x282C34, 0xABB2BF),
    "id": (0x282C34, 0xABB2BF),
    "sel": (0x3E4452, 0x000000),
    "cursor": (0x528BFF, 0x528BFF),
    "cursorline": (0x2C313C, 0x000000),
    "curlinum": (0x282C34, 0x737984),
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
} | ts_compat

tokyonight_storm_theme = {
    "bg": (0x24283B, 0x000000),
    "text": (0x24283B, 0xC0CAF5),
    "id": (0x24283B, 0xC0CAF5),
    "sel": (0x3D59A1, 0x000000),
    "cursor": (0x528BFF, 0x528BFF),
    "cursorline": (0x292E41, 0x000000),
    "curlinum": (0x24283B, 0x8089b3),
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
} | ts_compat

monokai_theme = {
    "bg": (0x26292C, 0x000000),
    "text": (0x26292C, 0xF8F8F0),
    "id": (0x26292C, 0xF8F8F0),
    "sel": (0x333842, 0x000000),
    "cursor": (0x528BFF, 0xF8F8F0),
    "cursorline": (0x3E3D33, 0x000000),
    "curlinum": (0x26292C, 0x2196F3),
    "linum": (0x26292C, 0x4D5154),
    "num": (0x26292C, 0xAE81FF),
    "kw": (0x26292C, 0xF92672),
    "kwfunc": (0X26292C, 0x66D9EF),
    "kwclass": "kw",
    "kwpreproc": "kw",
    "kwcond": "kw",
    "kwrepeat": "kw",
    "kwreturn": "kw",
    "kwcoroutine": "kw",
    "kwexception": "kw",
    "str": (0x26292C, 0xE6DB74),
    "escape": (0x26292C, 0xAE81FF),
    "const": (0x26292C, 0x66D9EF),
    "comment": (0x26292C, 0x9CA0A4, ["italic"]),
    "op": (0x26292C, 0xF92672),
    "func": (0x26292C, 0xA6E22E),
    "class": (0x26292C, 0x66D9EF),
    "module": (0x26292C, 0x66D9EF),
    "field": "id",
    "param": (0x26292C, 0xFD971F),
    "thisparam": (0x26292C, 0xFD971F),
    "error": (0xFF0000, 0xF8F8F0),
    "modeline": (0x3B4261, 0xF8F8F0),
    "completion": (0x26292C, 0xF8F8F0),
    "completion_selected": (0xFD971F, 0xF8F8F0),
    "border": (0x26292C, 0xF8F8F0),
} | ts_compat

catppuccin_mocha_theme = {
    "bg": (0x1E1E2E, 0x000000),
    "text": (0x1E1E2E, 0xCDD6F4),
    "id": (0x1E1E2E, 0xCDD6F4),
    "sel": (0x45475A, 0x000000),
    "cursor": (0xCDD6F4, 0x24283B),
    "cursorline": (0x2B2B3B, 0x000000),
    "curlinum": (0x1E1E2E, 0xcba6f7),
    "linum": (0x1E1E2E, 0x45475A),
    "num": (0x1E1E2E, 0xFAB387),
    "kw": (0x1E1E2E, 0xCBA6F7),
    "kwfunc": "kw",
    "kwclass": "kw",
    "kwpreproc": "kw",
    "kwcond": "kw",
    "kwrepeat": "kw",
    "kwreturn": "kw",
    "kwcoroutine": "kw",
    "kwexception": "kw",
    "str": (0x1E1E2E, 0xA6E3A1),
    "escape": (0x1E1E2E, 0xF5C2E7),
    "const": (0x1E1E2E, 0xFAB387),
    "comment": (0x1E1E2E, 0x9399B2, ["italic"]),
    "op": (0x1E1E2E, 0x89DCEB),
    "func": (0x1E1E2E, 0x89B4FA),
    "class": (0x1E1E2E, 0xF9E2AF),
    "module": (0x1E1E2E, 0xB4BEFE, ["italic"]),
    "field": (0x1E1E2E, 0xEA9FAC),
    "param": (0x1E1E2E, 0xEBA0AC),
    "thisparam": (0x1E1E2E, 0xF38BA8),
    "error": (0xFF0000, 0xCDD6F4),
    "modeline": (0x313244, 0xCDD6F4),
    "completion": (0x2B2B3C, 0xCDD6F4),
    "completion_selected": (0x45475A, 0xCDD6F4),
    "border": (0x1E1E2E, 0xCDD6F4),
} | ts_compat

themes = {
    "One Dark": onedark_theme,
    "Tokyo Night Storm": tokyonight_storm_theme,
    "Monokai": monokai_theme,
    "Catppuccin Mocha": catppuccin_mocha_theme,
}

default_theme = tokyonight_storm_theme
