TermEd, short for Terminal Editor, is an editor with unicode support, window spliting, and code highlighting (only available for python currently).
(It is only a project for fun, whose quality is not ensured.)
# Usage
- Clone the repo
``` bash
git clone https://github.com/FkjAccount123456/TermEd.git
```
- Compile C Libraries (only for highlighting currently)
``` bash
cd TermEd/
python3 ./build.py  # use gcc as default
python3 ./build.py clang  # specify C compiler
```
- Run the editor
``` bash
python3 ./termed.py  # open a new buffer
```
or
``` bash
python3 ./termed.py ./file.py  # open a file
```
# Features
- Unicode support
- Windows spliting (, resizing and switching)
- Vim-like model editing
- Python highlighting
- Word completion (experimental)
- Linux support
- File explorer (experimental, primary)
- Floating window
- Auto indent (primary)
# Todo List
- Builtin configuration language
- GUI
- Tree-sitter integration
- CTags integration
- LSP integration (may done by plugins)
# Screenshots
You can see them in ```./pics/```

![](/pics/微信截图_20250501094850.png "Editing python file")
![](/pics/微信截图_20250429211040.png "Splited to many windows")
![](/pics/屏幕截图_20250722_114845.png "Using file explorer")
![](/pics/屏幕截图_20250723_173909.png "Running theme selector")
