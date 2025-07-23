#include <ctype.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#define VEC(T)                                                                 \
  struct {                                                                     \
    size_t len, cap;                                                           \
    T *data;                                                                   \
  }

#define VEC_INIT(VECT)                                                         \
  ({                                                                           \
    VECT vec;                                                                  \
    vec.len = 0;                                                               \
    vec.cap = 8;                                                               \
    vec.data = malloc(sizeof(typeof(*vec.data)) * vec.cap);                    \
    vec;                                                                       \
  })

#define VEC_PUSH(vec, val)                                                     \
  do {                                                                         \
    if (vec.len == vec.cap) {                                                  \
      vec.cap *= 2;                                                            \
      vec.data = realloc(vec.data, sizeof(typeof(*vec.data)) * vec.cap);       \
    }                                                                          \
    vec.data[vec.len++] = val;                                                 \
  } while (0)

#define VEC_POP(vec) vec.data[--vec.len]

#define VEC_GET(vec, i) vec.data[i]

// 还是经典字典树代替字典

typedef struct IdSet {
  struct IdSet **chs;
  bool has;
} IdSet;

IdSet *IdSet_new() {
  IdSet *set = malloc(sizeof(IdSet));
  set->chs = calloc(128, sizeof(IdSet *));
  set->has = false;
  return set;
}

void IdSet_insert(IdSet *set, const char *key) {
  if (!*key) {
    set->has = true;
    return;
  }
  if (!set->chs[*key]) {
    set->chs[*key] = IdSet_new();
  }
  IdSet_insert(set->chs[*key], key + 1);
}

bool contains(IdSet *set, const wchar_t *key, size_t len) {
  for (size_t i = 0; i < len; i++) {
    if (!set || key[i] >= 128)
      return false;
    set = set->chs[key[i]];
  }
  return set && set->has;
}

void IdSet_free(IdSet *set) {
  for (size_t i = 0; i < 128; i++) {
    if (set->chs[i]) {
      IdSet_free(set->chs[i]);
    }
  }
  free(set->chs);
  free(set);
}

bool is_init = false;
IdSet *pyKwSet, *pySoftKwSet, *pySelfSet, *pyConstSet;
IdSet *pyOpSet, *pyFuncSet, *pyClassSet;
IdSet *pyOpKwSet, *pyExceptionKwSet, *pyRepeatKwSet;
IdSet *pyCoroutineKwSet, *pyCondKwSet, *pyReturnKwSet;

