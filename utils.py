import os


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

widthlist = []


def get_width(o):
    # 参考了https://wenku.baidu.com/view/da48663551d380eb6294dd88d0d233d4b14e3f18.html?
    """Return the screen column width for unicode ordinal o."""
    global widths
    o = o[-1]
    o = ord(o)
    if o in widthlist:
        return widthlist[o]
    if o == 0xe or o == 0xf:
        widthlist[o] = 0
        return 0
    if o == 0x9:
        widthlist[o] = 0
        return 8
    for num, wid in widths:
        if o <= num:
            widthlist[o] = wid
            return wid
    widthlist[o] = 1
    return 1
