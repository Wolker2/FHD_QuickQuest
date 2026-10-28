"""Lossless QMM7 <-> sparse editable JSON, using Python's standard library.

Layout reference: SRHD XenoModKit quest support and the game quest structures.
Only explicitly stored parameter changes/conditions are serialized to JSON.
No original binary, opaque payload or dense default-parameter matrix is needed.
"""
import math,struct

SCHEMA='srhd-qmm7-sparse-v1'
MEDIA='img:str sound:str track:str'
SPECS={
 'header':'header:u32 major_version:i32 minor_version:i32 change_log:str giving_race:u8 when_done:u8 planet_race:u8 player_career:u8 player_race:u8 reputation_change:i32 screen_width:i32 screen_height:i32 grid_width:i32 grid_height:i32 default_jump_count_limit:i32 hardness:i32',
 'range':'from_value:i32 to_value:i32 text:str',
 'parameter':'minimum:i32 maximum:i32 param_type:u8 reserved:bytes3 show_when_zero:u8 crit_type:u8 active:u8',
 'change':'parameter_id:i32 change:i32 showing_type:u8 change_type:u8 changing_formula:str crit_text:str '+MEDIA,
 'text':'text:str '+MEDIA,
 'location':'day_passed:i32 x:i32 y:i32 id:i32 max_visits:i32 location_type:u8 parameter_changes:change[] texts:text[] text_by_formula:u8 text_select_formula:str',
 'condition':'parameter_id:i32 must_from:i32 must_to:i32 equal:values mod:values',
 'jump':'priority:f64 day_passed:i32 id:i32 from_location_id:i32 to_location_id:i32 always_show:u8 jumping_count_limit:i32 showing_order:i32 parameter_conditions:condition[] parameter_changes:change[] formula_to_pass:str text:str description:str '+MEDIA,
 'strings':'to_star:str to_planet:str date:str money:str from_planet:str from_star:str ranger:str',
}
# Parameter range count precedes is_money/name, while range records follow them.

def fields(spec):return [tuple(x.split(':')) for x in SPECS[spec].split()]

class Reader:
 def __init__(self,data):self.data=memoryview(data);self.offset=0
 def take(self,n):
  if n<0 or self.offset+n>len(self.data):raise ValueError('Truncated QMM at '+str(self.offset))
  b=self.data[self.offset:self.offset+n];self.offset+=n;return b
 def number(self,fmt):return struct.unpack('<'+fmt,self.take(struct.calcsize('<'+fmt)))[0]
 def count(self):
  n=self.number('i')
  if not 0<=n<=1_000_000:raise ValueError('Invalid QMM count: '+str(n))
  return n
 def value(self,kind):
  if kind in ['i32','u32','u8','f64']:
   result=self.number({'i32':'i','u32':'I','u8':'B','f64':'d'}[kind])
   if kind=='f64' and not math.isfinite(result):raise ValueError('Non-finite priority')
   return result
  if kind=='str':
   flag=self.number('i')
   if flag==0:return None
   if flag!=1:raise ValueError('Unsupported string presence flag')
   return bytes(self.take(self.count()*2)).decode('utf-16le')
  if kind=='bytes3':return list(self.take(3))
  if kind=='values':
   n=self.count();flag=self.number('B');return {'flag':flag,'values':[self.number('i') for _ in range(n)]}
  if kind.endswith('[]'):return [self.record(kind[:-2]) for _ in range(self.count())]
  raise ValueError(kind)
 def record(self,spec):return {name:self.value(kind) for name,kind in fields(spec)}
 def parameter(self):
  p=self.record('parameter');n=self.count();p['is_money']=self.value('u8');p['name']=self.value('str')
  p['showing_info']=[self.record('range') for _ in range(n)]
  for key in ['crit_value_text','img','sound','track','starting_formula']:p[key]=self.value('str')
  return p

class Writer:
 def __init__(self):self.data=bytearray()
 def number(self,fmt,value):self.data.extend(struct.pack('<'+fmt,value))
 def value(self,kind,value):
  if kind in ['i32','u32','u8','f64']:
   if kind=='f64' and not math.isfinite(value):raise ValueError('Non-finite priority')
   self.number({'i32':'i','u32':'I','u8':'B','f64':'d'}[kind],value);return
  if kind=='str':
   self.number('i',0 if value is None else 1)
   if value is not None:
    b=value.encode('utf-16le');self.number('i',len(b)//2);self.data.extend(b)
   return
  if kind=='bytes3':
   if len(value)!=3:raise ValueError('Three reserved bytes required')
   self.data.extend(bytes(value));return
  if kind=='values':
   self.number('i',len(value['values']));self.number('B',value['flag'])
   for item in value['values']:self.number('i',item)
   return
  if kind.endswith('[]'):
   self.number('i',len(value))
   for item in value:self.record(kind[:-2],item)
   return
  raise ValueError(kind)
 def record(self,spec,value):
  for name,kind in fields(spec):self.value(kind,value[name])
 def parameter(self,p):
  self.record('parameter',p);self.number('i',len(p['showing_info']));self.value('u8',p['is_money']);self.value('str',p['name'])
  for item in p['showing_info']:self.record('range',item)
  for key in ['crit_value_text','img','sound','track','starting_formula']:self.value('str',p[key])

def decode(data):
 r=Reader(data);d=r.record('header');d={'format':SCHEMA,**d}
 if d['header'] not in (0x423a35d7,0x069f6bd7):raise ValueError('Only QMM7 is supported')
 d['parameters']=[r.parameter() for _ in range(r.count())];d['strings']=r.record('strings')
 locations,jumps=r.count(),r.count();d['success_text']=r.value('str');d['task_text']=r.value('str')
 d['locations']=[r.record('location') for _ in range(locations)];d['jumps']=[r.record('jump') for _ in range(jumps)]
 if r.offset!=len(data):raise ValueError('QMM has trailing bytes')
 return d

def encode(d):
 if d['format']!=SCHEMA or d['header'] not in (0x423a35d7,0x069f6bd7):raise ValueError('Expected sparse QMM7 JSON')
 w=Writer();w.record('header',d);w.number('i',len(d['parameters']))
 for p in d['parameters']:w.parameter(p)
 w.record('strings',d['strings']);w.number('i',len(d['locations']));w.number('i',len(d['jumps']))
 w.value('str',d['success_text']);w.value('str',d['task_text'])
 for item in d['locations']:w.record('location',item)
 for item in d['jumps']:w.record('jump',item)
 return bytes(w.data)
