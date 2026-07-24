# MSA Applicability to SECOM (W09-4, #68)

**Verdict: MSA / Gage R&R does not apply to SECOM.** SECOM has no
part x appraiser x trial structure, and none can be legitimately constructed
from it — a real Gage R&R belongs in the existing `apps/msa` app
(`compute_gage_rr`), never reimplemented here.

## What a Gage R&R requires

A Gage R&R is a *designed* crossed study: **n parts x k appraisers x r trials**,
with r >= 2 repeated measurements of the *same physical part* by the *same
appraiser* (AIAG MSA 4th ed. Section 3.1, recommended design 10x3x3; Section
3.2, Average-and-Range method assumptions). In-repo, these requirements are
already SME-verified against the primary manual and implemented unchanged in
`apps/msa/msa_app/gage_rr_engine.py` — see `apps/msa/docs/ASSUMPTIONS_LOG.md`
RULE 1 (Average-and-Range method, Section 3.2), RULE 11 (balanced crossed
data, Section 3.1), and RULE 12 (minimum study size — >=2 parts, >=2
appraisers, >=2 trials per cell, Section 3.1).

Two variance components come out of that structure:
- **Repeatability (Equipment Variation, EV)** — estimated *within* a
  (part, appraiser) cell, which needs r >= 2 trials of the same part by the
  same appraiser (`gage_rr_engine.py:203`).
- **Reproducibility (Appraiser Variation, AV)** — estimated *across*
  appraisers, which needs k >= 2 appraisers (`gage_rr_engine.py:213`).

## What SECOM actually is

SECOM (`apps/secom/secom_app/ingest.py:52`, `SecomDataset`) is observational
process-monitoring data: **1567 wafers x 590 sensor columns**, one float
reading per (wafer, sensor); the labels file (`secom_labels.data`) carries
only `label in {-1, +1}` and a `timestamp` — no `part`, `appraiser`/operator,
or `trial`/replicate column exists anywhere in the dataset. Each wafer is a
distinct production run measured once by each sensor.

Two tempting fabrications are explicitly rejected:
- **Sensors as appraisers** — invalid. Different sensors measure *different
  physical characteristics*, not repeat appraisals of one measurand. There is
  no "same part, same measurand, different observer" relationship between
  sensor columns.
- **Successive wafers as trials** — invalid. Each wafer is a *different part*
  (a distinct production run), not a re-measurement of the same part. Trials
  in a Gage R&R must be repeated readings of one physical part, not readings
  of different parts over time.

With one reading per wafer and no appraiser axis, **neither variance
component is estimable** — the very partition MSA exists to make (equipment
vs. appraiser vs. part variation) is undefined for this dataset. Either
fabrication above is exactly the kind of invention this issue forbids.

## What would be needed to run one

A genuine Gage R&R on this gauge would require a *designed* study collected
separately from SECOM's production stream: pull >=5-10 reference wafers, have
>=2-3 appraisers each re-measure every reference wafer on the sensor under
study >=2-3 times. SECOM, as vendored, contains none of this data.

## Where a real study goes

If such a designed study is ever collected, it belongs in the existing MSA
app (`apps/msa`, `compute_gage_rr` in
`apps/msa/msa_app/gage_rr_engine.py`) — the AIAG Average-and-Range engine
already implemented and verified there. SECOM never reimplements Gage R&R
math; `secom_app/msa.py` only detects and refuses the case where a frame
lacks the required structure (see `gage_rr_applicability` /
`assert_gage_rr_applicable`), pointing back to this document and to the real
engine.

> **Note — primary source not vendored.** The AIAG MSA 4th ed. manual PDF is
> not in this repo. The claims above are anchored to
> `apps/msa/docs/ASSUMPTIONS_LOG.md` (RULE 1/11/12), which records a prior
> SME verification against the primary manual (2026-07-19, Sid). No new AIAG
> section numbers, tables, or thresholds are introduced by this document —
> it asserts structure, not numbers.
