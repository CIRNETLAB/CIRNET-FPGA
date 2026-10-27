"""Observable source-release and fail-closed toolchain boundaries."""
import json
import os
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_script(name, *args):
    return subprocess.run([sys.executable, '-B', str(ROOT/'scripts'/name), *map(str,args)],
                          capture_output=True, text=True, timeout=90)


def test_source_archive_rebuild_has_same_bytes_and_rejects_unsafe_input(tmp_path):
    script = ROOT/'scripts/build_source.py'
    assert script.is_file(), 'versioned deterministic source builder is missing'
    provenance = ROOT/'integration/source-provenance.json'
    first,second = tmp_path/'first.tar.gz',tmp_path/'second.tar.gz'
    for path in (first,second):
        result = run_script('build_source.py','--output',path,'--provenance',provenance)
        assert result.returncode == 0, result.stdout+result.stderr
    assert first.read_bytes() == second.read_bytes()
    result = run_script('build_source.py','--output',ROOT/'forbidden.tar.gz','--provenance',provenance)
    assert result.returncode != 0
    assert not (ROOT/'forbidden.tar.gz').exists()


def test_rtl_gate_rejects_missing_explicit_toolchain(tmp_path):
    script = ROOT/'scripts/check_rtl.py'
    assert script.is_file(), 'mandatory RTL acceptance runner is missing'
    result = run_script('check_rtl.py','--toolchain',tmp_path/'missing.json')
    assert result.returncode != 0
    assert 'toolchain' in result.stderr.lower()


def test_toolchain_installer_rejects_unverified_archive_before_extraction(tmp_path):
    script = ROOT/'scripts/install_toolchain.py'
    assert script.is_file(), 'digest-verified RTL toolchain installer is missing'
    invalid=tmp_path/'bad.tgz'; invalid.write_bytes(b'not the selected release')
    result=run_script('install_toolchain.py','--archive',invalid)
    assert result.returncode != 0
    assert 'sha256' in result.stderr.lower()


def test_rtl_gate_rejects_wrong_toolchain_archive_identity(tmp_path):
    script = ROOT/'scripts/check_rtl.py'
    assert script.is_file(), 'mandatory RTL acceptance runner is missing'
    path=tmp_path/'wrong.json'
    path.write_text(json.dumps({'schemaVersion':1,'platform':'windows-x64','archiveSha256':'0'*64}))
    result=run_script('check_rtl.py','--toolchain',path)
    assert result.returncode != 0
    assert 'toolchain' in result.stderr.lower()


def test_contract_provenance_rejects_source_shadowing(tmp_path):
    shadow=tmp_path/'contracts';shadow.mkdir()
    (shadow/'__init__.py').write_text('"""Deliberately unowned source shadow."""\n')
    code="import sys; sys.path.insert(0,sys.argv[1]); import contracts_artifact; contracts_artifact.installed_provenance()"
    result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'scripts')],cwd=tmp_path,
                          env={**os.environ,'PYTHONPATH':str(tmp_path)},capture_output=True,text=True,timeout=60)
    assert result.returncode!=0
    assert 'shadowed' in result.stderr.lower()


@pytest.mark.parametrize('changed,mutation',[
    ('lib/ivl/ivlpp','remove'),('lib/ivl/vvp.conf','tamper'),
    ('lib/required.dll','remove'),('lib/librequired.so.1','tamper'),
    ('libexec/iverilog','remove'),('bin/iverilog','tamper')])
def test_archive_derived_execution_closure_rejects_missing_or_modified_support(tmp_path,changed,mutation):
    """Modeled native layouts; never claims execution of synthetic/Linux tools."""
    archive=tmp_path/'synthetic.tgz';extracted=tmp_path/'oss-cad-suite';extracted.mkdir()
    values={'bin/iverilog':b'wrapper','bin/vvp':b'runtime','libexec/iverilog':b'compiler',
            'lib/ivl/ivlpp':b'preprocessor','lib/ivl/vvp.conf':b'target-config',
            'lib/required.dll':b'native-windows','lib/librequired.so.1':b'native-linux'}
    with tarfile.open(archive,'w:gz') as bundle:
        for name,data in values.items():
            item=tarfile.TarInfo('oss-cad-suite/'+name);item.size=len(data)
            bundle.addfile(item,io.BytesIO(data))
            path=extracted/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    code=('import sys;sys.path.insert(0,sys.argv[1]);'
          'from check_rtl import authenticate_execution_files;'
          'authenticate_execution_files(sys.argv[2],sys.argv[3],sys.argv[4])')
    command=[sys.executable,'-B','-c',code,str(ROOT/'scripts'),str(extracted),str(archive),
             hashlib.sha256(archive.read_bytes()).hexdigest()]
    good=subprocess.run(command,capture_output=True,text=True,timeout=60)
    assert good.returncode==0,good.stderr
    target=extracted/changed
    if mutation=='remove':target.unlink()
    else:target.write_bytes(b'altered support')
    bad=subprocess.run(command,capture_output=True,text=True,timeout=60)
    assert bad.returncode!=0
    assert 'support' in bad.stderr.lower()
