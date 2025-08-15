from renderer import Renderer
from utils import copy_structure, log
import os
from .plaintext import PlainTextRenderer
import multiprocessing as mp
import multiprocessing.reduction as mpreduction
import dill
import io


def init_mp():
    mp.freeze_support()
    original_pickler = mpreduction.ForkingPickler
    
    class PatchedPickler(original_pickler):
        @classmethod
        def dumps(cls, obj, protocol=None):
            buf = io.BytesIO()
            cls(buf, protocol).dump(obj)
            return buf.getvalue()
    
    mpreduction.ForkingPickler = PatchedPickler
    mpreduction.dumps = PatchedPickler.dumps  # type: ignore


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
    

type RenderCommand = tuple


def render_process(lang, text: list[str], cmd: mp.Queue, res: mp.Queue):
    cmdbuf = []

    def cmd_peek():
        if cmdbuf:
            return cmdbuf[-1]
        elif not cmd.empty():
            c = cmd.get()
            cmdbuf.insert(0, c)
            return c
        
    def cmd_get():
        if cmdbuf:
            return cmdbuf.pop()
        return cmd.get()

    def render_all():
        nonlocal buf, tree
        buf = copy_structure(text, fill='')
        btext = bytes('\n'.join(text), 'utf-8')
        tree = parser.parse(btext)
        return render_inrange(-1, -1)

    def render_inrange(lb: int, rb: int):
        nonlocal buf
        c = cmd_peek()
        if not c or c[0] != 'g':  # 任务上新了
            return
        if not tree:
            return
        qdict = {}
        query = QueryCursor(base_query)
        if not (lb == rb == -1):
            query.set_byte_range(lb, rb)
        captures = query.captures(tree.root_node).items()
        for group, nodes in captures:
            if group.startswith('_'):
                continue
            for node in nodes:
                qdict[(node.start_point[0], node.start_point[1], node.end_point[0], node.end_point[1])] = group
        return qdict

    def get_as_bytes(y: int, x: int):
        lb = 0
        btext = b""
        for i, line in enumerate(text):
            if i == y:
                lb += len(bytes(line[:x], 'utf-8'))
            new = bytes(line, 'utf-8') + (b'\n' if i != len(text) - 1 else b'')
            if i < y:
                lb += len(new)
            btext += new
        return btext, lb
    
    def get_as_bytes2(y: int, x: int, q: int, p: int):
        lb, rb = 0, 0
        btext = b""
        for i, line in enumerate(text):
            if i == y:
                lb += len(bytes(line[:x], 'utf-8'))
            if i == q:
                rb += len(bytes(line[:p + 1], 'utf-8'))
                if p == len(line):
                    rb += 1
            new = bytes(line, 'utf-8') + (b'\n' if i != len(text) - 1 else b'')
            if i < y:
                lb += len(new)
            if i < q:
                rb += len(new)
            btext += new
        return btext, lb, rb
    
    def _insert(y: int, x: int, ny: int, nx: int, t: str):
        data = buf
        if x > 0:
            fill = data[y][x - 1]
        else:
            tmp = y
            while tmp > 0 and not data[tmp - 1]:
                tmp -= 1
            if tmp > 0:
                fill = data[tmp - 1][-1]
            else:
                fill = ''
        tmp = 0
        for ch in t:
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

    def _delete(y: int, x: int, q: int, p: int):
        data = buf
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

    def insert(y: int, x: int, ny: int, nx: int, t: str):
        _insert(y, x, ny, nx, t)
        nonlocal tree
        textinputer.insert(y, x, t)
        if not tree:
            return
        btext, lb = get_as_bytes(y, x)
        bx = len(bytes(text[y][:x], 'utf-8'))
        bnx = len(bytes(text[y][:nx], 'utf-8'))
        tree.edit(start_point=(y, bx), old_end_point=(y, bx), new_end_point=(ny, bnx),
                  start_byte=lb, old_end_byte=lb,
                  new_end_byte=lb + len(bytes(t, 'utf-8')))
        new_tree = parser.parse(btext, tree)
        changes = new_tree.changed_ranges(tree)
        if not changes:
            tree.edit(start_point=(y, bx), old_end_point=(y, bnx), new_end_point=(ny, bnx),
                      start_byte=lb, old_end_byte=lb + len(bytes(t, 'utf-8')),
                      new_end_byte=lb + len(bytes(t, 'utf-8')))
            new_tree = parser.parse(btext, new_tree)
            changes = new_tree.changed_ranges(tree)
            if not changes:
                return
        tree = new_tree
        clb = min(map(lambda x: x.start_byte, changes))
        crb = max(map(lambda x: x.end_byte, changes))
        return render_inrange(clb, crb)

    def pre_delete(y: int, x: int, q: int, p: int):
        nonlocal bp, dbset
        bp = len(bytes(text[q][:p], 'utf-8')) + 1
        _, *dbset = get_as_bytes2(y, x, q, p)

    def delete(y: int, x: int, q: int, p: int):
        _delete(y, x, q, p)
        nonlocal tree
        if not tree:
            return
        bx = len(bytes(text[y][:x], 'utf-8'))
        lb, rb = dbset
        btext, *_ = get_as_bytes(0, 0)
        tree.edit(start_point=(y, bx), old_end_point=(q, bp), new_end_point=(y, bx),
                        start_byte=lb, old_end_byte=rb,
                        new_end_byte=lb)
        new_tree = parser.parse(btext, tree)
        changes = new_tree.changed_ranges(tree)
        tree = new_tree
        if not changes:
            return
        lb = min(map(lambda x: x.start_byte, changes))
        rb = max(map(lambda x: x.end_byte, changes))
        return render_inrange(lb, rb)

    from textinputer import TextInputer
    from tree_sitter_language_pack import get_parser, get_language, SupportedLanguage
    from tree_sitter import QueryCursor, Query
    queries = read_scm(lang)
    queries = preprocess_query(queries)
    parser = get_parser(lang)
    language = get_language(lang)
    base_query = Query(language, queries)

    textinputer = TextInputer(None)
    textinputer.insert(0, 0, '\n'.join(text), True)
    text = textinputer.text
    buf = []
    tree = None
    bp = 0
    dbset = 0, 0
    update_dict = render_all()
    if not update_dict:
        update_dict = {}

    while True:
        c = cmd_get()
        if c[0] == 'a':
            update_dict = render_all()
            if not update_dict:
                update_dict = {}
        elif c[0] == 'i':
            qdict = insert(*c[1:])
            if qdict:
                for k, v in qdict.items():
                    update_dict[k] = v
        elif c[0] == 'd':
            pre_delete(*c[1:])
            textinputer.delete(*c[1:])
            qdict = delete(*c[1:])
            if qdict:
                for k, v in qdict.items():
                    update_dict[k] = v
        elif c[0] == 'g':
            res.put(list(update_dict.items()))
            update_dict = {}


