"""Name the browser's chunk downloads.
Some browsers (including the Claude desktop browser pane) leave downloads as unnamed *.tmp files.
Chunks are identified by exact byte size and taken in download order.
Usage: python collect_downloads.py <downloads_dir> <out_dir> <prefix>   (out_dir must already hold <prefix>_meta.json)"""
import os, sys, glob, json, shutil
D, O, P = sys.argv[1], sys.argv[2], sys.argv[3]
m = json.load(open(os.path.join(O, f'{P}_meta.json'))); n = len(m['sent']); C = m['chunk']; nch = -(-n // C)
tmps = sorted(glob.glob(os.path.join(D, '*.tmp')) + glob.glob(os.path.join(D, f'{P}_*_chunk_*.bin')), key=os.path.getmtime)
t_meta = os.path.getmtime(os.path.join(O, f'{P}_meta.json'))
for stage, dim in [('emb', 768), ('sent', 3)]:
    want = [min(C, n - c * C) * dim * 4 for c in range(nch)]; c = 0
    for t in tmps:
        if c >= nch: break
        if os.path.getsize(t) == want[c] and os.path.getmtime(t) >= t_meta - 600:
            dst = os.path.join(O, f'{P}_{stage}_chunk_{c}.bin')
            if not os.path.exists(dst): shutil.copy2(t, dst)
            c += 1
    print(stage, 'chunks found', c, 'of', nch)
