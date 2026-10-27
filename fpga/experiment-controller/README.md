# Lab-First Experiment Controller

EP4CE6E22C8N prototype, **no external SDRAM**; future EP4CE10E22C8N instrument target. Canonical authority: [Remote Lab-First architecture](https://github.com/net-Circuit-Remote/net-Circuit-Remote/blob/master/docs/ARCHITECTURE.md).

Current rtl/top.v is a compile-safe **control scaffold / electrical integration placeholder**. Mini PC uses Hardware Service FpgaTransport, with Serial/USB-SPI adapters unavailable until actual hardware is selected. No physical transport decoder, topology measurement, switching matrix or protection circuit exists here.

The abstract controller follows SAFE → SCANNING → SCANNED → PREPARED → ROUTED → POWERED → ARMED → RUNNING. Successful scan is observational readiness, never topology correctness. Safe condition and plan permits come from verified safety/protection integration; no boolean alone proves electrical safety.

Reset enters SAFE with routing/drive/clock off. Routing is infrastructure-only and defaults open. Drive requires explicit safe plan, route readiness, independent protection and armed watchdog; permits remain live while powered. Fault/watchdog assertion immediately gates outputs off and latches FAULT even for a short pulse; RESET after input clearance invalidates earlier scan/plan sequence. Invalid commands/sequences disable outputs. Clock uses a prepared half-period in abstract control-clock ticks, with no assumed board frequency/voltage/current.

Real implementation requires TBD_BY_HARDWARE_DESIGN: schematic and exact pins, switching/protected-output design, interlock/reset/watchdog behavior, synchronizers/reset release, input pulse requirements, clock source/constraints, supported endpoint resources and measured operating limits. Async latch logic is a simulation boundary; target-device synthesis/timing are unverified.

Simulation testbenches cover reset, invalid sequences, no route/drive before guards, exact clock boundaries, short fault pulse, every live permit loss, watchdog, STOP/SAFE_STATE, failed scan, zero period, invalid command and unavailable future instruments. Standalone acceptance requires exact pinned slang and Icarus/vvp; missing tools fail with no skips. See [current verification commands](../simulation/README.md). Neither compilation nor simulation proves electrical protection.