// 令人联想到betterlang函数注册壮观场景
// 不过这个是生成的
void init() {
  if (is_init)
    return;
  is_init = true;
  pyKwSet = IdSet_new();
  pySoftKwSet = IdSet_new();
  pySelfSet = IdSet_new();
  pyConstSet = IdSet_new();
  pyOpSet = IdSet_new();
  pyFuncSet = IdSet_new();
  pyClassSet = IdSet_new();
  pyOpKwSet = IdSet_new();
  pyExceptionKwSet = IdSet_new();
  pyRepeatKwSet = IdSet_new();
  pyCoroutineKwSet = IdSet_new();
  pyCondKwSet = IdSet_new();
  pyReturnKwSet = IdSet_new();
  // pyKwSet
  IdSet_insert(pyKwSet, "if");
  IdSet_insert(pyKwSet, "is");
  IdSet_insert(pyKwSet, "None");
  IdSet_insert(pyKwSet, "continue");
  IdSet_insert(pyKwSet, "async");
  IdSet_insert(pyKwSet, "for");
  IdSet_insert(pyKwSet, "try");
  IdSet_insert(pyKwSet, "from");
  IdSet_insert(pyKwSet, "lambda");
  IdSet_insert(pyKwSet, "elif");
  IdSet_insert(pyKwSet, "not");
  IdSet_insert(pyKwSet, "as");
  IdSet_insert(pyKwSet, "or");
  IdSet_insert(pyKwSet, "else");
  IdSet_insert(pyKwSet, "class");
  IdSet_insert(pyKwSet, "with");
  IdSet_insert(pyKwSet, "and");
  IdSet_insert(pyKwSet, "global");
  IdSet_insert(pyKwSet, "raise");
  IdSet_insert(pyKwSet, "def");
  IdSet_insert(pyKwSet, "pass");
  IdSet_insert(pyKwSet, "False");
  IdSet_insert(pyKwSet, "del");
  IdSet_insert(pyKwSet, "await");
  IdSet_insert(pyKwSet, "in");
  IdSet_insert(pyKwSet, "finally");
  IdSet_insert(pyKwSet, "break");
  IdSet_insert(pyKwSet, "yield");
  IdSet_insert(pyKwSet, "assert");
  IdSet_insert(pyKwSet, "nonlocal");
  IdSet_insert(pyKwSet, "return");
  IdSet_insert(pyKwSet, "True");
  IdSet_insert(pyKwSet, "import");
  IdSet_insert(pyKwSet, "except");
  IdSet_insert(pyKwSet, "while");
  // pySoftKwSet
  IdSet_insert(pySoftKwSet, "_");
  IdSet_insert(pySoftKwSet, "case");
  IdSet_insert(pySoftKwSet, "match");
  IdSet_insert(pySoftKwSet, "type");
  // pySelfSet
  IdSet_insert(pySelfSet, "cls");
  IdSet_insert(pySelfSet, "self");
  // pyConstSet
  IdSet_insert(pyConstSet, "True");
  IdSet_insert(pyConstSet, "False");
  IdSet_insert(pyConstSet, "None");
  // pyOpSet
  IdSet_insert(pyOpSet, ")");
  IdSet_insert(pyOpSet, "=");
  IdSet_insert(pyOpSet, "|");
  IdSet_insert(pyOpSet, "^");
  IdSet_insert(pyOpSet, ">");
  IdSet_insert(pyOpSet, "*");
  IdSet_insert(pyOpSet, ";");
  IdSet_insert(pyOpSet, ":");
  IdSet_insert(pyOpSet, "/");
  IdSet_insert(pyOpSet, "+");
  IdSet_insert(pyOpSet, "&");
  IdSet_insert(pyOpSet, "{");
  IdSet_insert(pyOpSet, "%");
  IdSet_insert(pyOpSet, ",");
  IdSet_insert(pyOpSet, "[");
  IdSet_insert(pyOpSet, "(");
  IdSet_insert(pyOpSet, "~");
  IdSet_insert(pyOpSet, "!");
  IdSet_insert(pyOpSet, ".");
  IdSet_insert(pyOpSet, "-");
  IdSet_insert(pyOpSet, "}");
  IdSet_insert(pyOpSet, "]");
  IdSet_insert(pyOpSet, "<");
  // pyFuncSet
  IdSet_insert(pyFuncSet, "pow");
  IdSet_insert(pyFuncSet, "hex");
  IdSet_insert(pyFuncSet, "hash");
  IdSet_insert(pyFuncSet, "round");
  IdSet_insert(pyFuncSet, "sum");
  IdSet_insert(pyFuncSet, "abs");
  IdSet_insert(pyFuncSet, "any");
  IdSet_insert(pyFuncSet, "delattr");
  IdSet_insert(pyFuncSet, "setattr");
  IdSet_insert(pyFuncSet, "eval");
  IdSet_insert(pyFuncSet, "min");
  IdSet_insert(pyFuncSet, "help");
  IdSet_insert(pyFuncSet, "locals");
  IdSet_insert(pyFuncSet, "globals");
  IdSet_insert(pyFuncSet, "len");
  IdSet_insert(pyFuncSet, "vars");
  IdSet_insert(pyFuncSet, "credits");
  IdSet_insert(pyFuncSet, "iter");
  IdSet_insert(pyFuncSet, "open");
  IdSet_insert(pyFuncSet, "repr");
  IdSet_insert(pyFuncSet, "format");
  IdSet_insert(pyFuncSet, "next");
  IdSet_insert(pyFuncSet, "exec");
  IdSet_insert(pyFuncSet, "exit");
  IdSet_insert(pyFuncSet, "ord");
  IdSet_insert(pyFuncSet, "divmod");
  IdSet_insert(pyFuncSet, "id");
  IdSet_insert(pyFuncSet, "ascii");
  IdSet_insert(pyFuncSet, "compile");
  IdSet_insert(pyFuncSet, "print");
  IdSet_insert(pyFuncSet, "issubclass");
  IdSet_insert(pyFuncSet, "max");
  IdSet_insert(pyFuncSet, "hasattr");
  IdSet_insert(pyFuncSet, "license");
  IdSet_insert(pyFuncSet, "copyright");
  IdSet_insert(pyFuncSet, "breakpoint");
  IdSet_insert(pyFuncSet, "getattr");
  IdSet_insert(pyFuncSet, "oct");
  IdSet_insert(pyFuncSet, "bin");
  IdSet_insert(pyFuncSet, "isinstance");
  IdSet_insert(pyFuncSet, "callable");
  IdSet_insert(pyFuncSet, "all");
  IdSet_insert(pyFuncSet, "dir");
  IdSet_insert(pyFuncSet, "quit");
  IdSet_insert(pyFuncSet, "input");
  IdSet_insert(pyFuncSet, "chr");
  // pyClassSet
  IdSet_insert(pyClassSet, "zip");
  IdSet_insert(pyClassSet, "reversed");
  IdSet_insert(pyClassSet, "bytearray");
  IdSet_insert(pyClassSet, "type");
  IdSet_insert(pyClassSet, "Warning");
  IdSet_insert(pyClassSet, "UnicodeTranslateError");
  IdSet_insert(pyClassSet, "AssertionError");
  IdSet_insert(pyClassSet, "NameError");
  IdSet_insert(pyClassSet, "UnicodeError");
  IdSet_insert(pyClassSet, "frozenset");
  IdSet_insert(pyClassSet, "UnicodeWarning");
  IdSet_insert(pyClassSet, "SystemExit");
  IdSet_insert(pyClassSet, "FloatingPointError");
  IdSet_insert(pyClassSet, "PendingDeprecationWarning");
  IdSet_insert(pyClassSet, "float");
  IdSet_insert(pyClassSet, "ImportError");
  IdSet_insert(pyClassSet, "NotImplementedError");
  IdSet_insert(pyClassSet, "LookupError");
  IdSet_insert(pyClassSet, "ChildProcessError");
  IdSet_insert(pyClassSet, "property");
  IdSet_insert(pyClassSet, "IsADirectoryError");
  IdSet_insert(pyClassSet, "AttributeError");
  IdSet_insert(pyClassSet, "super");
  IdSet_insert(pyClassSet, "NotADirectoryError");
  IdSet_insert(pyClassSet, "FutureWarning");
  IdSet_insert(pyClassSet, "complex");
  IdSet_insert(pyClassSet, "filter");
  IdSet_insert(pyClassSet, "UnicodeEncodeError");
  IdSet_insert(pyClassSet, "GeneratorExit");
  IdSet_insert(pyClassSet, "StopIteration");
  IdSet_insert(pyClassSet, "OverflowError");
  IdSet_insert(pyClassSet, "IndentationError");
  IdSet_insert(pyClassSet, "SyntaxError");
  IdSet_insert(pyClassSet, "ReferenceError");
  IdSet_insert(pyClassSet, "UserWarning");
  IdSet_insert(pyClassSet, "tuple");
  IdSet_insert(pyClassSet, "StopAsyncIteration");
  IdSet_insert(pyClassSet, "FileExistsError");
  IdSet_insert(pyClassSet, "InterruptedError");
  IdSet_insert(pyClassSet, "ModuleNotFoundError");
  IdSet_insert(pyClassSet, "list");
  IdSet_insert(pyClassSet, "ConnectionAbortedError");
  IdSet_insert(pyClassSet, "ConnectionError");
  IdSet_insert(pyClassSet, "RuntimeWarning");
  IdSet_insert(pyClassSet, "TabError");
  IdSet_insert(pyClassSet, "ImportWarning");
  IdSet_insert(pyClassSet, "BlockingIOError");
  IdSet_insert(pyClassSet, "staticmethod");
  IdSet_insert(pyClassSet, "KeyboardInterrupt");
  IdSet_insert(pyClassSet, "OSError");
  IdSet_insert(pyClassSet, "IndexError");
  IdSet_insert(pyClassSet, "memoryview");
  IdSet_insert(pyClassSet, "PermissionError");
  IdSet_insert(pyClassSet, "UnboundLocalError");
  IdSet_insert(pyClassSet, "bool");
  IdSet_insert(pyClassSet, "RuntimeError");
  IdSet_insert(pyClassSet, "RecursionError");
  IdSet_insert(pyClassSet, "int");
  IdSet_insert(pyClassSet, "EOFError");
  IdSet_insert(pyClassSet, "MemoryError");
  IdSet_insert(pyClassSet, "ConnectionRefusedError");
  IdSet_insert(pyClassSet, "BytesWarning");
  IdSet_insert(pyClassSet, "SyntaxWarning");
  IdSet_insert(pyClassSet, "TypeError");
  IdSet_insert(pyClassSet, "ConnectionResetError");
  IdSet_insert(pyClassSet, "set");
  IdSet_insert(pyClassSet, "slice");
  IdSet_insert(pyClassSet, "BufferError");
  IdSet_insert(pyClassSet, "str");
  IdSet_insert(pyClassSet, "UnicodeDecodeError");
  IdSet_insert(pyClassSet, "dict");
  IdSet_insert(pyClassSet, "ProcessLookupError");
  IdSet_insert(pyClassSet, "SystemError");
  IdSet_insert(pyClassSet, "BaseException");
  IdSet_insert(pyClassSet, "object");
  IdSet_insert(pyClassSet, "ArithmeticError");
  IdSet_insert(pyClassSet, "Exception");
  IdSet_insert(pyClassSet, "KeyError");
  IdSet_insert(pyClassSet, "DeprecationWarning");
  IdSet_insert(pyClassSet, "enumerate");
  IdSet_insert(pyClassSet, "range");
  IdSet_insert(pyClassSet, "ResourceWarning");
  IdSet_insert(pyClassSet, "bytes");
  IdSet_insert(pyClassSet, "classmethod");
  IdSet_insert(pyClassSet, "map");
  IdSet_insert(pyClassSet, "FileNotFoundError");
  IdSet_insert(pyClassSet, "ValueError");
  IdSet_insert(pyClassSet, "ZeroDivisionError");
  IdSet_insert(pyClassSet, "BrokenPipeError");
  IdSet_insert(pyClassSet, "TimeoutError");

  // pyOpKwSet
  IdSet_insert(pyOpKwSet, "in");
  IdSet_insert(pyOpKwSet, "and");
  IdSet_insert(pyOpKwSet, "not");
  IdSet_insert(pyOpKwSet, "or");
  IdSet_insert(pyOpKwSet, "is");

  // pyExceptionKwSet
  IdSet_insert(pyExceptionKwSet, "except");
  IdSet_insert(pyExceptionKwSet, "finally");
  IdSet_insert(pyExceptionKwSet, "raise");
  IdSet_insert(pyExceptionKwSet, "try");

  //  pyRepeatKwSet
  IdSet_insert(pyRepeatKwSet, "for");
  IdSet_insert(pyRepeatKwSet, "while");
  IdSet_insert(pyRepeatKwSet, "break");
  IdSet_insert(pyRepeatKwSet, "continue");

  // pyCoroutineKwSet
  IdSet_insert(pyCoroutineKwSet, "async");
  IdSet_insert(pyCoroutineKwSet, "await");

  // pyCondKwSet
  IdSet_insert(pyCondKwSet, "if");
  IdSet_insert(pyCondKwSet, "elif");
  IdSet_insert(pyCondKwSet, "else");

  // pyReturnKwSet
  IdSet_insert(pyReturnKwSet, "return");
  IdSet_insert(pyReturnKwSet, "yield");
}

