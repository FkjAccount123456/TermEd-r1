class EditorError(Exception):
    ...


class WinResizeError(EditorError):
    ...


class WinFindError(EditorError):
    ...


class EditorDeprecatedError(EditorError):
    ...
