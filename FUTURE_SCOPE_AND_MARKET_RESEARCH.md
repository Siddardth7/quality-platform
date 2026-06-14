# FMEA Risk Analyzer — Future Scope & Market-Gap Research

*Strategy document. Purpose: turn a working FMEA tool into (a) something a real engineering audience adopts, and (b) a portfolio centerpiece that makes hiring managers stop scrolling. Every recommendation below is tied to a researched market gap or a documented hiring signal — sources are listed at the end.*

---

## 1. Executive summary

The FMEA software market is real, growing, and dominated by expensive, heavyweight tools. The lightweight end is still owned by Excel — which the industry openly calls the "spreadsheet graveyard." That leaves a genuine middle gap: a **free, modern, standards-current, collaborative FMEA tool** that small teams and individual engineers can actually use. This project already sits in that gap. The work ahead is to (1) modernize the methodology to the current AIAG-VDA standard, (2) earn the "engineering-level, standard website" bar with architecture and ops upgrades, and (3) package it so the GitHub repo and live demo read as senior-engineer work.

The single highest-leverage finding: **the tool computes RPN, but the automotive industry officially replaced RPN with Action Priority (AP) in 2019.** Closing that one gap is both the strongest product differentiator and the most credible signal of domain depth to a hiring manager.

---

## 2. Market landscape (what exists today)

The FMEA software market is led by a handful of mature, enterprise-grade vendors. The current 2026 field, in roughly the order it shows up in buyer guides:

| Tool | Position | Notable strength | Practical weakness |
|---|---|---|---|
| **Relyence FMEA** | Premium leader | AI-driven insights, collaborative workflows, integrations | Enterprise pricing, heavy |
| **APIS IQ-FMEA** | Automotive standard-bearer | Syntax/structure-based, deeply AIAG-VDA aligned | Steep learning curve, costly |
| **ReliaSoft XFMEA** (HBM Prenscia) | Reliability-engineering anchor | Advanced RPN + reliability modeling | Complex, license-gated |
| **PLATO e1ns** | AI-assisted DFMEA | Standards-compliant, AI-assisted authoring | Enterprise procurement |
| **Sphera, Jama, ALD, DataLyzer, SETEQ** | Adjacent / niche | QMS, requirements, or process integration | Built for large orgs |

Market signals worth designing toward: **cloud-based deployments are ~46% of the market** and growing because of scalability; **~29% of FMEA tools now incorporate AI-driven failure prediction**; and adoption is concentrated in **automotive (39%), aerospace (21%), and electronics (18%)**. Pricing at the professional tier is steep — roughly **€5,200 per license plus ~21% annual maintenance**, and several vendors don't publish pricing at all.

The takeaway is not "compete with Relyence." It is: the paid tier is expensive and complex by design, which pushes the entire small-team and individual-engineer segment back onto spreadsheets.

---

## 3. Where the gap actually is

Two gaps, stacked.

**Gap 1 — the methodology gap (product credibility).** With the 2019 AIAG-VDA harmonized handbook, the automotive industry replaced the Risk Priority Number with **Action Priority (AP)**. RPN's documented flaws are well known: it weights Severity, Occurrence, and Detection equally, and gives no threshold at which action becomes mandatory — so a catastrophic, low-frequency failure can score *lower* than a trivial frequent one. AP fixes this with a severity-first lookup table that returns **High / Medium / Low** priority. This project currently computes RPN only. Any engineer or hiring manager with automotive/quality exposure will notice that immediately. Adding AP (while keeping RPN for legacy/teaching) moves the tool from "student project" to "knows the current standard."

**Gap 2 — the segment gap (market opportunity).** Excel persists because it's free and instantly accessible, but the industry itself documents its failure mode: the "spreadsheet graveyard" where FMEAs are saved once and never updated; broken linkage between the FMEA, the Control Plan, and the Process Flow Diagram; and the absence of version control and audit trails. Meanwhile dedicated software solves those problems but is "overly complex and costly for small teams or companies performing occasional FMEA analyses." **The unserved middle is a free/low-cost tool that gives you version history, validation, collaboration, and a clean UI without enterprise procurement.** That is precisely the niche a strong open-source project can own.

How to close it: be the tool that is *as easy to start as a spreadsheet* but *escapes the spreadsheet's failure modes* — structured validation, AP-based prioritization, revision history, and a shareable link instead of an emailed `.xlsx`.

---

## 4. Feature roadmap (prioritized by impact × differentiation)

Organized in three tiers. Tier 1 is what makes the tool *correct and credible*; Tier 2 makes it *adopted*; Tier 3 makes it *remarkable*.

