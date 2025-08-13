# Startup Instructions
## Environmental Requirements
- Python >= 3.11.0
- A C Compiler that supports C11
## Preparations
- Clone the repo
``` bash
git clone --recursive https://github.com/FkjAccount123456/TermEd.git
```
- Install Python Dependencies
``` bash
pip3 install -r requirements.txt
```
- Compile C Libraries (only for highlighting currently)
``` bash
cd TermEd/
python3 ./build.py  # use gcc as default
python3 ./build.py clang  # specify C compiler
```
## Running
``` bash
python3 ./termed.py  # open a new buffer
python3 ./termed.py ./file.py  # open a file
```
# Editor Usage
## Keymaps
TermEd is a terminal editor with vim-like model-editing and keymaps, so most of the basic keymaps in Vim can be used in TermEd, such as ```w``` for going to the beginning of next word.
Repeat time can be specified behind operations. Specifying counts for text objects is not supported currently.
There are also something different from Vim:
- When entering ```<C-]>```, TermEd will find the symbol under cursor and jump to it according to tags file, or pop up a float window for selecting a definition if there are multiple definitions.
- ```;st``` can be used to select a theme, a window will pop up and the changes can be immediately shown in the editor.
- ```;ff``` to find a file with fuzzy finder.
- ```;ft``` to find a tag with fuzzy finder.
## Commands
Use ```:``` to enter command mode just like Vim.
File operations are similar to Vim, but abbreviations like ```:wq``` is not supported.
- ```:tree``` to open file explorer.
- ```:theme [theme_name]``` to select a theme.
- ```:selectheme``` to select a theme using the theme picker.
- ```:addtags [tags_file]``` to add a tags file, if ```./tags``` can be found in cwd, it will be automatically added.
- ```:cleartags``` to clear all tags files.
- ```:tag [symbol_name]``` to find a symbol in tags files, same as ```<C-]>```.
- ```:f [pattern]``` to find a pattern in current buffer, like ```/``` in Vim, regex is unsupported.
- ```:s [pattern]/[replacement]``` to substitute a pattern in current buffer, like ```s``` in Vim, regex is unsupported.
- ```:cd [path]``` to change file explorer root path.
- ```:tagbar``` to open tagbar.
