"""Install the exact selected Contracts wheel after the locked dependency closure."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from artifact_download import download_artifact
from artifact_paths import artifact_directory
from contracts_artifact import selected_wheel_details, verify_wheel, verify_selected_install


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest')
    args=parser.parse_args(argv)
    if args.manifest or os.environ.get('NETCIRCUIT_CONTRACTS_ARTIFACT_MANIFEST'):
        wheel,digest=selected_wheel_details(args.manifest)
    else:
        url=os.environ.get('NETCIRCUIT_CONTRACTS_WHEEL_URL')
        digest=os.environ.get('NETCIRCUIT_CONTRACTS_WHEEL_SHA256')
        if not url or not digest:
            parser.error('Select an immutable Contracts manifest or exact HTTPS URL/SHA256.')
        wheel=artifact_directory('fpga-leaf-contracts')/'netcircuit_contracts-0.1.1-py3-none-any.whl'
        wheel.write_bytes(download_artifact(url,digest))
        verify_wheel(wheel,digest)
    runtime=artifact_directory('fpga-leaf-contract-install')
    subprocess.run([sys.executable,'-B','-m','pip','install','--no-deps','--force-reinstall',
        '--cache-dir',str(artifact_directory('fpga-leaf-pip-cache')),str(wheel)],check=True,
        env={**os.environ,'TEMP':str(runtime),'TMP':str(runtime),'TMPDIR':str(runtime),
             'PYTHONDONTWRITEBYTECODE':'1'})
    print(verify_selected_install(wheel,digest))


if __name__=='__main__':
    main()
