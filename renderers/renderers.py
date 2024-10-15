from .python import PythonRenderer
from .plaintext import PlainTextRenderer

renderers_table = {
    'py': PythonRenderer,
}


def get_renderer(ft: str = ''):
    return renderers_table.get(ft, PlainTextRenderer)
