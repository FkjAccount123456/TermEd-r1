import os
import time
import msvcrt


def getch():
    ch = msvcrt.getwch()
    if ch == "\xe0":
        return '\x00'
    return ch


def clear():
    os.system("cls")


def gotoxy(y, x):
    print(f"\033[{y};{x}f", end="")


def flush():
    print(flush=True, end='')


Pos = tuple[int, int]
widths = [
    (126, 1), (159, 0), (687, 1), (710, 0), (711, 1),
    (727, 0), (733, 1), (879, 0), (1154, 1), (1161, 0),
    (4347, 1), (4447, 2), (7467, 1), (7521, 0), (8369, 1),
    (8426, 0), (9000, 1), (9002, 2), (11021, 1), (12350, 2),
    (12351, 1), (12438, 2), (12442, 0), (19893, 2), (19967, 1),
    (55203, 2), (63743, 1), (64106, 2), (65039, 1), (65059, 0),
    (65131, 2), (65279, 1), (65376, 2), (65500, 1), (65510, 2),
    (120831, 1), (262141, 2), (1114109, 1),
]

widthlist = {}


def get_width(o):
    # 参考了https://wenku.baidu.com/view/da48663551d380eb6294dd88d0d233d4b14e3f18.html?
    """Return the screen column width for unicode ordinal o."""
    global widths
    o = ord(o)
    if o in widthlist:
        return widthlist[o]
    for num, wid in widths:
        if o <= num:
            widthlist[o] = wid
            return wid
    if o == 0xe or o == 0xf:
        widthlist[o] = 0
        return 0
    if o == 0x9:
        widthlist[o] = 8
        return 8
    widthlist[o] = 1
    return 1


def get_file_ext(f: str):
    return f[f.rfind('.') + 1:]


def log(s):
    with open("termed.log", "a", encoding="utf8") as f:
        f.write(str(s) + " " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")


def colorcvt(fg: int | tuple[int, int, int]):
    if isinstance(fg, int):
        return fg // (256 * 256), fg % (256 * 256) // 256, fg % 256
    return fg


cvt_cache = {}


def cvt_truecolor(bg: tuple[int, int, int], fg: tuple[int, int, int]):
    if (g := bg + fg) in cvt_cache:
        return cvt_cache[g]
    if bg == (0, 0, 0):
        cvt_cache[g] = res = f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m"
    else:
        cvt_cache[g] = res = f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m\033[48;2;{bg[0]};{bg[1]};{bg[2]}m"
    return res


def trans_getch(ch: str):
    if ch == '\t':
        return '<tab>'
    if ch == '\n' or ch == '\r':
        return '<cr>'
    if ch == ' ':
        return '<space>'
    if ch == '\x1b':
        return '<esc>'
    if ch == '\x08':
        return '<bs>'
    if ch.isprintable():
        return ch
    if 1 <= ord(ch) <= 26:
        return '<C-' + chr(ord('a') + ord(ch) - 1) + '>'
    if ch == '\x1d':
        return '<C-]>'
    if ch == '\x1c':
        return '<C-\\>'
    if ch == '\x7f':
        return '<C-bs>'
    if ch == '\x00':
        ch = getch()
        return {
            72: '<up>',
            80: '<down>',
            75: '<left>',
            77: '<right>',

            141: '<C-up>',
            145: '<C-down>',
            115: '<C-left>',
            116: '<C-right>',

            152: '<M-up>',
            160: '<M-down>',
            155: '<M-left>',
            157: '<M-right>',

            82: '<ins>',
            83: '<del>',
            71: '<home>',
            79: '<end>',
            73: '<pageup>',
            81: '<pagedown>',

            92: '<C-ins>',
            93: '<C-del>',
            119: '<C-home>',
            117: '<C-end>',
            134: '<C-pageup>',
            118: '<C-pagedown>',

            162: '<M-ins>',
            163: '<M-del>',
            151: '<M-home>',
            159: '<M-end>',
            153: '<M-pageup>',
            161: '<M-pagedown>',

            59: '<F1>',
            60: '<F2>',
            61: '<F3>',
            62: '<F4>',
            63: '<F5>',
            64: '<F6>',
            65: '<F7>',
            66: '<F8>',
            67: '<F9>',
            68: '<F10>',
            133: '<F11>',
            134: '<F12>',

            94: '<C-F1>',
            95: '<C-F2>',
            96: '<C-F3>',
            97: '<C-F4>',
            98: '<C-F5>',
            99: '<C-F6>',
            100: '<C-F7>',
            101: '<C-F8>',
            102: '<C-F9>',
            103: '<C-F10>',
            137: '<C-F11>',
            138: '<C-F12>',

            104: '<M-F1>',
            105: '<M-F2>',
            106: '<M-F3>',
            107: '<M-F4>',
            108: '<M-F5>',
            109: '<M-F6>',
            110: '<M-F7>',
            111: '<M-F8>',
            112: '<M-F9>',
            113: '<M-F10>',
            139: '<M-F11>',
            140: '<M-F12>',
        }.get(ord(ch), '<unknown>')

    return '<unknown>'


def ed_getch():
    return trans_getch(getch())


def get_char_type(ch: str) -> int:
    if ch.isspace():
        return 0
    if ch.isalnum() or ch == '_':
        return 1
    return 2