### Tier 1 — Standards & correctness (do these first)

- **Action Priority (AP) engine.** Implement the AIAG-VDA AP lookup (S→O→D → High/Medium/Low). Show AP alongside RPN; let the user toggle the prioritization basis. This is the headline differentiator versus a typical RPN-only project.
- **Editable S/O/D rating tables (1–10).** Let users load standard or custom severity/occurrence/detection scales rather than hardcoding. Ship sensible AIAG-VDA defaults.
- **Structured FMEA model, not flat rows.** Move toward the relational structure real FMEAs need (Function → Failure Mode → Effect → Cause → Control), which is exactly what spreadsheets handle badly.
- **Recommended-action tracking.** Owner, due date, status, and *re-evaluated* S/O/D after action — the "before/after" that real FMEA worksheets require.

### Tier 2 — Adoption & collaboration (close the segment gap)

- **Persistence + project workspace.** Save multiple FMEAs, revisit, and revise — directly attacks the "spreadsheet graveyard."
- **Revision history / audit trail.** Issued versions are frozen; changes are logged. This is a hard requirement in regulated industries and a known Excel weakness.
- **Collaboration:** comments, shareable read-only links, and (eventually) multi-user editing.
- **Control Plan + Process Flow linkage.** The connection Excel can't maintain cleanly; even a lightweight version is a strong differentiator.
- **Industry templates.** Automotive PFMEA/DFMEA, medical-device aligned to **ISO 14971** risk management, electronics. Templates lower the activation cost for new users.

### Tier 3 — Differentiation & "wow" (what gets shared)

- **AI-assisted failure-mode suggestion.** Given a component/function, suggest likely failure modes, effects, and causes for the engineer to accept/edit. This matches where the market is moving (29% of tools now have AI failure prediction) and is the single most demo-able, shareable feature. Frame it as *assistive*, with the human in control.
- **Trend & analytics dashboard.** Risk reduction across revisions, top recurring causes, action burn-down — turns a one-shot analysis into an ongoing instrument.
- **Public API + integrations.** A documented REST API (import/export, programmatic scoring) and export to common QMS/PLM formats.
- **What-if simulation.** Adjust S/O/D and watch AP/RPN and the risk matrix update live.

A clean way to sequence this: Tier 1 lands in the **next minor release**, Tier 2 spans the **next major**, and Tier 3 items become headline features that justify subsequent majors. (This maps directly onto the version-bump plan in `AUDIT_AND_ROADMAP_PROMPT.md`.)

---

## 5. Becoming an "engineering-level, standard website"

Today's stack (Streamlit + pandas) is excellent for getting the analysis right quickly. But Streamlit is widely understood as a **prototyping** framework: no real backend layer, limited routing/multi-page structure, full reruns that get expensive on large data, no server push, and limited control over exact design. "Streamlit → Dash → React" is the documented evolution path as a data app becomes a product. The decision is about *positioning*, so make it deliberately:

**Option A — Stay Streamlit, but professionalize it.** Cheapest path. Add `@st.cache_data` discipline, real session/state handling, a polished theme, and persistence behind it. Good enough to demo and to serve small teams. Honest framing for a portfolio: "rapid, correct, deployed."

**Option B (recommended for the hiring-manager goal) — Split into a product architecture.** Keep the proven Python analysis core, but expose it as a **FastAPI** service (async, automatic OpenAPI docs, Pydantic validation — and you already use Pydantic v2, so the schema layer ports cleanly), and build a real front end in **React/Next.js**. This demonstrates exactly the skills hiring guides flag as high-signal in 2026: API-based web apps, full-stack range, and a product (not a dashboard) mindset. Streamlit can remain as an internal/admin or "labs" surface.

Either way, the **engineering-standard bar** is met by the surrounding system, not just features:

- **CI/CD that's visible:** badges, automated tests, lint, type-check, coverage gate, and a deploy pipeline (the audit prompt already pushes most of this).
- **Live, always-on demo** with seeded sample data and a one-click "try it" path. A deployed demo with real functionality is repeatedly cited as the #1 portfolio differentiator.
- **Observability & quality:** structured logging, error handling that never shows a stack trace to a user, and basic metrics.
- **Docs as a product:** a README that sells the problem and shows screenshots/GIFs, an architecture diagram, an API reference, and a short "design decisions" write-up.
- **Security & compliance posture:** input validation, CSV-injection-safe exports, dependency scanning — especially credible given the regulated industries FMEA serves.

---

## 6. Making it land with hiring managers

