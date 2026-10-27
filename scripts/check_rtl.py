"""Mandatory installed Contracts, slang elaboration and actual RTL simulation."""
import argparse
import hashlib
from importlib.metadata import distribution
from importlib.resources import files
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import tarfile
import uuid

from artifact_paths import artifact_directory, validate_artifact_directory
from contracts_artifact import installed_provenance
from install_toolchain import ROOT, checked_members, selected_platform, sha256, tool_env


def authenticate_execution_files(root,archive,expected_archive_sha256):
    """Archive-derived required native helpers, configs, wrappers and libraries.

    Linux modeled-layout tests do not establish actual hosted Linux execution.
    """
    root=Path(root).resolve();archive=Path(archive)
    if sha256(archive)!=expected_archive_sha256:
        raise ValueError('Toolchain archive SHA256 differs from the pinned release.')
    with tarfile.open(archive,'r:gz') as bundle:
        members=checked_members(bundle)
        records={item.name.removeprefix('oss-cad-suite/'):item for item in members if not item.isdir()}
        required={name for name in records if name.startswith(('bin/iverilog','bin/vvp','libexec/','lib/ivl/'))
                  or name.lower().endswith(('.dll','.vpi')) or re.search(r'\.so(?:\.|$)',name.lower())}
        if not required:raise ValueError('Toolchain archive has no execution support inventory.')
        targets={};pending=list(required)
        while pending:
            name=pending.pop();item=records[name]
            if not (item.issym() or item.islnk()):continue
            if item.issym():
                if PurePosixPath(item.linkname).is_absolute():raise ValueError('Unsafe support symlink target.')
                target=posixpath.normpath(posixpath.join(posixpath.dirname(name),item.linkname))
            else:target=item.linkname.removeprefix('oss-cad-suite/')
            if target.startswith('../') or target not in records:
                raise ValueError('Toolchain support link target is absent or unsafe.')
            targets[name]=target
            if target not in required:required.add(target);pending.append(target)
        hashes={}
        # Keep archive order to avoid repeated backward decompression seeks.
        for item in members:
            name=item.name.removeprefix('oss-cad-suite/')
            if name not in required or not item.isfile():continue
            stream=bundle.extractfile(item)
            if stream is None:raise ValueError('Toolchain support archive member has no bytes.')
            expected=hashlib.file_digest(stream,'sha256').hexdigest();hashes[name]=expected
            path=root/name
            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root) or sha256(path)!=expected:
                raise ValueError('Toolchain support file missing or modified: '+name)
        for name,target in targets.items():
            item=records[name];path=root/name
            if item.issym():
                if not path.is_symlink() or os.readlink(path).replace('\\','/')!=item.linkname:
                    raise ValueError('Toolchain support symlink target differs: '+name)
            elif not path.is_file() or path.is_symlink() or not path.samefile(root/target):
                raise ValueError('Toolchain support hardlink differs: '+name)
            visited={name};final=target
            while final in targets:
                if final in visited:raise ValueError('Toolchain support link cycle.')
                visited.add(final);final=targets[final]
            if (not path.is_file() or not path.resolve().is_relative_to(root) or
                final not in hashes or sha256(path)!=hashes[final]):
                raise ValueError('Toolchain support linked bytes differ: '+name)
    return len(required)


def verify_toolchain(root,provenance=None):
    root=Path(root).resolve()
    validate_artifact_directory(root)
    provenance=Path(provenance) if provenance else root/'.netcircuit-toolchain.json'
    value=json.loads(provenance.read_text())
    lock=json.loads((ROOT/'integration/toolchain-lock.json').read_text())
    key=selected_platform();selected=lock['platforms'][key]
    if (value.get('schemaVersion')!=1 or value.get('platform')!=key or value.get('release')!=lock['tag']
        or value.get('archiveSha256')!=selected['sha256']):
        raise ValueError('Toolchain provenance differs from the pinned platform/archive.')
    archive=Path(value['archivePath'])
    validate_artifact_directory(archive.parent)
    if not archive.is_absolute():raise ValueError('Toolchain archive path must be absolute.')
    authenticated=authenticate_execution_files(root,archive,selected['sha256'])
    tools={}
    for name in ('iverilog','vvp'):
        relative='bin/'+name+('.exe' if key=='windows-x64' else '')
        executable=(root/relative).resolve()
        if not executable.is_relative_to(root): raise ValueError('Toolchain executable escaped its owned root.')
        record=value['tools'][name]
        if record['path']!=relative or sha256(executable)!=record['sha256']:
            raise ValueError('Toolchain executable hash differs from selected provenance: '+name)
        tools[name]=executable
    return tools,{**value,'authenticatedExecutionFiles':authenticated},selected


