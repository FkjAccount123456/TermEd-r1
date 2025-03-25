import editor
from os import get_terminal_size
from utils import clear
import sys


editor = editor.Editor(get_terminal_size().lines, get_terminal_size().columns)
if len(sys.argv) > 1:
    editor.cur.open_file(sys.argv[1])
editor.mainloop()

clear()