The research on hiring is blunt: **73% of hiring managers weight a strong portfolio over a perfect résumé**, and GitHub profiles with strong READMEs and consistent commit history get **~3x more visits and more interview requests**. What they're actually evaluating is *how you think and build*, not feature count. Translate that into concrete moves for this repo:

1. **Lead with a real problem, solved.** The README's first screen should say: *the industry replaced RPN with AP in 2019; most free tools never caught up; this one did.* That single sentence signals domain awareness most candidates lack.
2. **Ship a live demo, not a screenshot.** Deployed, seeded, instantly clickable. This is the highest-ROI single action.
3. **Show the engineering, not just the app.** Surface the CI badge, the test/coverage numbers, the architecture diagram, and a CHANGELOG with real semantic versions. The commit history already reads like disciplined work (conventional commits, refactors, CI additions) — make that legible on the README.
4. **Quality over quantity.** Three-to-five *finished, polished* capabilities beat a sprawl of half-features. Pick the AP engine + persistence + one Tier-3 "wow" (AI suggestion *or* trend dashboard) and make those excellent.
5. **Write the decisions down.** A short "why FastAPI/React over staying in Streamlit," "why AP over RPN," "what I'd do with more time" section demonstrates senior judgment — the thing interviews actually probe.
6. **Avoid the tutorial-clone smell.** FMEA tooling is inherently *not* a to-do/weather/Netflix clone; lean into that. It's a real domain with standards, regulated users, and measurable risk-reduction outcomes — say so.

---

## 7. Recommended next 3 moves

1. **Implement the AP engine** (Tier 1) and reframe the README around standards-currency. Highest credibility-per-hour.
2. **Add persistence + revision history** (Tier 2) to escape the spreadsheet graveyard and unlock the small-team segment.
3. **Stand up a live, seeded demo** and, if pursuing the hiring goal seriously, begin the **FastAPI core + React front end** split — then ship **one** Tier-3 feature (AI-assisted failure modes is the most shareable) as the headline.

Everything here is compatible with the phased audit and version-bump plan in `AUDIT_AND_ROADMAP_PROMPT.md`: run the audit first to harden what exists, then execute this roadmap tier by tier, mapping each tier to a SemVer release.

---

## Sources

- [Top 10 Best FMEA Software of 2026 — Gitnux](https://gitnux.org/best/fmea-software/)
- [6 Best FMEA Software for 2026 — Centrum FMEA](https://fmea.com.pl/6-best-fmea-software/?lang=en)
- [10 Best FMEA Software for Risk Analysis in 2026 — Visure Solutions](https://visuresolutions.com/alm-guide/best-fmea-software/)
- [5 Best FMEA Software Tools for Reliability (2026) — Fabrico](https://www.fabrico.io/blog/best-fmea-software-tools/)
- [FMEA Software Market Size, Trend Report 2033 — Market Growth Reports](https://www.marketgrowthreports.com/market-reports/failure-mode-and-effects-analysis-fmea-software-market-112759)
- [RPN vs Action Priority (AP) — Why RPN is Outdated — Quality Assist](https://quasist.com/fmea/rpn-vs-ap-action-priority/)
- [Action Priority in FMEA (AIAG-VDA Standard) — Quality Assist](https://quasist.com/fmea/action-priority-in-fmea/)
- [AIAG & VDA FMEA — Quality-One](https://quality-one.com/aiag-vda-fmea/)
- [Overview of Key Changes to AIAG-VDA FMEA — FMEA-Training](https://fmea-training.com/key-changes-aiag-vda-fmea/)
- [Is Excel the right tool for FMEA? — DataLyzer (Marc Schaeffers)](https://datalyzer.com/wp-content/uploads/2017/03/ExcelrighttoolforFMEA.pdf)
- [Why Choose FMEA Software over an Excel template — Relyence](https://relyence.com/products/fmea/move-over-excel/)
- [Software Engineer Portfolio (Examples & Tips 2026) — whatisthesalary](https://whatisthesalary.com/guides/software-engineer-portfolio/)
- [The Portfolio Projects That Actually Get You Hired in 2026 — DEV](https://dev.to/devraj_singh7/the-portfolio-projects-that-actually-get-you-hired-in-2026-1l0e)
- [Top 10 Full Stack Portfolio Projects for 2026 — Nucamp](https://www.nucamp.co/blog/top-10-full-stack-portfolio-projects-for-2026-that-actually-get-you-hired)
- [Dash vs Streamlit vs React for Data Applications — Lean Data Engineer](https://leandataengineer.com/blog/dash-vs-streamlit-vs-react-for-data-applications/)
- [Serving an ML Model with FastAPI and Streamlit — TestDriven.io](https://testdriven.io/blog/fastapi-streamlit/)
