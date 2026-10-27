"""Build a deterministic source/scaffold release, never a Python/board binary."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

from artifact_paths import validate_artifact_directory

ROOT = Path(__file__).resolve().parents[1]
NAME = 'netcircuit-fpga-scaffold'
SOURCE_NAMES = {'README.md','LICENSE','VERSION','.gitignore','.gitattributes','pytest.ini',
                'requirements-verification.lock','fpga','tests','scripts','integration','docs','.github'}
SUFFIXES = {'.md','.py','.mjs','.json','.v','.lock','.yml','.yaml','.ini'}


def source_files(root):
    result={}
    for entry in sorted(root.iterdir()):
        if entry.name not in SOURCE_NAMES:
            if entry.name in {'.git','.build','__pycache__','.pytest_cache','.venv','fpga-artifact.json'}:
                continue
            raise ValueError('Unexpected source-root entry: '+entry.name)
        if entry.is_symlink() or (hasattr(entry,'is_junction') and entry.is_junction()):
            raise ValueError('Source-root aliases are unsupported: '+entry.name)
        paths=entry.rglob('*') if entry.is_dir() else [entry]
        for path in sorted(paths):
            if '__pycache__' in path.parts or path.suffix=='.pyc':
                continue
            if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):
                raise ValueError('Source aliases are unsupported: '+str(path))
            if not path.is_file():
                continue
            relative=path.relative_to(root).as_posix()
            if path.name not in {'LICENSE','VERSION','.gitignore','.gitattributes','.gitkeep'} and path.suffix not in SUFFIXES:
                raise ValueError('Unexpected source/diagnostic file: '+relative)
            result[relative]=path.read_bytes()
    for required in ['LICENSE','VERSION','README.md','fpga/experiment-controller/rtl/top.v',
                     'fpga/instrument/rtl/top.v','fpga/simulation/tb_lab_first_control.v']:
        if required not in result:
            raise ValueError('Missing required source: '+required)
    return result


def build(output,provenance,root=ROOT):
    output=Path(output)
    if not output.is_absolute():
        raise ValueError('Source archive output must be absolute and allocator-owned.')
    if output.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Source archive output cannot be inside the product source, including a fresh export.')
    validate_artifact_directory(output.parent)
    if output.exists():
        raise ValueError('Source archive output already exists.')
    source=json.loads(Path(provenance).read_text(encoding='utf-8'))
    # Only this exact checkout may supply live Git provenance. A fresh export
    # uses explicit supplied provenance; never discover a parent/sibling repo.
    if (Path(root)/'.git').exists():
        head=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
        status=subprocess.run(['git','-C',str(root),'status','--porcelain=v1'],capture_output=True,text=True,check=True).stdout
        source={**source,'revision':head,'uncommittedMigration':bool(status)}
    for key in ('repository','originalRepository'):
        if not isinstance(source.get(key),str) or not source[key].startswith('https://'):
            raise ValueError('Explicit source repository provenance is required.')
    for key in ('revision','originalRevision'):
        if not re.fullmatch('[0-9a-f]{40}',source.get(key,'')):
            raise ValueError('Explicit source revision provenance is required.')
    if not isinstance(source.get('uncommittedMigration'),bool):
        raise ValueError('Explicit uncommittedMigration provenance is required.')
    payload=source_files(Path(root))
    if payload['VERSION'].decode().strip()!='0.1.0':
        raise ValueError('Unsupported scaffold source version.')
    hashes={name:hashlib.sha256(value).hexdigest() for name,value in sorted(payload.items())}
    fingerprint=hashlib.sha256(''.join(f'{digest}  {name}\n' for name,digest in hashes.items()).encode()).hexdigest()
    identity={'schemaVersion':1,'name':NAME,'version':'0.1.0','kind':'source','contractsVersion':'1.0.1',
              'logicalProtocolVersion':'1.0-scaffold','registerMapVersion':'1.0-reserved',
              'physicalAvailable':False,'source':source,'files':hashes,'sourceFingerprint':fingerprint}
    payload['fpga-artifact.json']=(json.dumps(identity,indent=2,sort_keys=True)+'\n').encode()
    with output.open('xb') as stream:
        with gzip.GzipFile(fileobj=stream,mode='wb',filename='',mtime=0,compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed,mode='w',format=tarfile.PAX_FORMAT) as archive:
                for name,value in sorted(payload.items()):
                    item=tarfile.TarInfo(name); item.size=len(value); item.mode=0o644; item.mtime=0
                    archive.addfile(item,io.BytesIO(value))
    return {'schemaVersion':1,'source':{'path':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest()},
            'sourceFingerprint':fingerprint}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--provenance',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(build(args.output,args.provenance),indent=2))
