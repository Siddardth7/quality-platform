# Control Plan

Scaffold for the Control Plan app. It mounts into the unified Quality Platform
shell alongside FMEA, SPC, and MSA, sharing `quality_core`.

Today it provides validated ingest of a Control Plan CSV (`characteristic, lsl,
usl, target, measurement_method, sample_size, frequency, recommended_chart,
reaction_plan`) through `quality_core.io`. FMEA → Control Plan mapping/derivation
and the authoring/editing UI land in later issues.