def gen_renderer(lang) -> type[Renderer]:
    class Res(Renderer):
        def __init__(self, text: list[str]):
            super().__init__(text, '')
            self.cmd = mp.Queue()
            self.res = mp.Queue()
            self.renderer = mp.Process(target=render_process, args=(lang, text, self.cmd, self.res), daemon=True)
            self.renderer.start()
            self.buf = copy_structure(text, fill='')
            self.all_tochange.append(self.buf)
            self.need_render = True

        def render_all(self, *_):
            self.cmd.put(('a',))
            self.need_render = True

        def insert(self, y: int, x: int, q: int, p: int, text: str):
            super().insert(y, x, q, p, text)
            self.cmd.put(('i', y, x, q, p, text))
            self.need_render = True

        def delete(self, y: int, x: int, q: int, p: int):
            super().delete(y, x, q, p)
            self.cmd.put(('d', y, x, q, p))
            self.need_render = True
        
        def render(self, *_):
            pass

        def check_update(self):
            return not self.res.empty()
        
        def get(self, y: int, x: int) -> str:
            ry, rx = y, x
            if self.need_render:
                self.need_render = False
                self.cmd.put(('g',))
            if not self.res.empty():
                buf, text = self.buf, self.text
                updates = self.res.get()
                for (y, x, q, p), group in updates:
                    x = calc_unicodex(text[y], x)
                    p = calc_unicodex(text[q], p)
                    while (y, x) < (q, p):
                        if x < len(buf[y]):
                            buf[y][x] = group
                        x += 1
                        if x >= len(buf[y]):
                            y, x = y + 1, 0
            return self.buf[ry][rx]

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
