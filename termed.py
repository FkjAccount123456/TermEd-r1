from utils import clear, reset_term
from renderers.renderers import init_mp

if __name__ == '__main__':
    try:
        init_mp()

        import editor as core
        from os import get_terminal_size
        import os
        import sys
        from renderers.renderers import finalize
        from editor import TextBuffer, Split, HSplit, check_tree


        if sys.platform == "win32":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

        treepath = None
        files = []
        for arg in sys.argv[1:]:
            if os.path.exists(arg):
                if os.path.isdir(arg):
                    treepath = arg
                elif os.path.isfile(arg):
                    files.append(arg)

        termh = get_terminal_size().lines - 1

        editor = core.Editor(termh + 1, get_terminal_size().columns)

        if files:
            editor.cur.open_file(files[0])  # type: ignore
            cur = editor.cur
            nfiles = min(len(files), termh // 10)
            h = termh // nfiles
            for file in files[1:nfiles]:
                cur.split(HSplit, TextBuffer, h)  # type: ignore
                cur = cur.parent[0].win2  # type: ignore
                cur.open_file(file)  # type: ignore
        if treepath:
            editor.open_explorer(treepath)

        editor.mainloop()

        clear()
        finalize()

    except Exception as e:
        reset_term()
        raise e

    reset_term()
