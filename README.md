# net-Circuit-FPGA

Independent Lab-First FPGA source/scaffold **0.1.0**. The portable controller,
disabled future instrument interface retain their Remote source bytes. The
original testbench retains every assertion and holds reset through one clock
edge before release, correcting simulator-dependent declaration initialization.
Hardware drivers belong to net-Circuit-Hardware; system safety,
orchestration and integrated acceptance belong to net-Circuit-Remote.

There is no board image, Python runtime package, transport decoder, switching
matrix, electrical protection, topology scanner, ADC/DAC, SDRAM or CDC
implementation. Pinout, Quartus synthesis/timing and electrical measurements
remain **TBD_BY_HARDWARE_DESIGN**. Software/RTL results cannot close OPEN-ABI,
OPEN-FRESHNESS or OPEN-HARDWARE.

Version domains are independent: Contracts **1.0.1**, logical control
**1.0-scaffold**, reserved register map **1.0-reserved**, physical firmware and
protocol **UNAVAILABLE**. B12 is explicitly resolved: Contracts' preserved
unavailable design-target example says `2.0-scaffold`; that illustrative label
is rejected by the executable logical schema. It is never rewritten or treated
as supported firmware.

Verification uses installed immutable Contracts and the independent DEV
allocator, Node 22, exact `pyslang==12.0.0`, and the official digest-pinned OSS CAD
Suite 2026-10-26. Icarus/vvp report the upstream bundled development identity
`14.0 (devel) (s20260301-713-gf9111a949-dirty)`. Missing/wrong tools fail acceptance.
The complete hash-locked Python closure supports Windows/Python 3.14 and
Linux/Python 3.12; hosted Linux execution is separate evidence.

Bootstrap a private environment with `python -B scripts/bootstrap_contract_tools.py
--manifest ABSOLUTE_CONTRACTS_MANIFEST` (or exact DEV URL/SHA environment
selectors). This allocates the first external session before writing diagnostics.
Keep the emitted session/context and direct `TEMP`, `TMP`, `TMPDIR`, pip cache,
pytest basetemp and all logs into that session. Download
`requirements-verification.lock` with `--require-hashes --only-binary=:all:`
into its external wheelhouse, then install with `--no-index --find-links
ABSOLUTE_WHEELHOUSE --require-hashes --only-binary=:all:`. Install the selected
Contracts wheel with `python -B scripts/install_contracts.py --manifest
ABSOLUTE_CONTRACTS_MANIFEST`; run `python -B -m pip check`.

Run `python -B scripts/install_toolchain.py --archive ABSOLUTE_PINNED_ARCHIVE`,
or omit `--archive` to download the pinned official release. It extracts a fresh
owned tool root and writes archive/binary/version provenance there; CI receives
`NETCIRCUIT_FPGA_TOOLCHAIN_ROOT`. Set that variable locally to the printed root.
Run `python -B scripts/check_rtl.py --toolchain-root ABSOLUTE_OWNED_ROOT` and
`python -B -m pytest --basetemp ABSOLUTE_OWNED_SESSION/pytest`. There are no
optional parser/compiler/simulation skips or PATH fallback. Both original and
supplemental testbenches must emit their PASS markers. Immediate drive inhibit
and synchronous FAULT/routing cleanup are distinct abstract simulation checks.

Build with `python -B scripts/build_source.py --output
ABSOLUTE_OWNED_SESSION/netcircuit-fpga-scaffold-0.1.0.tar.gz --provenance
ABSOLUTE_SOURCE_PROVENANCE_JSON`. The source archive has deterministic metadata,
an exact file/SHA256 inventory and `fpga-artifact.json` at its root. Source
fingerprint is SHA256 of sorted `sha256  path` LF lines; identity excludes itself
from that inventory. No source sibling imports or canonical schema copies are
required. Fresh exports must carry explicit provenance. The initial
[provenance](integration/source-provenance.json) honestly records the uncommitted
migration against both preserved baseline revisions.

Inspect external diagnostics before cleanup using the installed allocator's
guarded session cleanup. Preserve LICENSE, original RTL/testbench, frozen source,
historical evidence and Git ancestry. No board programming or physical rollback
is claimed. Canonical system authority remains Lab-First v3.1 in
[net-Circuit-Remote architecture](https://github.com/net-Circuit-Remote/net-Circuit-Remote/blob/master/docs/ARCHITECTURE.md).
