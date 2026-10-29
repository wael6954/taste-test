"""Inject app data and the pipeline stages into app_tpl.html. Writes app/index.html (public, no review text) and,
with --private, app/index_private.html (review text in the 3D galaxy hover; git-ignored)."""
import json, os, sys
D = os.path.dirname(os.path.abspath(__file__)); OUTDIR = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(os.path.dirname(D), 'app')
os.makedirs(OUTDIR, exist_ok=True)
t = open(f'{D}/app_tpl.html').read()
stages = open(f'{D}/out/stages.json').read()
for priv in [False] + (['--private' in sys.argv] if '--private' in sys.argv else []):
    data = open(f'{D}/out/app_data{"_private" if priv else ""}.json').read()
    if not priv: assert '"text":[]' in data, 'public app data must not carry review text'
    html = t.replace('__STAGES__', stages).replace('__DATA__', data)
    fn = os.path.join(OUTDIR, 'index_private.html' if priv else 'index.html'); open(fn, 'w').write(html)
    print(fn, len(html) // 1024, 'KB')