def compile_slang():
    if distribution('pyslang').version!='12.0.0':
        raise ValueError('RTL acceptance requires pyslang==12.0.0; no optional skip.')
    from pyslang.syntax import SyntaxTree
    from pyslang.ast import Compilation
    compilation=Compilation()
    sources=[ROOT/'fpga/experiment-controller/rtl/top.v',ROOT/'fpga/instrument/rtl/top.v',
             ROOT/'fpga/simulation/tb_lab_first_control.v',ROOT/'fpga/simulation/tb_permit_matrix.v']
    for path in sources: compilation.addSyntaxTree(SyntaxTree.fromFile(str(path)))
    errors=[str(d.code) for d in compilation.getAllDiagnostics() if d.isError()]
    if errors: raise RuntimeError('Slang parsing/elaboration failed: '+repr(errors))
    return sources


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolchain-root',type=Path)
    parser.add_argument('--toolchain',type=Path,help='Explicit provenance JSON, primarily for diagnostics.')
    args=parser.parse_args(argv)
    selected=args.toolchain_root or os.environ.get('NETCIRCUIT_FPGA_TOOLCHAIN_ROOT')
    if not selected and args.toolchain: selected=args.toolchain.parent
    if not selected: parser.error('An explicit pinned toolchain root is required; no PATH fallback.')
    tools,provenance,pin=verify_toolchain(selected,args.toolchain)
    contracts=installed_provenance()
    resource=files('contracts')
    schema=json.loads((resource/'fpga-protocol/control.schema.json').read_text())
    manifest=json.loads((resource/'manifest.json').read_text())
    record=next(x for x in manifest['contracts'] if x['id']=='FpgaControlScaffold')
    if record['version']!='1.0-scaffold' or schema['properties']['protocol_version']['const']!='1.0-scaffold':
        raise ValueError('Installed Contracts logical protocol is incompatible.')
    sources=compile_slang()
    runtime=artifact_directory('fpga-leaf-rtl-'+uuid.uuid4().hex[:8]);env=tool_env(selected,runtime)
    report={'contracts':contracts,'pyslang':'12.0.0','toolchain':provenance,'results':[],
            'outputDirectory':str(runtime),'sourceHashes':{p.relative_to(ROOT).as_posix():sha256(p) for p in sources}}
    for name,executable in tools.items():
        result=subprocess.run([str(executable),'-V'],env=env,cwd=runtime,capture_output=True,text=True,timeout=60)
        output=result.stdout+result.stderr
        if result.returncode or pin['version'] not in output:
            raise ValueError('Toolchain execution version differs from the pinned release: '+name)
    command=[str(tools['iverilog']),'-g2012','-tnull',str(sources[0]),str(sources[1])]
    result=subprocess.run(command,env=env,cwd=runtime,capture_output=True,text=True,timeout=60)
    if result.returncode: raise RuntimeError('Both-top syntax failure: '+result.stdout+result.stderr)
    for bench,marker in [('tb_lab_first_control','LAB_FIRST_RTL_PASS'),('tb_permit_matrix','PERMIT_MATRIX_RTL_PASS')]:
        image=runtime/(bench+'.vvp')
        command=[str(tools['iverilog']),'-g2012','-s',bench,'-o',str(image),*[str(p) for p in sources[:2]],
                 str(ROOT/'fpga/simulation'/(bench+'.v'))]
        built=subprocess.run(command,env=env,cwd=runtime,capture_output=True,text=True,timeout=60)
        (runtime/(bench+'-compile.log')).write_text(built.stdout+built.stderr)
        if built.returncode: raise RuntimeError('RTL compilation failed: '+built.stdout+built.stderr)
        run=subprocess.run([str(tools['vvp']),str(image)],env=env,cwd=runtime,capture_output=True,text=True,timeout=60)
        (runtime/(bench+'-behavior.log')).write_text(run.stdout+run.stderr)
        if run.returncode or marker not in run.stdout:
            raise RuntimeError('RTL behavioral simulation failed: '+run.stdout+run.stderr)
        report['results'].append({'testbench':bench,'marker':marker,'status':'PASS'})
    (runtime/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__': main()