#define find_after(ch) _find_after(s + i, ch, braclv)

bool _find_after(wchar_t *cur, wchar_t ch, size_t *braclv) {
  while (*cur && (isspace(*cur) || *cur == '\\')) {
    if (*cur == '\n' && !(braclv[0] + braclv[1] + braclv[2])) {
      return false;
    }
    if (*cur == '\\') {
      if (*(cur + 1) == '\n')
        cur++;
    }
    cur++;
  }
  return *cur == ch;
}

bool is_camelcase(wchar_t *id, size_t idlen) {
  bool has_lc = false;
  if (!('A' <= id[0] && id[0] <= 'Z'))
    return false;
  for (size_t j = 1; j < idlen; j++) {
    if ('a' <= id[j] && id[j] <= 'z') {
      has_lc = true;
    } else if (id[j] == '_') {
      return false;
    }
  }
  return has_lc;
}

typedef enum PyTok : char {
  Unknown = -1,
  Id = 0,
  Num = 1,
  Const = 2,
  Keyword = 3,
  Str = 4,
  Comment = 5,
  Op = 6,
  Other = 7,
  Class = 8,
  Func = 9,
  Module = 10,
  Field = 11,
  Param = 12,
  Escape = 13,
  Error = 14,
  ThisParam = 15,
  KwFunc = 16,
  KwClass = 17,
  KwPreproc = 18,
  KwCond = 19,
  KwRepeat = 20,
  KwReturn = 21,
  KwCoroutine = 22,
  KwException = 23,
} PyTok;

