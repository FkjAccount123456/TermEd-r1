from renderer import Renderer


class PlainTextRenderer(Renderer):
    def __init__(self, text: list[str]): ...

    def insert(self, *_): ...

    def delete(self, *_): ...

    def clear(self): ...
