# Competitive Landscape — AI-Integrated Quality Toolkits, Skills & Plugins

**Date:** 2026-07-26
**Method:** GitHub search API (repo keywords + topic filters), profile inspection, README reads, web search for ecosystem context.
**Scope:** Projects and developers doing what we're doing — quality/manufacturing engineering domain knowledge packaged for AI agents, plus adjacent open-source SPC/QMS tooling.

---

## 1. Executive summary

There are **three distinct clusters** in this space, and they barely overlap:

| Cluster | What it is | Maturity | Our overlap |
|---|---|---|---|
| **A. Domain skill packs for AI agents** | Standards knowledge (ISO/AIAG/VDA) packaged as installable Claude/agent skills | New (all built 2026), fast-growing, one clear breakout | **Direct — this is the closest analog to our skills/plugin layer** |
| **B. Classic OSS statistical/quality libraries** | pyspc, `manufacturing`, SixSigma (R), spc-kit | Mature but mostly stale (2019–2023 commits) | **Partial — our SPC/MSA/DOE engine competes here, and this cluster is weak** |
| **C. Open-source eQMS platforms** | QAtrial, OpenQMS, qara-pulse-eqms, qualvora | Small but active, mostly regulated-industry (pharma/MedTech) | **Partial — our platform/UI layer, different vertical** |

