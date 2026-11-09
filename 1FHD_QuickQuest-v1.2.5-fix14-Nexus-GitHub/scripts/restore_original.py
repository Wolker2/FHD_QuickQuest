#!/usr/bin/env python3
"""Restore original QuickQuest fix14 installation ZIP from integrity-checked GitHub fragments."""
from pathlib import Path
import argparse,hashlib
ROOT=Path(__file__).resolve().parents[1]
SHA256='86855c9bf5f3648d7c1e672bf9cc60ab8711feb83fd761efefe73fd8abd2893e'

def restore(root=ROOT, output=None):
 root=Path(root);files=sorted((root/'install/parts').glob('*.part'))
 if len(files)!=11:raise ValueError('Expected exactly 11 parts of installer, got '+str(len(files)))
 blob=b''.join(p.read_bytes() for p in files)
 digest=hashlib.sha256(blob).hexdigest()
 if digest!=SHA256:raise ValueError('Installer SHA-256 mismatch: '+digest)
 output=Path(output) if output else root/'install/FHD_QuickQuest_v1.2.5-fix14.zip'
 output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(blob)
 return output
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path)
 a=p.parse_args();print('Restored original, SHA-256 OK:',restore(output=a.output))
