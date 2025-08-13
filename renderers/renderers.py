from renderer import Renderer
from utils import copy_structure
from tree_sitter_language_pack import get_parser, get_language, SupportedLanguage
from tree_sitter import QueryCursor, Query
import os
from .plaintext import PlainTextRenderer


def read_scm(lang: SupportedLanguage) -> str:
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


def preprocess_query(query_text):
    processed = query_text.replace("#lua-match?", "#match?")
    if query_text.startswith("; inherits: "):
        inherits = query_text[12 : query_text.find("\n")].split(',')
        for i in inherits:
            processed += '\n' + preprocess_query(read_scm(i.strip()))
    return processed


def calc_unicodex(s: str, x: int):
    try:
        return len(s.encode("utf-8")[:x].decode("utf-8"))
    except Exception as e:
        print((s, x, len(s.encode())))
        raise e


def gen_renderer(lang: SupportedLanguage) -> type[Renderer]:
    queries = read_scm(lang)
    queries = preprocess_query(queries)
    parser = get_parser(lang)
    language = get_language(lang)
    base_query = Query(language, queries)

    class Res(Renderer):
        def __init__(self, text: list[str]):
            super().__init__(text, '')
            self.render_all()
            self.all_tochange.append(self.buf)

        def render_all(self, *_):
            self.buf = copy_structure(self.text, fill='')
            text = bytes('\n'.join(self.text), 'utf-8')
            self.tree = parser.parse(text)
            self.render_inrange(-1, -1)

        def get_as_bytes(self, y: int, x: int):
            lb = 0
            btext = b""
            for i, line in enumerate(self.text):
                if i == y:
                    lb += len(bytes(line[:x], 'utf-8'))
                new = bytes(line, 'utf-8') + (b'\n' if i != len(self.text) - 1 else b'')
                if i < y:
                    lb += len(new)
                btext += new
            return btext, lb

        def get_as_bytes2(self, y: int, x: int, q: int, p: int):
            lb, rb = 0, 0
            btext = b""
            for i, line in enumerate(self.text):
                if i == y:
                    lb += len(bytes(line[:x], 'utf-8'))
                if i == q:
                    rb += len(bytes(line[: p + 1], 'utf-8'))
                    if p == len(line):
                        rb += 1
                new = bytes(line, 'utf-8') + (b'\n' if i != len(self.text) - 1 else b'')
                if i < y:
                    lb += len(new)
                if i < q:
                    rb += len(new)
                btext += new
            return btext, lb, rb

        def render_inrange(self, lb: int, rb: int):
            text = self.text
            buf = self.buf
            qdict = {}
            query = QueryCursor(base_query)
            if not (lb == rb == -1):
                query.set_byte_range(lb, rb)
            captures = query.captures(self.tree.root_node).items()
            for group, nodes in captures:
                if group.startswith('_'):
                    continue
                for node in nodes:
                    qdict[
                        (
                            node.start_point[0],
                            node.start_point[1],
                            node.end_point[0],
                            node.end_point[1],
                        )
                    ] = group
            for (y, x, q, p), group in qdict.items():
                x = calc_unicodex(text[y], x)
                if x < len(buf[y]) and buf[y][x] == group:
                    continue
                p = calc_unicodex(text[q], p)
                while (y, x) < (q, p):
                    if x < len(buf[y]):
                        buf[y][x] = group
                    x += 1
                    if x >= len(buf[y]):
                        y, x = y + 1, 0

        def pre_insert(self, y: int, x: int, text: str): ...

        def insert(self, y: int, x: int, text: str):
            btext, lb = self.get_as_bytes(y, x)
            bx = len(bytes(self.text[y][:x], 'utf-8'))
            ny, nx = super().insert(y, x, text)
            bnx = len(bytes(self.text[y][:nx], 'utf-8'))
            self.tree.edit(
                start_point=(y, bx),
                old_end_point=(y, bx),
                new_end_point=(ny, bnx),
                start_byte=lb,
                old_end_byte=lb,
                new_end_byte=lb + len(bytes(text, 'utf-8')),
            )
            new_tree = parser.parse(btext, self.tree)
            changes = new_tree.changed_ranges(self.tree)
            self.tree = new_tree
            if not changes:
                return
            clb = min(map(lambda x: x.start_byte, changes))
            crb = max(map(lambda x: x.end_byte, changes))
            self.render_inrange(clb, crb)

        def pre_delete(self, y: int, x: int, q: int, p: int):
            self.bp = len(bytes(self.text[q][:p], 'utf-8')) + 1
            _, *self.dbset = self.get_as_bytes2(y, x, q, p)

        def delete(self, y: int, x: int, q: int, p: int):
            bp = self.bp
            super().delete(y, x, q, p)
            bx = len(bytes(self.text[y][:x], 'utf-8'))
            lb, rb = self.dbset
            btext, *_ = self.get_as_bytes(0, 0)
            self.tree.edit(
                start_point=(y, bx),
                old_end_point=(q, bp),
                new_end_point=(y, bx),
                start_byte=lb,
                old_end_byte=rb,
                new_end_byte=lb,
            )
            new_tree = parser.parse(btext, self.tree)
            changes = new_tree.changed_ranges(self.tree)
            self.tree = new_tree
            if not changes:
                return
            lb = min(map(lambda x: x.start_byte, changes))
            rb = max(map(lambda x: x.end_byte, changes))
            self.render_inrange(lb, rb)

        def render(self, *_):
            pass

        def get(self, y: int, x: int) -> str:
            return self.buf[y][x]

    return Res


renderers_table: dict[str, type[Renderer]] = {
    'c': gen_renderer('c'),
    'cpp': gen_renderer('cpp'),
    'rs': gen_renderer('rust'),
    'lua': gen_renderer('lua'),
    'go': gen_renderer('go'),
    'py': gen_renderer('python'),
}
finalizers = []


def get_renderer(ft: str = '') -> type:
    return renderers_table.get(ft, PlainTextRenderer)


def finalize():
    for f in finalizers:
        f()
