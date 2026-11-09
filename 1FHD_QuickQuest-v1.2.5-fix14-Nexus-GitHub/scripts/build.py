#!/usr/bin/env python3
"""Self-contained rebuild of FHD_QuickQuest v1.2.5-fix14 from editable JSON QMM/DAT sources."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import argparse,hashlib,json,sys,io
from dat_codec import encode as dat_encode
from qmm_codec import encode as qmm_encode
ROOT=Path(__file__).resolve().parents[1]
PREFIX='Mods/FHD_MODS/FHD_QuickQuest/'
def read_json(path):return json.loads(path.read_text(encoding='utf-8'))
def sha256(data):return hashlib.sha256(data).hexdigest()
def read_source_archive(path):
 if path.is_file():return path.read_bytes()
 parts=path.parent/"parts"
 files=sorted(parts.glob("*.part"))
 if not files:raise FileNotFoundError(path)
 return b"".join(p.read_bytes() for p in files)
def build(root=ROOT):
 root=Path(root);source=root/'source';files={}
 for path in sorted((source/'config').rglob('*.json')):
  name='CFG/'+path.relative_to(source/'config').with_suffix('.dat').as_posix()
  files[name]=dat_encode(read_json(path))
 with ZipFile(io.BytesIO(read_source_archive(source/'quests'/'Rus.zip'))) as z:
  seen=set()
  for entry in sorted(z.namelist()):
   if not entry.endswith('.json'):raise ValueError('Unexpected quest-source file '+entry)
   catalog=json.loads(z.read(entry).decode('utf-8'))
   if catalog.get('format')!='srhd-qmm7-catalog-v1':raise ValueError('Invalid catalog '+entry)
   for name,document in catalog['quests'].items():
    if name in seen or name.endswith('/') or '/' in name or '\\' in name or not name.endswith('.qmm'):
     raise ValueError('Invalid / duplicate quest '+name)
    seen.add(name)
    files['DATA/Quest/Rus/'+name]=qmm_encode(document)
 with ZipFile(io.BytesIO(read_source_archive(source/'artwork'/'assets.zip'))) as z:
  for name in z.namelist():
   if name.endswith('/') or name.startswith('/') or '..' in Path(name).parts or name in files:
    raise ValueError('Invalid / repeated asset '+name)
   files[name]=z.read(name)
 files['ModuleInfo.txt']=(source/'ModuleInfo.txt').read_bytes().decode('utf-8').encode('cp1251')
 return files
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--verify-original',action='store_true',help='Require 122 runtime files to have original SHA-256')
 p.add_argument('--output',type=Path,default=ROOT/'dist/FHD_QuickQuest_v1.2.5-fix14_INSTALL.zip')
 a=p.parse_args();files=build()
 if a.verify_original:
  expected=read_json(ROOT/'original-file-sha256.json')
  actual={name:sha256(b) for name,b in files.items()}
  errors=sorted(name for name in expected.keys()|actual.keys() if expected.get(name)!=actual.get(name))
  if errors:raise SystemExit('Original-source mismatch: '+', '.join(errors[:30]))
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with ZipFile(a.output,'w',ZIP_DEFLATED,compresslevel=9) as z:
  for name,data in sorted(files.items()):
   info=__import__('zipfile').ZipInfo(PREFIX+name,(2026,1,1,0,0,0))
   info.external_attr=0o644<<16
   z.writestr(info,data,compress_type=ZIP_DEFLATED,compresslevel=9)
 print(json.dumps({'runtime_files':len(files),'source_bytes_verified':a.verify_original,'install_zip':str(a.output)},ensure_ascii=False))
if __name__=='__main__':main()
