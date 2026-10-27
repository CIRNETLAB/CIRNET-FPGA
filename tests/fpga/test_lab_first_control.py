"""Installed logical protocol and mandatory actual parser/behavior acceptance."""
from importlib.resources import files
import json
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT=Path(__file__).resolve().parents[2]
TOP=ROOT/'fpga/experiment-controller/rtl/top.v'
INSTRUMENT=ROOT/'fpga/instrument/rtl/top.v'


def test_control_boundary_names_and_transport_neutral_contract():
    text=TOP.read_text()
    for port in ['command_valid','command_code','safe_condition','scan_done','scan_success',
                 'plan_valid','routing_ready','protection_ready','watchdog_armed','watchdog_expired',
                 'fault_in','drive_enable','routing_enable','topology_scan_enable','experiment_clock']:
        assert port in text, f'missing control boundary: {port}'
    schema=json.loads((files('contracts')/'fpga-protocol/control.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    validator=Draft202012Validator(schema)
    request={'protocol_version':'1.0-scaffold','sequence':1,'operation':'SAFE_STATE'}
    validator.validate(request)
    with pytest.raises(ValidationError): validator.validate({**request,'operation':'AUTO_CORRECT_STUDENT_WIRING'})
    with pytest.raises(ValidationError): validator.validate({**request,'protocol_version':'0.1-dev'})


def test_b12_design_target_is_preserved_and_rejected_as_logical_runtime_protocol():
    resource=files('contracts')
    schema=json.loads((resource/'fpga-protocol/control.schema.json').read_text())
    manifest=json.loads((resource/'manifest.json').read_text())
    record=next(x for x in manifest['contracts'] if x['id']=='FpgaControlScaffold')
    assert record['version']=='1.0-scaffold'
    target=json.loads((resource/'physical-lab/examples/v1-target-capabilities.json').read_text())
    assert target['fpga_protocol_version']=='2.0-scaffold' and target['available'] is False
    assert target['firmware_version']=='UNAVAILABLE'
    assert all(x['channels']==0 and x['runtime_reconfiguration_supported'] is False
               for x in target['instrument_capabilities'].values())
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate({'protocol_version':target['fpga_protocol_version'],
                                             'sequence':1,'operation':'START'})


def test_future_instrument_interfaces_are_explicitly_unavailable():
    assert INSTRUMENT.is_file(),'future instrument interface missing'
    text=INSTRUMENT.read_text()
    for port in ['acquisition_clk','generator_clk','sdram_clk','logic_analyzer_available',
                 'scope_2ch_available','generator_2ch_available','capture_valid','sdram_request']:
        assert port in text
    docs=(ROOT/'fpga/instrument/README.md').read_text()
    for marker in ['EP4CE10','SDRAM Arbiter','Trigger','Timestamp','CDC','TBD_BY_HARDWARE_DESIGN']:
        assert marker in docs


def test_actual_rtl_compilation_and_original_and_supplemental_behavior():
    result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/check_rtl.py')],
                          capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert value['pyslang']=='12.0.0' and value['contracts']['version']=='0.1.1'
    assert [x['marker'] for x in value['results']]==['LAB_FIRST_RTL_PASS','PERMIT_MATRIX_RTL_PASS']
