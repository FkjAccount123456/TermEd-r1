from utils import clear, reset_term
from renderers.renderers import init_mp

if __name__ == '__main__':
    try:
        init_mp()

        import editor as core
        from os import get_terminal_size
        import sys
        from renderers.renderers import finalize
        from editor import TextBuffer


        if sys.platform == "win32":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

        editor = core.Editor(get_terminal_size().lines, get_terminal_size().columns)
        if len(sys.argv) > 1:
            if isinstance(editor.cur, TextBuffer):
                editor.cur.open_file(sys.argv[1])
        editor.mainloop()

        clear()
        finalize()

    except Exception as e:
        reset_term()
        raise e

    reset_term()