typedef enum TypeHintTp {
  NoTypeHint,
  AfterArrow,
  AfterColon,
} TypeHintTp;

typedef VEC(PyTok) PyTokList;
typedef VEC(PyTokList) PyHLRes;

PyHLRes render(wchar_t *s, size_t len) {
  // printf("render: %ls (%llu)\n", s, len);
  PyHLRes res = VEC_INIT(PyHLRes);
  VEC_PUSH(res, VEC_INIT(PyTokList));
  size_t braclv[3] = {0, 0, 0};
  size_t i = 0;
  TypeHintTp after_hint = NoTypeHint;
  bool after_dot = false, after_class = false, after_def = false,
       after_import = false;

  while (i < len) {
    if (isspace(s[i])) {
      while (i < len && isspace(s[i])) {
        if (s[i] == '\n' && !(braclv[0] + braclv[1] + braclv[2])) {
          after_hint = NoTypeHint, after_dot = false, after_class = false,
          after_def = false, after_import = false;
          VEC_PUSH(res, VEC_INIT(PyTokList));
        } else if (s[i] == '\n') {
          VEC_PUSH(res, VEC_INIT(PyTokList));
        } else {
          VEC_PUSH(res.data[res.len - 1], Other);
        }
        i++;
      }
    } else if (isdigit(s[i])) {
      while (i < len && (isalnum(s[i]) || s[i] == '.')) {
        VEC_PUSH(res.data[res.len - 1], Num);
        i++;
      }
      after_dot = false;
    } else if (isalpha(s[i]) || s[i] == '_' || s[i] >= 128) {
      wchar_t *id = s + i;
      size_t idlen = 0;
      while (i < len && (isalnum(s[i]) || s[i] == '_' || s[i] >= 128)) {
        i++;
        idlen++;
      }
      PyTok tp;
      if (contains(pyConstSet, id, idlen)) {
        tp = Const;
      } else if (contains(pyOpKwSet, id, idlen)) {
        tp = Op;
      } else if (contains(pyKwSet, id, idlen)) {
        tp = Keyword;
        if (idlen == 5 && !memcmp(id, L"class", 5 * sizeof(wchar_t)) &&
            !(braclv[0] + braclv[1] + braclv[2])) {
          after_class = true;
          tp = KwClass;
        } else if (idlen == 3 && !memcmp(id, L"def", 3 * sizeof(wchar_t)) &&
                   !(braclv[0] + braclv[1] + braclv[2])) {
          after_def = true;
          tp = KwFunc;
        } else if (idlen == 4 && !memcmp(id, L"from", 4 * sizeof(wchar_t)) &&
                   !(braclv[0] + braclv[1] + braclv[2])) {
          after_import = true;
          tp = KwPreproc;
        } else if (idlen == 6 && !memcmp(id, L"import", 6 * sizeof(wchar_t)) &&
                   !(braclv[0] + braclv[1] + braclv[2])) {
          after_import = !after_import;
          tp = KwPreproc;
        } else if (idlen == 6 && !memcmp(id, L"lambda", 6 * sizeof(wchar_t))) {
          tp = KwFunc;
        } else if (contains(pyExceptionKwSet, id, idlen)) {
          tp = KwException;
        } else if (contains(pyRepeatKwSet, id, idlen)) {
          tp = KwRepeat;
        } else if (contains(pyCoroutineKwSet, id, idlen)) {
          tp = KwCoroutine;
        } else if (contains(pyCondKwSet, id, idlen)) {
          tp = KwCond;
        } else if (contains(pyReturnKwSet, id, idlen)) {
          tp = KwReturn;
        }
      } else if (contains(pySelfSet, id, idlen)) {
        tp = ThisParam;
      } else if (find_after('=') && braclv[0]) {
        tp = Param;
      } else if (after_import) {
        tp = Module;
      } else if (after_hint || after_class) {
        tp = Class;
      } else if (after_def && (find_after('=') || find_after(')') ||
                               find_after(',') || find_after(':'))) {
        tp = Param;
      } else if (after_def) {
        tp = Func;
      } else if (after_dot) {
        if (find_after('(')) {
          if (is_camelcase(id, idlen)) {
            tp = Class;
          } else {
            tp = Func;
          }
        } else {
          tp = Field;
        }
      } else if (contains(pyClassSet, id, idlen)) {
        tp = Class;
      } else if (contains(pyFuncSet, id, idlen)) {
        tp = Func;
      } else if (find_after('(')) {
        if (is_camelcase(id, idlen)) {
          tp = Class;
        } else {
          tp = Func;
        }
      } else if (contains(pySoftKwSet, id, idlen)) {
        tp = Keyword;
      } else {
        tp = Id;
      }
      for (size_t j = 0; j < idlen; j++) {
        VEC_PUSH(res.data[res.len - 1], tp);
      }
      after_dot = false;
    } else if (s[i] == '\"' || s[i] == '\'') {
      char qc = s[i], nq = 1, cnt = 0;
      i++;
      VEC_PUSH(res.data[res.len - 1], Str);
      if (i < len && s[i] == qc) {
        i++;
        VEC_PUSH(res.data[res.len - 1], Str);
        if (i < len && s[i] == qc) {
          i++;
          VEC_PUSH(res.data[res.len - 1], Str);
          nq = 3;
        } else {
          continue;
        }
      }
      while (i < len && cnt < nq) {
        if (s[i] == qc) {
          cnt++;
        } else if (s[i] == '\\') {
          i++;
          VEC_PUSH(res.data[res.len - 1], Str);
          cnt = 0;
        } else {
          cnt = 0;
        }
        if (s[i] == '\n') {
          i++;
          VEC_PUSH(res, VEC_INIT(PyTokList));
        } else if (i < len) {
          i++;
          VEC_PUSH(res.data[res.len - 1], Str);
        }
      }
      after_dot = false;
    } else if (contains(pyOpSet, s + i, 1)) {
      if (s[i] == '(') {
        braclv[0]++;
      } else if (s[i] == ')' && braclv[0]) {
        braclv[0]--;
      } else if (s[i] == '[') {
        braclv[1]++;
      } else if (s[i] == ']' && braclv[1]) {
        braclv[1]--;
      } else if (s[i] == '{') {
        braclv[2]++;
      } else if (s[i] == '}' && braclv[2]) {
        braclv[2]--;
      } else if (s[i] == '-' && i + 1 < len && s[i + 1] == '>') {
        VEC_PUSH(res.data[res.len - 1], Op);
        i++;
        if (!(braclv[0] + braclv[1] + braclv[2]))
          after_hint = AfterArrow;
      } else if (s[i] == ':') {
        if (!(braclv[0] + braclv[1] + braclv[2]) ||
            (braclv[0] == 1 && !(braclv[1] + braclv[2])))
          after_hint = AfterColon;
        if (!(braclv[0] + braclv[1] + braclv[2]))
          after_class = after_def = false;
      } else if (s[i] == ',' && braclv[0] == 1 && !(braclv[1] + braclv[2])) {
        after_hint = NoTypeHint;
      } else if (s[i] == '=' &&
                 (!(braclv[0] + braclv[1] + braclv[2]) ||
                  (braclv[0] == 1 && !(braclv[1] + braclv[2])))) {
        after_hint = NoTypeHint;
      } else if (s[i] == ':' && after_hint == AfterArrow &&
                 !(braclv[0] + braclv[1] + braclv[2])) {
        after_hint = NoTypeHint;
      }
      after_dot = s[i] == '.';
      VEC_PUSH(res.data[res.len - 1], Op);
      i++;
    } else if (s[i] == '#') {
      while (i < len && s[i] != '\n') {
        VEC_PUSH(res.data[res.len - 1], Comment);
        i++;
      }
      after_dot = false;
    } else if (s[i] == '\\') {
      if (i + 1 < len && s[i + 1] == '\n') {
        VEC_PUSH(res.data[res.len - 1], Other);
        VEC_PUSH(res, VEC_INIT(PyTokList));
        i += 2;
      } else {
        VEC_PUSH(res.data[res.len - 1], Error);
        i++;
      }
      after_dot = false;
    } else {
      VEC_PUSH(res.data[res.len - 1], Error);
      i++;
    }
  }

  return res;
}

