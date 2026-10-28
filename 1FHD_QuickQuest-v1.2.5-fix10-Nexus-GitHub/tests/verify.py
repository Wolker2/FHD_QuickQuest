#!/usr/bin/env python3
"""Verify source-only build, all quest graphs, DAT wrappers and local resources."""
from pathlib import Path
from collections import Counter
import copy,json,platform,re,shutil,sys,tempfile,zlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from build import build,hashes,load,PREFIX,quest_sources
from dat_codec import decode as dat_decode,encode as dat_encode,outer_header
from qmm_codec import decode as qmm_decode,encode as qmm_encode

def walk(block,prefix=''):
    for e in block['entries']:
        name=prefix+e['name'];yield name,e
        if e['kind']=='block':yield from walk(e['value'],name+'.')
def media_fields(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ['img','sound','track'] and item:yield key,item
            yield from media_fields(item)
    elif isinstance(value,list):
        for item in value:yield from media_fields(item)

def verify():
    checks=[]
    def check(condition,label):
        assert condition,label;checks.append(label)
    with tempfile.TemporaryDirectory() as folder:
        clean=Path(folder)
        for name in ['source','scripts']:shutil.copytree(ROOT/name,clean/name,ignore=shutil.ignore_patterns('__pycache__'))
        files=build(clean)
    expected=load(ROOT/'original-file-sha256.json')
    check(hashes(files)==expected,'Isolated source-only build reproduces all 120 original runtime SHA-256 hashes')
    check(len(files)==120,'Exactly 120 runtime files')
    check(sum(n.endswith('.qmm') for n in files)==114,'All 114 QMM quests rebuilt')
    check(sum(n.endswith('.dat') for n in files)==3,'Three DAT configs rebuilt')
    check(sum(n.endswith('.jpg') for n in files)==2,'Both quest JPG images retained')
    check(not any(n.lower().endswith(('.dll','.scr','.bmp')) for n in files),'No DLL/SCR in upload; documentation BMPs excluded')
    catalogs=list((ROOT/'source/quests/Rus').glob('*.json'))
    check(len(catalogs)==12 and len(list(quest_sources(ROOT/'source')))==114,'Twelve JSON catalogs contain all 114 named quests')
    project_files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in ['.git','dist','__pycache__'] for x in p.relative_to(ROOT).parts)]
    check(len(project_files)<=100,'Source package contains at most 100 files')
    configs={};nodes={};parameters=[]
    for name,data in files.items():
        if not name.endswith('.dat'):continue
        fmt='cachedata' if name.endswith('CacheData.dat') else 'blockpar'
        d=dat_decode(data,fmt);configs[name]=d
        check(dat_encode(d)==data,'DAT roundtrip: '+name)
        for key,e in walk(d['root']):
            nodes[key]=e
            if e['kind']=='parameter':parameters.append((key,e['value']))
    cache=files['CFG/CacheData.dat']
    check(configs['CFG/CacheData.dat']['outer_checksum']=='resource-dat-v1','CacheData outer-checksum format retained')
    check(cache[:8]==outer_header(cache[8:]),'CacheData outer length and both CRC calculations match')
    damaged=bytearray(cache);damaged[-1]^=1
    try:dat_decode(bytes(damaged),'cachedata')
    except ValueError:rejected=True
    else:rejected=False
    check(rejected,'Corrupted CacheData rejected')
    local_paths=[];literal_refs=set()
    for key,text in parameters:
        if text.startswith('Mods\\FHD_MODS\\FHD_QuickQuest\\'):
            target=text.replace('\\','/').removeprefix(PREFIX)
            check(target in files,'Configured local file exists: '+target);local_paths.append(target)
        literal_refs.update(re.findall(r"(?:CT|GenerateCodeStringFromBlock)\('([^']*)'\)",text))
    check(all(ref in nodes for ref in literal_refs),'All complete literal CT/code-block references resolve')
    quest_targets={p for p in local_paths if p.endswith('.qmm')}
    check(quest_targets=={n for n in files if n.endswith('.qmm')},'All 114 supplied quests have config mappings, without unused QMM extras')
    media=Counter();inventory=[];total_locations=total_jumps=total_parameters=0
    for name,data in sorted(files.items()):
        if not name.endswith('.qmm'):continue
        d=qmm_decode(data)
        check(qmm_encode(d)==data,'QMM roundtrip through EOF: '+name)
        ids=[loc['id'] for loc in d['locations']];idset=set(ids)
        check(len(ids)==len(idset),'Unique location IDs: '+name)
        check(all(j['from_location_id'] in idset and j['to_location_id'] in idset for j in d['jumps']),'All jump endpoints exist: '+name)
        valid=True
        for obj in d['locations']+d['jumps']:
            for field in ['parameter_changes','parameter_conditions']:
                ids=[x['parameter_id'] for x in obj.get(field,[])]
                valid=valid and len(ids)==len(set(ids)) and all(1<=i<=len(d['parameters']) for i in ids)
        check(valid,'Sparse parameter IDs valid and unique: '+name)
        media.update(media_fields(d));total_locations+=len(d['locations']);total_jumps+=len(d['jumps']);total_parameters+=len(d['parameters'])
        inventory.append({'quest':Path(name).name,'locations':len(d['locations']),'jumps':len(d['jumps']),'parameters':len(d['parameters'])})
    custom_media={name for kind,name in media if kind=='img' and name.startswith('FHDJohnDoe_')}
    check(custom_media=={'FHDJohnDoe_01','FHDJohnDoe_02'},'Both custom John Doe image keys are used by quests')
    for name in sorted(custom_media):
        binding=nodes.get('Bm.PQI.'+name)
        check(binding is not None and binding['value'].replace('\\','/').removeprefix(PREFIX) in files,'Custom quest media resolves through Bm.PQI: '+name)
    sample_name='DATA/Quest/Rus/Abandoned.qmm';sample=qmm_decode(files[sample_name]);edited=copy.deepcopy(sample)
    edited['task_text']=(edited['task_text'] or '')+'\n[Source edit verification]'
    check(qmm_encode(edited)!=files[sample_name] and qmm_decode(qmm_encode(edited))==edited,'QMM text edits compile without altering other source fields')
    broken=copy.deepcopy(sample);broken['locations'][0]['id']+=1_000_000
    bad_ids={x['id'] for x in broken['locations']}
    check(any(j['from_location_id'] not in bad_ids or j['to_location_id'] not in bad_ids for j in broken['jumps']),'Graph audit detects a broken source location reference')
    lang=copy.deepcopy(configs['CFG/Rus/Lang.dat']);process=dict(walk(lang['root']))['Script.FHDQuickQuest10.Process.01']
    process['value']+=' // source edit verification'
    check(dat_decode(dat_encode(lang),'blockpar')==lang,'Embedded game script edits survive DAT serialization')
    metadata=files['ModuleInfo.txt'].decode('cp1251')
    check('Name=FHD_QuickQuest\r\n' in metadata and 'Priority=100\r\n' in metadata,'CP1251 metadata, CRLF and original priority retained')
    check('Languages=Eng' in metadata and not any(n.startswith(('CFG/Eng/','DATA/Quest/Eng/')) for n in files),'Original English declaration and Russian-only payload preserved')
    check('ver.1.2.3.' in metadata,'Original stale metadata version preserved')
    process='\n'.join(e['value'] for key,e in nodes.items() if key.startswith('Script.FHDQuickQuest10.Process.') and e['kind']=='parameter')
    check('markerIndex>10' in process and 'selectedPercent=10+markerIndex' in process,'Runtime selection is clamped to 10..20 percent')
    observations=[
        {'id':'version-label','fact':'Upload filename is v1.2.5-fix10 and ModuleInfo says ver.1.2.3; QMM files retain their embedded changelog/version labels. Original labels are preserved, not reconciled by guessing.'},
        {'id':'fee-description','fact':'ModuleInfo says 10..25 percent. Runtime markerIndex clamps to 0..10 and selectedPercent=10+markerIndex, i.e. 10..20 percent.'},
        {'id':'language-files','fact':'ModuleInfo advertises Eng but only Russian config/quest payloads are supplied.'}]
    return {'status':'passed','checks_passed':len(checks),'checks':checks,'runtime_sha256':hashes(files),
        'totals':{'quests':len(inventory),'locations':total_locations,'jumps':total_jumps,'parameters':total_parameters},
        'configured_local_files':len(local_paths),'literal_code_text_refs':sorted(literal_refs),
        'source_package_files':len(project_files),'quest_catalog_files':len(catalogs),
        'quest_inventory':inventory,'media':{'unique_fields':len(media),'custom_images':sorted(custom_media),'other_media_require_game_resources':True},
        'observations':observations,'live_game_or_tge_gui_executed':False,
        'test_scope':'Source-only rebuild, original-byte hashes, DAT/QMM serialization and edit tests, quest graph/sparse parameter integrity, local configuration/media references. Game event timing, fees, money-marker behavior and quest playthroughs were not executed.',
        'environment':{'python':platform.python_version(),'zlib':zlib.ZLIB_RUNTIME_VERSION}}

if __name__=='__main__':
    report=verify()
    if len(sys.argv)>1:
        target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','checks_passed','totals','configured_local_files']},indent=2))
