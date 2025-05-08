from .python import PythonRenderer
from .plaintext import PlainTextRenderer
from . import python

renderers_table: dict[str, type] = {
    'py': PythonRenderer,
}
finalizers = [python.finalize]


def get_renderer(ft: str = '') -> type:
    return renderers_table.get(ft, PlainTextRenderer)


def finalize():
    for f in finalizers:
        f()
