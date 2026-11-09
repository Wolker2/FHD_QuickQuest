#!/usr/bin/env python3
"""QuickQuest v1.2.5-fix14: source-only reproduction and integrity checks."""
from pathlib import Path
import copy,hashlib,json,sys,zipfile,tempfile,shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build import build,read_json
from dat_codec import encode as dat_encode,decode as dat_decode
from qmm_codec import encode as qmm_encode,decode as qmm_decode

def verify():
 with tempfile.TemporaryDirectory() as temp:
  root=Path(temp)
  shutil.copytree(ROOT/'source',root/'source')
  runtime=build(root)
 expected=read_json(ROOT/'original-file-sha256.json')
 current={n:hashlib.sha256(b).hexdigest() for n,b in runtime.items()}
 assert expected==current,'Mismatch of original runtime SHA-256'
 assert len(runtime)==122
 assert sum(n.endswith('.qmm') for n in runtime)==114
 assert sum(n.endswith('.dat') for n in runtime)==3
 assert sum(n.endswith('.jpg') for n in runtime)==2
 assert sum(n.endswith('.bmp') for n in runtime)==2
 assert sum(n.endswith('.txt') for n in runtime)==1
 details={'quests':114,'locations':0,'jumps':0,'parameters':0,'runtime_files':122}
 for name,b in runtime.items():
  if name.endswith('.qmm'):
   obj=qmm_decode(b);assert qmm_encode(obj)==b,name
   details['locations']+=len(obj['locations']);details['jumps']+=len(obj['jumps']);details['parameters']+=len(obj['parameters'])
  if name.endswith('.dat'):
   fmt='cachedata' if name.endswith('CacheData.dat') else 'blockpar'
   assert dat_encode(dat_decode(b,fmt))==b,name
 assert details['locations']==14064 and details['jumps']==37678 and details['parameters']==4501
 sample='DATA/Quest/Rus/Prison.qmm';doc=qmm_decode(runtime[sample]);edited=copy.deepcopy(doc)
 edited['task_text']=(edited['task_text'] or '')+' [test source edit]'
 assert qmm_encode(edited)!=runtime[sample] and qmm_decode(qmm_encode(edited))==edited
 print(json.dumps({'status':'PASS','tests':'122 file SHA-256, 114 QMM roundtrips, 3 DAT roundtrips, source-only isolated build, editable quest text','counts':details},ensure_ascii=False,indent=2))
 return details
if __name__=='__main__':verify()
