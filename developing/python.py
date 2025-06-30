from renderer import Renderer
from langdata.python import *


class PythonRenderer(Renderer):
    # 有人不知道什么是屎山？
    def _render(self, y: int, end: int, col: int):
        target = end, col

        def parse_section(ln: int, pos: int) -> tuple[int, int]:
            def update_ln():
                nonlocal code, states, results
                code = self.text[ln]
                states = self.states[ln]
                results = self.results[ln]

            def find_after(char: str = '(') -> bool:
                p = pos
                while p < len(code) and code[p].isspace():
                    p += 1
                return code[p] in char
            
            def parse_string():
                nonlocal state, pos
                if state & StrLong:
                    qc = "'''"
                elif state & Str2Long:
                    qc = '"""'
                elif state & StrCont:
                    qc = "'"
                elif state & Str2Cont:
                    qc = '"'
                prestate = state
                qclen = len(qc)
                while (ln, pos) <= target and pos < len(code) and code[pos: pos + qclen] != qc:
                    if state == states[pos]:
                        return True
                    if code[pos] == "\\":
                        results[pos] = Str
                        if pos + 1 >= len(code):
                            states[pos] = prestate
                            return True
                        states[pos] = prestate ^ AnyStrCont
                        pos += 1
                    states[pos] = prestate
                    results[pos] = Str
                    pos += 1
                    if pos >= len(code) and ln < len(self.text):
                        pos = 0
                        ln += 1
                        update_ln()
                if pos >= len(code) or (ln, pos) > target:
                    return True
                for _ in range(qclen):
                    results[pos] = Str
                    states[pos] = prestate ^ AnyStrCont
                    pos += 1
                return False

            code = self.text[ln]
            states = self.states[ln]
            results = self.results[ln]
            if pos > 0:
                state = self.states[ln][pos - 1]
            elif ln > 0:
                state = self.states[ln - 1][-1]
                if state & AnyStr:
                    if parse_string():
                        return ln, pos
                if not (state & AnyParen):
                    state = 0
            else:
                state = 0
            while pos < len(code) and (ln, pos) < target and not (state == states[pos]):
                if code[pos].isspace():
                    while pos < len(code) and code[pos].isspace():
                        states[pos] = state
                        results[pos] = Other
                        pos += 1
                elif code[pos].isdigit():
                    while pos < len(code) and (code[pos].isdigit() or code[pos] == "."):
                        states[pos] = state
                        results[pos] = Num
                        pos += 1
                    state &= ~AfterDot
                elif code[pos].isalpha() or code[pos] == "_":
                    cur_token = ""
                    start = pos
                    while pos < len(code) and (code[pos].isalnum() or code[pos] == "_"):
                        cur_token += code[pos]
                        pos += 1
                    if cur_token in pyConstSet:
                        tp = Const
                    elif cur_token in pyKwSet:
                        tp = Keyword
                        if cur_token == "class" and not (state & AnyParen):
                            state |= AfterClass
                        elif cur_token == "def" and not (state & AnyParen):
                            state |= AfterDef
                        elif cur_token == "from" and not (state & AnyParen):
                            state |= AfterImport
                        elif cur_token == "import" and not (state & AnyParen):
                            state ^= AfterImport
                    elif find_after('=') and not (state & ParenLv):
                        tp = Param
                    elif state & AfterImport:
                        tp = Module
                    elif state & AfterClass or state & AfterTh:
                        tp = Class
                    elif state & AfterDef and find_after('=),:'):
                        tp = Param
                    elif state & AfterDef:
                        tp = Func
                    elif state & AfterDot:
                        if find_after():
                            if ord('A') <= ord(cur_token[0]) <= ord('Z') and '_' not in cur_token:
                                tp = Class
                            else:
                                tp = Func
                        else:
                            tp = Field
                    elif cur_token in pyClassSet:
                        tp = Class
                    elif cur_token in pyFuncSet:
                        tp = Func
                    elif find_after():
                        if ord('A') <= ord(cur_token[0]) <= ord('Z') and '_' not in cur_token:
                            tp = Class
                        else:
                            tp = Func
                    elif cur_token in pySelfSet:
                        tp = Param
                    elif cur_token in pySoftKwSet:
                        tp = Keyword
                    else:
                        tp = Id
                    for i in range(start, pos):
                        states[i] = state    
                        results[i] = tp
                    state &= ~AfterDot
                elif code[pos] in "\"'":
                    start = pos
                    qc = code[pos]
                    pos += 1
                    if pos < len(code) and code[pos] == qc:
                        pos += 1
                        if pos < len(code) and code[pos] == qc:
                            pos += 1
                            if qc == '\'':
                                state |= StrLong
                            else:
                                state |= Str2Long
                        else:
                            for i in range(start, pos):
                                states[i] = state
                                results[i] = Str
                            continue
                    else:
                        if qc == '\'':
                            state |= StrCont
                        else:
                            state |= Str2Cont
                    for i in range(start, pos):
                        states[i] = state
                        results[i] = Str
                    parse_string()
                    state &= ~AfterDot
                elif code[pos] in pyOpSet:
                    cur_token = ""
                    while pos < len(code) and code[pos] in pyOpSet:
                        states[pos] = state
                        results[pos] = Op
                        cur_token += code[pos]
                        if code[pos] == '(':
                            state += ParenLv
                        elif code[pos] == ')' and state & ParenLv:
                            state -= ParenLv
                        elif code[pos] == '[':
                            state += BrcktLv
                        elif code[pos] == ']' and state & BrcktLv:
                            state -= BrcktLv
                        elif code[pos] == '{':
                            state += BrcktLv
                        elif code[pos] == '}' and state & BrcktLv:
                            state -= BrcktLv
                        pos += 1
                    if cur_token.endswith("->") and not (state & AnyParen):
                        state |= AfterThArrow
                        state &= ~AfterThColon
                    elif cur_token.endswith(":") and (state & AnyParen) in (0, ParenLv):
                        state |= AfterThColon
                        state &= ~AfterThArrow
                        if not (state & ParenLv):
                            state &= ~AfterClass
                            state &= ~AfterDef
                    elif cur_token.endswith(",") and state & AfterThColon and not (state & AnyParen):
                        state &= ~AfterTh
                    elif cur_token.endswith("=") and state & AfterThColon and (state & AnyParen) in (0, ParenLv):
                        state &= ~AfterTh
                    elif cur_token.endswith(":") and state & AfterThArrow and not (state & AnyParen):
                        state &= ~AfterTh
                    if cur_token.endswith(".") or cur_token.endswith("...."):
                        state |= AfterDot
                    else:
                        state &= ~AfterDot
                elif code[pos] == '#':
                    while pos < len(code) and code[pos] != '\n':
                        states[pos] = state
                        results[pos] = Comment
                        pos += 1
                    state &= ~AfterDot
                else:
                    states[pos] = state
                    results[pos] = Other
                    pos += 1

    def render(self, ln: int, col: int):
        self.change_points.sort()
        self._render(self.change_points[0], ln, col)
