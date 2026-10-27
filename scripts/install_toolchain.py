"""Install only the digest-pinned official OSS CAD Suite into an owned session."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tarfile
import uuid

from artifact_download import download_artifact
from artifact_paths import artifact_directory, validate_artifact_directory

ROOT=Path(__file__).resolve().parents[1]


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def selected_platform():
    if platform.machine().lower() not in {'amd64','x86_64'}:
        raise ValueError('Pinned RTL toolchain supports x64 Windows/Linux only.')
    if os.name=='nt': return 'windows-x64'
    if platform.system()=='Linux': return 'linux-x64'
    raise ValueError('Pinned RTL toolchain supports Windows/Linux only.')


def tool_env(root,runtime):
    root=Path(root);runtime=Path(runtime)
    selected={key:value for key,value in os.environ.items() if not key.upper().startswith(('LD_','DYLD_'))
              and key.upper() not in {'LIBPATH','SHLIB_PATH','IVERILOG_ROOT','VPI_MODULE_PATH',
                                     'IVERILOG_DUMPER','IVERILOG_ICONFIG','GCONV_PATH','BASH_ENV','ENV'}}
    return {**selected,'PATH':os.pathsep.join([str(root/'bin'),str(root/'lib'),os.environ.get('PATH','')]),
            'YOSYSHQ_ROOT':str(root),'TMP':str(runtime),'TEMP':str(runtime),'TMPDIR':str(runtime),
            'PYTHONDONTWRITEBYTECODE':'1'}


def checked_members(archive):
    members=archive.getmembers();seen=set()
    for item in members:
        path=PurePosixPath(item.name)
        if ('\\' in item.name or path.is_absolute() or '..' in path.parts or
            not path.parts or path.parts[0]!='oss-cad-suite' or ':' in item.name or item.name in seen):
            raise ValueError('Unsafe or duplicate toolchain archive member.')
        seen.add(item.name)
        if not (item.isfile() or item.isdir() or item.issym() or item.islnk()):
            raise ValueError('Unsupported toolchain archive member.')
    return members


def install(archive=None):
    key=selected_platform()
    lock=json.loads((ROOT/'integration/toolchain-lock.json').read_text())
    selected=lock['platforms'][key]
    # Reject a bad local archive before creating extraction/runtime directories.
    if archive is not None:
        archive=Path(archive)
        if not archive.is_absolute() or sha256(archive)!=selected['sha256']:
            raise ValueError('Toolchain archive SHA256 does not match the pinned release.')
        validate_artifact_directory(archive.parent)
    owned=artifact_directory('fpga-leaf-toolchain-'+uuid.uuid4().hex[:8])
    if archive is None:
        archive=owned/selected['filename']
        archive.write_bytes(download_artifact(selected['url'],selected['sha256']))
    if archive.stat().st_size!=selected['size']:
        raise ValueError('Toolchain archive size differs from the pinned release.')
    with tarfile.open(archive,'r:gz') as bundle:
        members=checked_members(bundle)
        bundle.extractall(owned,members=members,filter='data')
    root=owned/'oss-cad-suite';env=tool_env(root,owned)
    tools={}
    extension='.exe' if key=='windows-x64' else ''
    for name in ('iverilog','vvp'):
        executable=root/'bin'/(name+extension)
        result=subprocess.run([str(executable),'-V'],env=env,cwd=owned,capture_output=True,text=True,timeout=60)
        output=result.stdout+result.stderr
        if result.returncode or selected['version'] not in output:
            raise ValueError('Toolchain executable version differs from the pinned release: '+name)
        tools[name]={'path':'bin/'+executable.name,'sha256':sha256(executable),'versionOutput':output}
    provenance={'schemaVersion':1,'platform':key,'release':lock['tag'],'archivePath':str(archive),
                'archiveSha256':selected['sha256'],'tools':tools}
    (root/'.netcircuit-toolchain.json').write_text(json.dumps(provenance,indent=2)+'\n')
    if os.environ.get('GITHUB_ENV'):
        with Path(os.environ['GITHUB_ENV']).open('a',encoding='utf-8') as output:
            output.write('NETCIRCUIT_FPGA_TOOLCHAIN_ROOT='+str(root)+'\n')
    print(json.dumps({'root':str(root),'provenance':provenance},indent=2))
    return root


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path)
    args=parser.parse_args()
    install(args.archive)
