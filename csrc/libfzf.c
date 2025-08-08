#include <ctype.h>
#include <stdlib.h>
#include <stdbool.h>

// 问的deepseek，还不错
size_t fuzzy_match(wchar_t *pat, wchar_t *text) {
  if (!*pat)
    return 100;
  size_t score = 0, pati = 0, i = 0;
  for (; text[i] && pat[pati]; i++) {
    if (text[i] > 0x7f)
      return 0;
    if (tolower(text[i]) == tolower(pat[pati])) {
      pati++;
      if (i > 0 && tolower(text[i - 1]) == tolower(pat[pati > 1 ? pati - 2 : 0]))
        score += 10;
      if (i == 0)
        score += 5;
      score += 1;
    }
  }
  if (pat[pati])
    return 0;
  for (; text[i]; i++)
    if (text[i] > 0x7f)
      return 0;
  score += (double)pati / (double)i * 20;
  return score;
}

typedef struct {
  size_t pos, score;
} match_t;

int fuzzy_cmp(const void *a, const void *b) {
  return ((match_t *)b)->score - ((match_t *)a)->score;
}

size_t *fuzzy_find(wchar_t *pat, wchar_t **text, size_t n) {
  size_t cap = 8, len = 0;
  match_t *res = malloc(cap * sizeof(match_t));
  for (size_t i = 0; i < n; i++) {
    if (fuzzy_match(pat, text[i])) {
      if (len == cap) {
        cap *= 2;
        res = realloc(res, cap * sizeof(match_t));
      }
      res[len].score = fuzzy_match(pat, text[i]);
      res[len++].pos = i;
    }
  }
  qsort(res, len, sizeof(match_t), fuzzy_cmp);
  size_t *ret = malloc((len + 1) * sizeof(size_t));
  ret[0] = len;
  for (size_t i = 0; i < len; i++) {
    ret[i + 1] = res[i].pos;
  }
  free(res);
  return ret;
}

void free_list(size_t *lst) {
  free(lst);
}
