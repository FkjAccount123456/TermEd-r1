from renderer import Renderer


class PlainTextRenderer(Renderer):
    def __init__(self, text: list[str]): ...

    def change(sefl, ln: int): ...

    def add(self, begin: int, end: int): ...

    def rem(self, begin: int, end: int): ...
