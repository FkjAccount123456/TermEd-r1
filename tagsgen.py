import subprocess
import os
from ederrors import *


def get_output_file(path: str):
    root = os.path.join(os.path.dirname(__file__), "data")
    name = path.replace('-', '--').replace('/', '-').replace('\\', '-') + ".ctags"
    if not os.path.exists(root):
        os.mkdir(root)
    if not os.path.isdir(root):
        raise EditorError(
            "failed to start tags generator: cannot establish data directory")
    return os.path.join(root, name)


class TagsGenerator:
    def __init__(self, root: str):
        self.output = get_output_file(root)
        # 适用于TermEd文件夹的参数
        self.cmd = ["ctags", "--fields=+niazS", "--extras=+q", "--c++-kinds=+pxI", "--c-kinds=+px",
                    "--exclude=external", "--exclude=deprecated", "--exclude=pics", "--exclude=tests",
                    "--exclude=developing", "--exclude=*.md",
                    "-R", "-f " + self.output]
        self.root = root.replace('\\', '/')
        subprocess.run(self.cmd, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

    def update(self, ud_file: str):
        froot = os.path.dirname(ud_file).replace('\\', '/')
        if froot.startswith(self.root):
            subprocess.run(self.cmd)
            return True
        return False

    def force_update(self):
        subprocess.run(self.cmd, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