void PyTokList_free(PyTokList lst) { free(lst.data); }

void PyHLRes_free(PyHLRes res) {
  for (size_t i = 0; i < res.len; i++) {
    PyTokList_free(res.data[i]);
  }
  free(res.data);
}

void finalize() {
  IdSet_free(pyClassSet);
  IdSet_free(pyFuncSet);
  IdSet_free(pyConstSet);
  IdSet_free(pyKwSet);
  IdSet_free(pySelfSet);
  IdSet_free(pySoftKwSet);
  IdSet_free(pyOpSet);
}

// wchar_t *code = L"import os\n\nclass A:\n\tdef __init__(self):\n\t\tself.a = 1\n\n\tdef f(self):\n\t\treturn self.a\n\n\tdef g(self):\n\t\treturn os.path.join('a', 'b')\n\n\tdef h(self):\n\t\treturn self.f() + self.g()\n\n\tdef i(self):\n\t\treturn self.h() + self.g()\n\n\tdef j(self):\n\t\treturn self.i() + self.g()\n\n\tdef k(self):\n\t\treturn self.j() + self.g()\n\n\tdef l(self):\n\t\treturn self.k() + self.g";

// int main() {
//   init();
//   PyTokList lst = render(code, wcslen(code));
//   for (size_t i = 0; i < lst.len; i++) {
//     printf("%d ", lst.data[i]);
//   }
//   return 0;
// }
