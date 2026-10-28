#!/usr/bin/env python3
"""Build QuickQuest fix10 from editable configs/QMM7 JSON and supplied JPGs."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from dat_codec import encode as dat_encode
from qmm_codec import encode as qmm_encode
ROOT=Path(__file__).resolve().parents[1];PREFIX='Mods/FHD_MODS/FHD_QuickQuest/'
def load(path):return json.loads(Path(path).read_text('utf-8'))
def hashes(files):return {n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())}
def quest_sources(source):
    seen=set()
    for path in sorted((Path(source)/'quests/Rus').glob('*.json')):
        catalog=load(path)
        if catalog.get('format')!='srhd-qmm7-catalog-v1':raise ValueError('Expected quest catalog: '+str(path))
        for name,document in catalog['quests'].items():
            if Path(name).name!=name or not name.endswith('.qmm') or name in seen:raise ValueError('Invalid or repeated quest filename: '+name)
            seen.add(name);yield name,document
def build(root=ROOT):
    source=Path(root)/'source';files={}
    for p in sorted((source/'config').rglob('*.json')):files['CFG/'+p.relative_to(source/'config').with_suffix('.dat').as_posix()]=dat_encode(load(p))
    for name,document in quest_sources(source):files['DATA/Quest/Rus/'+name]=qmm_encode(document)
    for p in sorted((source/'artwork').glob('*.jpg')):files['DATA/Quest/Rus/'+p.name]=p.read_bytes()
    files['ModuleInfo.txt']=(source/'ModuleInfo.txt').read_bytes().decode('utf-8').encode('cp1251')
    return files
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify-original',action='store_true')
    p.add_argument('--output',type=Path,default=ROOT/'dist/FHD_QuickQuest-v1.2.5-fix10-install.zip');a=p.parse_args()
    files=build()
    if a.verify_original:
        actual=hashes(files);expected=load(ROOT/'original-file-sha256.json')
        changed=sorted(n for n in actual.keys()|expected.keys() if actual.get(n)!=expected.get(n))
        if changed:raise SystemExit('Original-byte verification failed: '+', '.join(changed))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(PREFIX+name,(2026,1,1,0,0,0));info.external_attr=0o644<<16
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    print(json.dumps({'runtime_files':len(files),'original_bytes_verified':a.verify_original,'output':str(a.output)},indent=2))
if __name__=='__main__':main()
