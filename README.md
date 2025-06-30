TermEd, short for Terminal Editor, is an editor with unicode support, window spliting, and code highlighting (only available for python currently).  
(It is only a project for fun, whose quality is not ensured.)
# Usage
- Clone the repo
``` bash
git clone https://github.com/FkjAccount123456/TermEd.git
```
- Compile C Highlighting Library (only an example, replace ”gcc“ with the C Compiler you use)
``` bash
cd TermEd/
gcc -fPIC -shared ./renderers/libpyhl.c -o ./renderers/libpyhl.so
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
# Todo List
- Floating window
- Auto indent
- Builtin configuration language
- GUI
- Tree-sitter integration
- CTags integration
- LSP integration (may done by plugins)
# Screenshots
You can see them in ```./pics/```

![](/pics/微信截图_20250501094850.png "Editing python file")
![](/pics/微信截图_20250429211040.png "Splited to many windows")
