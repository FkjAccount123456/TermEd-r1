import editor
from os import get_terminal_size
from utils import clear
import sys
from renderers.renderers import finalize

if sys.platform == "win32":
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

editor = editor.Editor(get_terminal_size().lines, get_terminal_size().columns)
if len(sys.argv) > 1:
    editor.cur.open_file(sys.argv[1])
editor.mainloop()

clear()

finalize()
