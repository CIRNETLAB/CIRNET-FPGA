# M6 product version work

Date: 2026-10-27. This is current work-unit evidence, separate from historical migration reports.

Scaffold VERSION, deterministic source identity, Contracts dependency checks, artifact filenames, CI and current README target exactly 0.1.1. DEV remains 1.0.0a1. Logical protocol 1.0-scaffold, register map 1.0-reserved, physical unavailable status and RTL source bytes are unchanged. Historical source-provenance input remains preserved; a checkout build replaces revision/dirty fields with actual Git evidence. A clean committed build is mandatory for the release.

Changed Python/JSON syntax checks PASS. RTL parser/compiler/behavioral acceptance is NOT_RUN in this work unit until the committed Contracts 0.1.1 artifact is installed into an independent environment.

Follow README bootstrap and pinned toolchain installation; run `python -B scripts/check_rtl.py` and `python -B -m pytest --basetemp ABSOLUTE_SESSION/pytest`. Build `python -B scripts/build_source.py --output ABSOLUTE_SESSION/netcircuit-fpga-scaffold-0.1.1.tar.gz --provenance ABSOLUTE_COMMITTED_PROVENANCE`, repeat to a distinct output and compare bytes. No optional RTL skip or board programming is authorized as release evidence.

All generated regression fixtures/archives used the shared external allocator session with all six Git roots. Shared-session cleanup remains with the migration owner. No stage/commit/merge/push was performed by this work unit.
