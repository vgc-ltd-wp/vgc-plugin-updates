# -*- coding: utf-8 -*-
"""Audit the dev-mode component IDs.

Lists every `data-devid` in the app, grouped by page, and flags any that the
components map (vgc-stock-manager-components.md) doesn't mention yet. Run this
after tagging a screen so the doc and the code can't silently drift.

    python vgc-stock-manager-components.py
"""
import re
import io
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, 'vgc-stock-manager', 'app', 'app.js')
MD = os.path.join(ROOT, 'vgc-stock-manager-components.md')

_src = io.open(APP, encoding='utf-8').read()
# Literal attributes, plus the dynamic devids passed as string args to helpers
# that emit data-devid themselves — group() on the item form ('itemform-*') and
# lowCard() on the dashboard ('home-low-*').
ids = set(re.findall(r'data-devid="([^"]+)"', _src))
ids |= set(re.findall(r"'((?:itemform|home-low)-[a-z]+)'", _src))
# Drop the group() helper's own dynamic construction (data-devid="' + devid + '").
ids = sorted(i for i in ids if re.match(r'^[a-z0-9]+(-[a-z0-9]+)+$', i))
groups = {}
for i in ids:
    page = i.split('-', 1)[0]
    groups.setdefault(page, []).append(i)

print('%d component IDs across %d page(s)\n' % (len(ids), len(groups)))
for page in sorted(groups):
    print(page + ':')
    for i in groups[page]:
        print('   ' + i)

md = io.open(MD, encoding='utf-8').read() if os.path.exists(MD) else ''
missing = [i for i in ids if ('`' + i + '`') not in md]
if missing:
    print('\nUNDOCUMENTED (in code, missing from components.md):')
    for i in missing:
        print('   ' + i)
else:
    print('\nAll IDs are documented in components.md.')
