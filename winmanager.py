from editor import Editor


class EdWindow:
    def __init__(self, parent: "EdWindow | None", leftop: tuple[int, int], h: int, w: int):
        self.parent, self.leftop, self.h, self.w = parent, leftop, h, w

    def draw(self):
        ...

    def resize(self, h: int, w: int):
        ...

    def move(self, leftop: tuple[int, int]):
        ...

    # 默认分一半，本Window留在左上
    def split(self, d: bool):
        ...


class EdSplit(EdWindow):
    def __init__(self, parent: "EdWindow | None", leftop: tuple[int, int], h: int, w: int, sp_d: bool, sp_pos: int, sp_1: EdWindow, sp_2: EdWindow):
        super().__init__(parent, leftop, h, w)
        self.sp_d, self.sp_pos = sp_d, sp_pos  # T: WS F: AD
        self.sp_1, self.sp_2 = sp_1, sp_2

    def draw(self):
        self.sp_1.draw()
        self.sp_2.draw()

    # 倒是令我想起那个矩形旋转的三角函数实现
    def resize(self, h: int, w: int):
        if self.sp_d:  # 纵向等比例
            h1 = int(self.sp_1.h / (self.sp_1.h + self.sp_2.h) * h)
            self.sp_1.resize(h1, w)
            self.sp_2.resize(h - h1, w)
        else:  # 横向等比例
            w1 = int(self.sp_1.w / (self.sp_1.w + self.sp_2.w) * w)
            self.sp_1.resize(h, w1)
            self.sp_2.resize(h, w - w1)

    def move(self, leftop: tuple[int, int]):
        sh = self.leftop[0] - leftop[0], self.leftop[1] - leftop[1]
        self.sp_1.move((self.sp_1.leftop[0] + sh[0], self.sp_1.leftop[1] + sh[1]))
        self.sp_2.move((self.sp_2.leftop[0] + sh[0], self.sp_2.leftop[1] + sh[1]))
        self.leftop = leftop


class EdBuffer(EdWindow):
    def __init__(self, parent: "EdWindow | None", leftop: tuple[int, int], h: int, w: int, editor: Editor):
        super().__init__(parent, leftop, h, w)
        self.editor = editor

    def draw(self):
        ...

    def resize(self, h: int, w: int):
        self.h, self.w = h, w

    def move(self, leftop: tuple[int, int]):
        self.leftop = leftop
