from .python import PythonRenderer
from .plaintext import PlainTextRenderer

renderers_table: dict[str, type] = {
    'py': PythonRenderer,
}


def get_renderer(ft: str = '') -> type:
    return renderers_table.get(ft, PlainTextRenderer)
