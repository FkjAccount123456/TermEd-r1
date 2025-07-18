import os
import sys


if __name__ == '__main__':
    need_build_dirs = ['csrc', 'renderers']
    cc = 'gcc'
    if sys.argv[1:]:
        cc = sys.argv[1]
    print(f'Using {cc} to build')

    cwd = os.path.dirname(__file__)
    for d in need_build_dirs:
        if not os.path.exists(d):
            continue
        curdir = os.path.join(cwd, d)
        for name in os.listdir(curdir):
            if not os.path.isfile(os.path.join(curdir, name)):
                continue
            if name.endswith('.c'):
                cmd = f'{cc} -fPIC -shared {os.path.join(curdir, name)} -o {os.path.join(curdir, name)[:-2]}.so'
                print(cmd)
                os.system(cmd)
