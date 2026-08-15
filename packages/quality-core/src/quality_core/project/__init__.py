"""The M3 project-file contract: what a Quality Platform project looks like on disk.

`schema` holds the pydantic models for `project.yaml` and the artifact files
(FMEA, Control Plan, SPC config, SPC result, Gage R&R, MSA->SPC gate, SPC->FMEA
feedback), each under one shared `ArtifactEnvelope` (`schema_version` / `generated_at` / `generated_by`).
`io` holds the file graph (`ProjectPaths` / `discover_project`) and the generic
load/write pair every M3 arrow issue (#277+) routes through.

Files hold current state only — git is the history (#276): re-runs overwrite in
place, `project_id` is a stable slug, and `spc/results/*.json` is one file per
characteristic. See `docs/PROJECT_FILE_CONTRACT.md` for the graph and
`packages/quality-core/docs/ASSUMPTIONS_LOG.md` for the design record.
"""

from quality_core.project.io import (
    CONTROL_PLAN_JSON,
    FEEDBACK_JSON,
    FMEA_JSON,
    GAGE_RR_JSON,
    MSA_GATE_JSON,
    PROJECT_YAML,
    SPC_CONFIG_JSON,
    SPC_RESULTS_DIR,
    ProjectError,
    ProjectPaths,
    discover_project,
    load_artifact,
    load_optional_artifact,
    load_project_meta,
    spc_result_path,
    spc_result_paths,
    write_artifact,
    write_project_meta,
)
from quality_core.project.schema import (
    SCHEMA_VERSION,
    ArtifactEnvelope,
    CapabilityPayload,
    ChartMetric,
    ControlChartPayload,
    ControlChartViolation,
    ControlPlanArtifact,
    ControlPlanArtifactRow,
    FMEAArtifact,
    GateStatus,
    MSAGageRRArtifact,
    NormalityPayload,
    ProjectCharacteristic,
    ProjectMeta,
    SecondarySeries,
    SPCConfigArtifact,
    SPCConfigRow,
    SPCMSAGateArtifact,
    SPCMSAGateRow,
    SPCResultArtifact,
    SPCToFMEAFeedbackArtifact,
    SPCToFMEAFeedbackRow,
    ToleranceSource,
)

__all__ = [
    # schema
    "SCHEMA_VERSION",
    "ArtifactEnvelope",
    "ToleranceSource",
    "GateStatus",
    "ProjectCharacteristic",
    "ProjectMeta",
    "FMEAArtifact",
    "ControlPlanArtifactRow",
    "ControlPlanArtifact",
    "ControlChartViolation",
    "ChartMetric",
    "SecondarySeries",
    "ControlChartPayload",
    "NormalityPayload",
    "CapabilityPayload",
    "SPCConfigRow",
    "SPCConfigArtifact",
    "SPCMSAGateRow",
    "SPCMSAGateArtifact",
    "SPCResultArtifact",
    "MSAGageRRArtifact",
    "SPCToFMEAFeedbackRow",
    "SPCToFMEAFeedbackArtifact",
    # io
    "PROJECT_YAML",
    "FMEA_JSON",
    "CONTROL_PLAN_JSON",
    "SPC_CONFIG_JSON",
    "MSA_GATE_JSON",
    "SPC_RESULTS_DIR",
    "GAGE_RR_JSON",
    "FEEDBACK_JSON",
    "ProjectError",
    "ProjectPaths",
    "discover_project",
    "spc_result_path",
    "spc_result_paths",
    "load_artifact",
    "load_optional_artifact",
    "load_project_meta",
    "write_artifact",
    "write_project_meta",
]
