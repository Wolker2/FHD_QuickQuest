"""Lossless SRHD BlockPar/CacheData DAT <-> editable JSON (Python standard library).
Derived from the earlier QuickQuest GitHub recovery scripts, which credit
Sergei Osminin's MIT-licensed rangers-utils for format details.
"""
import struct,zlib
KEYS={'blockpar':bytes.fromhex('89 c6 e8 b1'),'cachedata':bytes.fromhex('37 3f 8f ea')}
OUTER_KEYS=(0x7db6c99d,0xc83fcbf3)
def outer_header(data):
 a,b=OUTER_KEYS
 checked=struct.pack('<I',zlib.crc32(data)^a)+data
 return struct.pack('<II',len(data)^a^b,zlib.crc32(checked)^b)
def cipher(data,seed):
 seed&=0xffffffff
 if seed>=0x80000000:seed-=0x100000000
 out=bytearray(data)
 for i in range(len(out)):
  hi,lo=divmod(seed,0x1f31d)
  seed=lo*0x41a7-hi*0xb14
  if seed<1:seed+=0x7fffffff
  out[i]^=(seed-1)&255
 return bytes(out)
class Reader:
 def __init__(self,data):self.data=data;self.p=0
 def take(self,n):
  if n<0 or self.p+n>len(self.data):raise ValueError('Unexpected EOF')
  r=self.data[self.p:self.p+n];self.p+=n;return r
 def u8(self):return self.take(1)[0]
 def u32(self):return struct.unpack('<I',self.take(4))[0]
 def wide(self):
  start=self.p
  while self.p+1<len(self.data):
   if self.take(2)==b'\0\0':return self.data[start:self.p-2].decode('utf-16le')
  raise ValueError('Unterminated UTF16')
 def block(self,fmt,depth=0):
  if depth>128:raise ValueError('nesting')
  sorted_flag=bool(self.u8()) if fmt=='blockpar' else None
  count=self.u32()
  if count>200000:raise ValueError('count')
  entries=[]
  for _ in range(count):
   meta=[self.u32(),self.u32()] if sorted_flag else None
   kind=self.u8();name=self.wide()
   if kind==1:entry={'kind':'parameter','name':name,'value':self.wide()}
   elif kind==2:entry={'kind':'block','name':name,'value':self.block(fmt,depth+1)}
   else:raise ValueError('bad kind')
   if meta is not None:entry['sort_meta']=meta
   entries.append(entry)
  out={'entries':entries}
  if fmt=='blockpar':out['sorted']=sorted_flag
  return out
def decode(data,fmt):
 wrapped=fmt=='cachedata' and len(data)>=24 and data[:8]==outer_header(data[8:])
 if wrapped:data=data[8:]
 if len(data)<16:raise ValueError('Short DAT')
 key=KEYS[fmt]
 digest=struct.unpack_from('<I',data)[0]
 seed=int.from_bytes(bytes(a^b for a,b in zip(data[4:8],key)),'little',signed=True)
 zipped=cipher(data[8:],seed)
 if zlib.crc32(zipped)!=digest:raise ValueError('bad DAT CRC')
 if zipped[:4]!=b'ZL01':raise ValueError('unsupported DAT')
 original_len=struct.unpack_from('<I',zipped,4)[0]
 uncompressed=zlib.decompress(zipped[8:])
 if len(uncompressed)!=original_len:raise ValueError('bad uncompressed length')
 r=Reader(uncompressed);root=r.block(fmt)
 if r.p!=len(uncompressed):raise ValueError('trailing bytes')
 result={'format':fmt,'seed':seed,'root':root}
 if wrapped:result['outer_checksum']='resource-dat-v1'
 return result
def wide(out,text):
 if '\0' in text:raise ValueError('NUL in string')
 out.extend(text.encode('utf-16le'));out.extend(b'\0\0')
def block(out,b,fmt):
 sorted_flag=bool(b.get('sorted')) if fmt=='blockpar' else False
 if fmt=='blockpar':out.append(int(sorted_flag))
 entries=b['entries'];out.extend(struct.pack('<I',len(entries)))
 for i,entry in enumerate(entries):
  if sorted_flag:
   if 'sort_meta' in entry:a,c=entry['sort_meta']
   else:
    a=0
    while i-a>0 and entries[i-a-1]['name']==entry['name']:a+=1
    c=sum(e['name']==entry['name'] for e in entries) if a==0 else 0
   out.extend(struct.pack('<II',a,c))
  kind=entry['kind'];out.append({'parameter':1,'block':2}[kind]);wide(out,entry['name'])
  if kind=='parameter':wide(out,entry['value'])
  else:block(out,entry['value'],fmt)
def encode(project):
 fmt=project['format'];seed=project['seed'];key=KEYS[fmt]
 plain=bytearray();block(plain,project['root'],fmt)
 zipped=b'ZL01'+struct.pack('<I',len(plain))+zlib.compress(plain,9)
 digest=struct.pack('<I',zlib.crc32(zipped))
 seedbits=(int(seed)&0xffffffff).to_bytes(4,'little')
 salt=bytes(a^b for a,b in zip(seedbits,key))
 out=digest+salt+cipher(zipped,seed)
 if project.get('outer_checksum'):
  if fmt!='cachedata' or project['outer_checksum']!='resource-dat-v1':raise ValueError('unsupported outer format')
  return outer_header(out)+out
 return out
