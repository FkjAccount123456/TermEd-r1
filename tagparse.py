import os

type TagEntry = dict[str, str]
type FileEntry = tuple[str, tuple[int, int]]


def parse_tags_file(tags_path: str) -> dict[str, list[TagEntry]]:
    tag_base = os.path.dirname(tags_path)
    if not tag_base:
        tag_base = os.curdir
    tags = {}
    with open(tags_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('!'):
                continue
            parts = line.strip().split('\t')
            if len(parts) < 3:
                continue
            entry = {
                'name': parts[0],
                'path': os.path.join(tag_base, parts[1]),
                'pattern': parts[2]
            }
            for field in parts[3:]:
                if ':' in field:
                    k, v = field.split(':', 1)
                    if k not in entry:
                        entry[k] = v
                else:
                    entry['kind'] = field
            if entry['name'] not in tags:
                tags[entry['name']] = [entry]
            else:
                tags[entry['name']].append(entry)
    return tags


def tags_navigate(entry: TagEntry, lines: list[str] | None = None) -> FileEntry | None:
    file = entry['path']
    if not os.path.exists(file) or not os.path.isfile(file):
        return
    pattern = entry['pattern']
    if not pattern.startswith('/^'):
        try:
            lnnum = int(pattern[:pattern.rfind(';')])
            return file, (lnnum - 1, 0)
        except ValueError:
            return
    pattern = pattern[pattern.find('^') + 1 : pattern.rfind('$')].strip()
    if not lines:
        with open(file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    for i, line in enumerate(lines):
        if (j := line.find(pattern)) != -1:
            if (j := line.find(entry['name'], j)) != -1:
                return file, (i, j)
            return file, (i, j)


# 又一个副作用merge
def merge_tags(tags: dict[str, list[TagEntry]], other: dict[str, list[TagEntry]]):
    for name, entries in other.items():
        if name in tags:
            tags[name].extend(entries)
        else:
            tags[name] = entries