**Key finding:** The breakout project is [jherrodthomas/automotive-skills-suite](https://github.com/jherrodthomas/automotive-skills-suite) — **2,419★ from a GitHub account created 11 April 2026** (~3 months). It proves there is real, immediate demand for standards-anchored engineering skills. Nobody has yet done what we're doing: a **working analytical platform** (real SPC/MSA/DOE math on real data) *plus* the agent layer. Cluster A is prompt/knowledge packs with xlsx outputs — no computation engine. Cluster B has the math but is dead and has no AI story.

**Gap we occupy:** validated statistical engine + standards fidelity + agent-native interface. No repo found does all three.

---

## 2. Cluster A — Domain skill packs for AI agents (direct competitors)

### 2.1 The breakout: `jherrodthomas/automotive-skills-suite`

- **URL:** https://github.com/jherrodthomas/automotive-skills-suite
- **Stars:** 2,419 · **Pushed:** 2026-07-26 (daily activity) · **License:** MIT
- **Scale:** README claims **152 skills** (76 builder + 76 matching "confirmation reviewer" pairs); repo description says 100+.
- **Standards:** ISO 26262, ISO/SAE 21434, ISO 21448 SOTIF, IATF 16949, AIAG-VDA (APQP/DFMEA/PFMEA/Control Plan/PPAP), ASPICE, AUTOSAR, ISO 14229/UDS, SysML, MBSE (ARCADIA).
- **Also covers our exact turf:** 8D, 5-Why, fishbone, **MSA Gauge R&R, SPC**.

**Why it works — three mechanics worth stealing:**
1. **Builder + Reviewer pairing.** Every artifact-producing skill has a paired reviewer skill that audits the output and emits a dashboard with KPI tiles, charts, findings tables. Trust mechanism, not just generation.
2. **The chain is the moat** (their words). Skills consume the upstream skill's `.xlsx` as a stable file-format contract: `Item Definition → Safety Plan → DIA → HARA → FSC → TSC → … → Safety Case`. Parallel chains for TARA, SOTIF, and `APQP → DFMEA → PFMEA → Control Plan → PPAP`.
3. **Distribution via installable `.skill` files** + full bundle in GitHub Releases, triggered by frontmatter phrasing.

**Author profile — [Jherrod Thomas](https://github.com/jherrodthomas)**
- Bio: *"I build, break, & rebuild; closing the gap between how things work & how they should."* · Site: `jherrodthomas.com` · 46 followers · 9 public repos · **account created 2026-04-11**
- Portfolio (this is a strategy, not one repo):
  - `automotive-skills-suite` — 2,419★
  - `robotics-skills-suite` — 255★ — 76 audit-ready skills, ISO 10218/13849/62061/12100/9283/15066/3691-4, IEC 62443
  - `asimov-v1` — 104★ — safety fork w/ ISO 12100/10218/13849/13482/9001 package
  - `compliance-checker-algo` — 81★ — standard-agnostic compliance engine, 8-layer NLP pipeline (TF-IDF, graph analysis, ensemble classification, fuzzy matching)
  - `integrated-automotive-standards-handbook` — 36★ — cross-mapping ISO 26262 / 21434 / 21448 / 8800 / 9001
  - `ASIL-SIL-PL-DAL-CROSS-MAPPING-ALGO` — 13★ — interactive safety-classification converter
- **Takeaway:** vertical suites + cross-mapping reference artifacts + a small algorithmic tool. Went 0 → 2.9k★ across the portfolio in ~15 weeks.

### 2.2 The nearest-exact analog: `RBraga01/Quality-Engineering-Skills`

- **URL:** https://github.com/RBraga01/Quality-Engineering-Skills · Site: rbraga01.github.io/Quality-Engineering-Skills
- **Stars:** 13 · **Pushed:** 2026-07-26 · **License:** MIT · **Author:** R. Braga, Braga Portugal, 7 followers, joined Dec 2021
- **Content:** 22 skills + 8 agents. Install: `npx skills add RBraga01/Quality-Engineering-Skills`. Format: agentskills.io (portable to Claude Code, Codex CLI, Cursor, Gemini CLI).
- **Coverage table (theirs):** 8D/5-Why/Fishbone/Is-Is-Not/PDCA/DMAIC · PFMEA/DFMEA/AIAG-VDA Action Priority · PPAP (5 levels, 18 elements)/APQP (5 phases)/Control Plan/DVP&R · MSA Gauge R&R/SPC · NCR/CAR/8D customer report · ISO 9001 internal + IATF 16949 supplemental + VDA 6.3 audits · supplier SCAR.
- **This is our skills roadmap, already published.** Their pitch: *"AI agents… don't know 8D from PDCA, can't apply the AIAG-VDA Action Priority table, and generate generic NCR text that no auditor would accept."*
- **Their agents validate methodology, not format** — e.g. `/8d-coach` rejects "human error" as a root cause without systemic analysis, blocks D4 until containment is verified.
- **Author's broader play:** `a-team` (12★, 26 specialist agents + 19 enforced workflow skills), `builder-growth`, `builder-ai`, `builder-design`, `builder-product`, `awesome-codex-plugins`, `awesome-codex-cli`. Same "enforcement pack" template applied per domain.
- **Why only 13★ vs 2,419★:** narrower scope, no reviewer-pair mechanic, no dashboard output, weaker distribution. Content quality looks comparable. **Distribution and packaging are the differentiator, not domain depth.**

### 2.3 Single-standard specialist skills

| Repo | ★ | Notes |
|---|---|---|
| [robustagile/six-sigma-in-r-skill](https://github.com/robustagile/six-sigma-in-r-skill) | 12 | Helps agents write *correct R* for Six Sigma/SPC incl. control chart constants. Closest to our statistical-correctness angle. |
| [cleverlab-ai/iso-17025-skill](https://github.com/cleverlab-ai/iso-17025-skill) | 8 | ISO/IEC 17025:2017 lab accreditation. **Trilingual (EN/PL/DE)** — separate branches, `npx skills add …@iso-17025-de`. Audit prep, gap analysis, measurement uncertainty, LIMS compliance. Localization as a differentiation lever. |
| [YuchenXia/LLMRiskAnalyzer](https://github.com/YuchenXia/LLMRiskAnalyzer) | 38 | LLM-assisted FMEA. Academic/research flavor. |
| [lukasbahr/kg-rag-fmea](https://github.com/lukasbahr/kg-rag-fmea) | 32 | Knowledge-graph RAG over FMEA. Research. |
| [RajAnandakumar-Microsoft/8d-solution-agent](https://github.com/RajAnandakumar-Microsoft/8d-solution-agent) | 0 | PowerPoint-embedded 8D coaching agent on Azure AI Foundry. PoC. |
| [kolmag/8d-expert-workbench](https://github.com/kolmag/8d-expert-workbench) | 1 | RAG expert Q&A + guided 8D report builder. |
| [realnghon/data-scientist](https://github.com/realnghon/data-scientist) | 2 | Cross-platform AI plugin for statistical method planning + manufacturing data. |

### 2.4 Ecosystem context (where skills get discovered)

- Anthropic launched Agent Skills Oct 2025; spec published as an **open standard at agentskills.io on 2025-12-18**. ~40 skills-compatible products on the official showcase (Codex, Copilot, Cursor, Gemini CLI, VS Code).
- Directories now index at scale: **SkillsMP ~1.9M public skills** scraped from GitHub; claudemarketplaces.com ~23,400; agentskill.sh claims 274,000+; plus LobeHub, MCP Market, llmskills.org, agent-skills.cc, claudeskills.info.
- **Quality is the bottleneck, not supply.** SkillsBench analyzed 47,150 public skills: mean quality **6.2/12**; curated skills raised agent pass rates by **+16.2 pp**. ([Agentman 2026 ecosystem report](https://agentman.ai/blog/agent-skills-ecosystem-report-2026))
- Curated marketplaces are the credibility layer: [trailofbits/skills-curated](https://github.com/trailofbits/skills-curated) (469★, community-vetted), [obra/superpowers-marketplace](https://github.com/obra/superpowers-marketplace) (1,173★).
- Reference-scale general packs: [anthropics/skills](https://github.com/anthropics/skills) 164k★, [obra/superpowers](https://github.com/obra/superpowers) 261k★, [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) 80k★, [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) 29.5k★, [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) 31.8k★ ("170,000+ scientists" — the domain-vertical proof point outside engineering).

---

## 3. Cluster B — Classic OSS statistical/quality libraries (our engine's peers)

**Headline: this cluster is stagnant.** Almost nothing here is both mature and maintained.

| Repo | ★ | Lang | Last push | Status |
|---|---|---|---|---|
| [carlosqsilva/pyspc](https://github.com/carlosqsilva/pyspc) | 238 | Python | 2023-01 | Category leader, **abandoned 3.5 yrs** |
| [slightlynybbled/manufacturing](https://github.com/slightlynybbled/manufacturing) | 69 | Python | 2026-06 | **Active.** Cpk/Ppk, trends. Closest live Python peer to our capability module |
| [jchester/spc-kit](https://github.com/jchester/spc-kit) | 69 | PLpgSQL | 2025-08 | SPC in SQL — interesting architectural alternative |
| [AUS-DOH-Safety-and-Quality/PowerBI-SPC](https://github.com/AUS-DOH-Safety-and-Quality/PowerBI-SPC) | 72 | TS | 2026-07 | **Active.** SPC as a Power BI custom visual — govt healthcare |
| [nhs-r-community/NHSRplotthedots](https://github.com/nhs-r-community/NHSRplotthedots) | 61 | R | 2025-09 | NHS "Making Data Count" — institutional backing |
| [KensoBI/spc-chart](https://github.com/KensoBI/spc-chart) | 13 | TS | 2026-07 | Grafana panel: Xbar-R, Xbar-S, XmR. Commercial-adjacent (KensoBI) |
| [huft-jonathan/pyshewhart](https://github.com/huft-jonathan/pyshewhart) | 33 | Python | 2026-07 | Active, narrow (Shewhart only) |
| [emilopezcano/SixSigma](https://github.com/emilopezcano/SixSigma) | 19 | R | 2023-04 | The CRAN SixSigma package |
| [ReliaQualAssociates/ramstk](https://github.com/ReliaQualAssociates/ramstk) | 56 | Python | 2026-05 | RAMS analysis (reliability/availability/maintainability/safety) — serious, adjacent |
| [hviidhenrik/SPC](https://github.com/hviidhenrik/SPC) | 19 | Python | 2023-03 | Stale |
| [jjmartegarcia/sixsigmaspc](https://github.com/jjmartegarcia/sixsigmaspc) | 11 | Python | 2025-06 | Small |
| [omerfarukozturk/AnomalyDetection](https://github.com/omerfarukozturk/AnomalyDetection) | 13 | Python | 2021-09 | Nelson rules implementation |
| [dromation/open-fmea](https://github.com/dromation/open-fmea) | 33 | Python | 2024-06 | Stale |
| [Manojkumar-Alagesan/msa-simulators](https://github.com/Manojkumar-Alagesan/msa-simulators) | 0 | HTML | 2026-07 | Interactive Gage R&R simulators, self-contained HTML, no build step — nice format idea |
| [cowboy2718/FMEA](https://github.com/cowboy2718/FMEA) | 22 | R | 2018 | Dead |

**Notable absences:** no maintained Python DOE library surfaced in search (only `pyDOE` descendants, none ranked); no serious open Python MSA/Gage R&R package. **DOE and MSA are open ground.**

**Also:** healthcare/NHS is a surprisingly strong SPC constituency (NHSRplotthedots, SPCreporter, PowerBI-SPC, spc_healthcare_with_r) — a real adjacent market that is *not* automotive.

---

## 4. Cluster C — Open-source eQMS platforms

| Repo | ★ | Stack | Vertical |
|---|---|---|---|
| [MeyerThorsten/QAtrial](https://github.com/MeyerThorsten/QAtrial) | 12 | React 19 + Hono + PostgreSQL 16 + Prisma v7, AGPL-3.0 | Pharma/MedTech/CRO/GAMP. Live demo at qatrial.vercel.app, product site qatrial.com |
| [C-realize/OpenQMS](https://github.com/C-realize/OpenQMS) | 24 | JavaScript | Cloud-native lightweight QMS (OpenQMS.net) |
| [jonaesantos/odoo-qms-iso9001](https://github.com/jonaesantos/odoo-qms-iso9001) | 24 | Python/Odoo | ISO 9001 as an Odoo module |
| [ManishVlogs/qualvora](https://github.com/ManishVlogs/qualvora) | 0 | Angular | **Automotive eQMS** — LPA, NCR, CAPA, 8D. Our exact vertical, tiny |
| [abonnet-qarapulse/qara-pulse-eqms](https://github.com/abonnet-qarapulse/qara-pulse-eqms) | 4 | Makefile | Git-native eQMS for SaMD & AI medical devices |
| [erroronline1/caro](https://github.com/erroronline1/caro) | 0 | PHP | Cloud Assisted Records and Operations |
| [dromation/open-eqms](https://github.com/dromation/open-eqms) | 5 | kvlang | Enterprise QMS |

**QAtrial is the one to study.** It's the most complete open eQMS: 45+ Prisma models, append-only audit trail, e-signatures, 5-role RBAC + OIDC SSO, **multi-provider AI (Anthropic/OpenAI/OpenRouter/Ollama) behind a server-side proxy with 9 prompts**, SSE realtime, 12 languages, PWA offline, connectors for Jira/GitHub/SAP QM/LabWare LIMS. AGPL-3.0 + a commercial site = open-core play. That is a credible reference architecture for a Week-12+ platform, and a good argument for the React+FastAPI+Supabase path *if* a product signal ever appears.

---

## 5. Individual developer profiles worth tracking

| Profile | Why |
|---|---|
| **[jherrodthomas](https://github.com/jherrodthomas)** | The template for success in this niche. Watch cadence, README structure, release packaging. Getting external amplification (X/Twitter posts). |
| **[RBraga01](https://github.com/RBraga01)** (R. Braga, Portugal) | Nearest-exact competitor + prolific "enforcement pack" publisher across 6 domains. Watch what he ships next. |
| **[slightlynybbled](https://github.com/slightlynybbled)** | Maintains the one live Python Cpk/Ppk library. Potential collaborator/dependency rather than competitor. |
| **[MeyerThorsten](https://github.com/MeyerThorsten)** | QAtrial — open-core eQMS with real AI integration. Architecture reference. |
| **[cleverlab-ai](https://github.com/cleverlab-ai)** | Single-standard skill done well, multilingual. Lab/ISO 17025 niche. |
| **[robustagile](https://github.com/robustagile)** | Six-Sigma-in-R skill; statistical-correctness positioning. |
| **[timothyfraser](https://github.com/timothyfraser)** (`sysen`, 11★) | Cornell SYSEN 5300 course repo — academic channel for Six Sigma in R. |
| **[emilopezcano](https://github.com/emilopezcano)** | Author of the CRAN `SixSigma` package — the academic authority in this space. |
| **[EloisaElias](https://github.com/EloisaElias)** (`Elo_portfolio`, 11★) | Data scientist + Six Sigma portfolio positioning — a *portfolio* precedent, relevant to the career-asset angle. |

Also seen: `nandkishorlohar25-blip` — a corporate quality/business-excellence leader (12+ yrs) using their GitHub profile README as a résumé. Low signal technically, but confirms quality professionals are showing up on GitHub as a career move.

---

## 6. What this means for us

**Where we're already differentiated:**
1. **Real computation.** Cluster A generates documents; we compute EWMA/CUSUM, Box-Cox capability, run-rule gating, DOE screening on real data (SECOM). No skill pack does math.
2. **Tested engine.** CI, coverage baselines, release gates. Cluster A repos are markdown; Cluster B is unmaintained.
3. **DOE + MSA are open ground.** Nobody maintains a credible open Python DOE or Gage R&R library.

**Where we're behind:**
1. **Packaging/distribution.** We have no installable skill artifacts, no `npx skills add`, no marketplace presence. RBraga01 proves content parity isn't enough; jherrodthomas proves packaging is what converts.
2. **Reviewer/verification mechanic.** The builder+reviewer pair is the single most-copyable idea found. It maps perfectly onto our standards-fidelity preference — a reviewer that rejects a Cpk claim on non-normal data without Box-Cox is exactly our kind of gate.
3. **A visible artifact.** Both leaders ship dashboards / GitHub Pages sites. Our Streamlit app isn't discoverable from a repo listing.

**Concrete moves, cheapest first:**
1. Publish the SPC/MSA/capability engine as installable agent skills in the agentskills.io format (`npx skills add`) — the format is open and non-Claude-specific, so it's one artifact for Claude Code, Codex, Cursor, and Gemini CLI.
2. Adopt **builder + reviewer pairs**, where our reviewers cite the actual statistical precondition violated — a defensible edge over prompt-only competitors.
3. Chain skills on a file contract (their moat mechanic): `MSA → SPC → Capability → Control Plan`.
4. Add a GitHub Pages landing page with the Reflex/Streamlit screenshots. Table stakes for discovery in this niche.
5. Consider healthcare SPC as a second beachhead — an active, institutionally-funded constituency with no AI-agent offering at all.

**What NOT to chase:** a full eQMS. QAtrial has a 45-model head start with SSO, audit trails, and e-signatures, in a different (pharma) vertical. Compete on analytical depth and agent-native workflow instead.

---

## Sources

GitHub search API (repo keyword + topic queries, July 2026) and direct README/profile reads for every repo cited above, plus:

- [Agent Skills Ecosystem in 2026 — Agentman](https://agentman.ai/blog/agent-skills-ecosystem-report-2026)
- [agentskills.io — open Agent Skills standard](https://agentskills.io)
- [Claude Skills Directory — claudemarketplaces.com](https://claudemarketplaces.com/skills)
- [SkillsMP marketplace](https://skillsmp.com/)
- [LobeHub skills marketplace](https://lobehub.com/skills)
- [MCP Market skills directory](https://mcpmarket.com/tools/skills)
