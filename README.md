# Quality Platform

Integrated manufacturing quality platform — **FMEA**, **SPC**, and **Control Plan** tools over a
shared core, aligned with the AIAG / IATF-16949 core quality toolset.

This is a monorepo. Two previously standalone apps now live here with their **full commit history
preserved** (the histories are part of the engineering story):

| App | Path | What it does |
| --- | ---- | ------------ |
| FMEA Risk Analyzer | [`apps/fmea/`](apps/fmea/) | Failure Mode & Effects Analysis — RPN / AIAG-VDA Action Priority, exports |
| Manufacturing SPC Dashboard | [`apps/spc/`](apps/spc/) | Statistical Process Control — control charts + process capability |

> Migrated from the standalone repos
> [`fmea-risk-analyzer`](https://github.com/Siddardth7/fmea-risk-analyzer) and
> [`manufacturing-spc-dashboard`](https://github.com/Siddardth7/manufacturing-spc-dashboard),
> which are now **archived → moved here**.

## Run an app

Each app still runs unchanged from its own directory:

```bash
cd apps/fmea && streamlit run app.py
cd apps/spc  && streamlit run app.py
```

## Repository layout

```
apps/
  fmea/   # FMEA Risk Analyzer (full original history)
  spc/    # Manufacturing SPC Dashboard (full original history)
```

A shared `quality_core` package and a unified Streamlit shell are introduced in subsequent
Week-01 issues (see the project board).
