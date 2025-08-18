"""
好久不写语言了，不过Lisp系的Parser实在再简单不过
不过还有现成的TL2
"""

import os


def tokenize(code: str) -> list[str]:
    pos = 0
    res = []

    while pos < len(code):
        while pos < len(code) and code[pos] in ' \n\r\t;':
            if code[pos] == ';':
                while pos < len(code) and code[pos] not in '\r\n':
                    pos += 1
            else:
                pos += 1
        if pos >= len(code):
            break
        elif code[pos] == '"':
            pos += 1
            s = '"'
            while pos < len(code) and code[pos] != '"':
                if code[pos] == '\\':
                    s += code[pos]
                    pos += 1
                s += code[pos]
                pos += 1
            if pos >= len(code):
                raise
            pos += 1
            s += '"'
            res.append(s)
        elif code[pos] in '()\',[]':
            res.append(code[pos])
            pos += 1
        elif code[pos].isdigit():
            num = ''
            while pos < len(code) and (code[pos].isdigit() or code[pos] == '.'):
                num += code[pos]
                pos += 1
            res.append(num)
        else:
            s = ""
            while pos < len(code) and code[pos] not in ' \n\t()\',";[]':
                s += code[pos]
                pos += 1
            res.append(s)
    return res + [""]


class List:
    def __init__(self, val: list):
        self.val = val

    __repr__ = __str__ = lambda self: f"({', '.join(map(str, self.val))})"  # type: ignore


class Symbol:
    def __init__(self, name: str):
        self.name = name

    __repr__ = __str__ = lambda self: f"'{self.name}"  # type: ignore


def parse(tokens: list[str]):
    pos = 0

    def parse():
        nonlocal pos
        if tokens[pos] == '':
            raise
        elif tokens[pos] == '(':
            pos += 1
            res = []
            while tokens[pos] != ')':
                res.append(parse())
            if tokens[pos] != ')':
                raise
            pos += 1
            return res
        elif tokens[pos] == '[':
            pos += 1
            res = []
            while tokens[pos] != ']':
                res.append(parse())
            if tokens[pos] != ']':
                raise
            pos += 1
            return List(res)
        elif tokens[pos][0] == '"':
            s = tokens[pos][1: -1]
            pos += 1
            return s
        elif tokens[pos][0].isdigit():
            num = tokens[pos]
            pos += 1
            if '.' in num:
                return float(num)
            else:
                return int(num)
        else:
            s = tokens[pos]
            pos += 1
            return Symbol(s)

    res = []
    while pos < len(tokens) and tokens[pos] != '':
        res.append(parse())
    return res



unicode_property_map = {
    r'\pL': r'[a-zA-Z\u00C0-\u02AF\u0370-\u1FFF]',
    r'\p{Ll}': r'[a-z\u00E0-\u00FF]',
    r'\p{Lu}': r'[A-Z\u00C0-\u00DE]',
    r'\pN': r'[0-9\u0660-\u0669\u06F0-\u06F9]',
    r'\pP': r'[!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~]',
    r'\s': r'[ \t\n\r\f\v]',
}

lua_to_rust = {
    '%a': unicode_property_map[r'\pL'],
    '%l': unicode_property_map[r'\p{Ll}'],
    '%u': unicode_property_map[r'\p{Lu}'],
    '%d': r'[0-9]',
    '%w': r'[a-zA-Z0-9_]',
    '%s': unicode_property_map[r'\s'],
    '%p': unicode_property_map[r'\pP'],
    '%A': f'[^{unicode_property_map[r"\pL"][1:-1]}]',
    '%D': r'[^0-9]',
    '%W': r'[^a-zA-Z0-9_]',
    '%S': f'[^{unicode_property_map[r"\s"][1:-1]}]',
    '%.': r'\.',
    '%%': r'%',
    '%+': r'\+',
    '%*': r'\*',
    '%?': r'\?',
    '%^': r'\^',
    '%$': r'\$',
    '%(': r'\(',
    '%)': r'\)',
    '%[': r'\[',
    '%]': r'\]',
}


def trans_regex(s: str) -> str:
    res = ""
    i = 0
    xbr = 0
    while i < len(s):
        if s[i] == '%':
            rust = lua_to_rust.get(s[i: i+2], s[i])
            if rust[0] == '[' and xbr == 1:
                rust = rust[1:-1]
            res += rust
            i += 1
        else:
            res += s[i]
            if s[i] == '[':
                xbr += 1
            elif s[i] == ']':
                xbr -= 1
        i += 1
    return res


def rebuild(tree) -> str:
    if isinstance(tree, list):
        if isinstance(tree[0], Symbol) and tree[0].name == '#lua-match?':
            return f"(#match? {rebuild(tree[1])} \"{trans_regex(tree[2])}\")"
        if isinstance(tree[0], Symbol) and tree[0].name == '#set!' and len(tree) == 4:
            del tree[1]
        return "(" + " ".join(map(rebuild, tree)) + ")"
    elif isinstance(tree, str):
        return '"' + tree + '"'
    elif isinstance(tree, int) or isinstance(tree, float):
        return str(tree)
    elif isinstance(tree, Symbol):
        return tree.name
    elif isinstance(tree, List):
        return '[' + " ".join(map(rebuild, tree.val)) + ']'
    raise


def read_scm(lang) -> str:
    scm_file = os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        "external/nvim-treesitter/queries",
        lang,
        "highlights.scm",
    )
    with open(scm_file, "r", encoding="utf-8") as f:
        queries = f.read()
    return queries


def preprocess_query(query_text: str) -> str:
    if query_text.startswith('; inherits: '):
        inherits = query_text[12 : query_text.find('\n')].split(',')
        for i in inherits:
            query_text = read_scm(i) + query_text
    tree = parse(tokenize(query_text))
    return '\n'.join(map(rebuild, tree))


if __name__ == '__main__':
    query_text = open('external/nvim-treesitter/queries/xml/highlights.scm', 'r', encoding='utf-8').read()
    print(preprocess_query(query_text).split('\n')[33])
