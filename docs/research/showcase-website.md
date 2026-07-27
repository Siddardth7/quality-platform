# Standalone Showcase Website — End-to-End Research & Recommendation

**Status:** research / decision doc (no code changes)
**Date:** 2026-07-26
**Asked before:** Week 12 (frontend migration → Reflex)
**Question:** Should we build a standalone website to showcase this toolkit, given more toolkits are coming?
**Verdict:** **YES — build it. But as a *static* site, timeboxed to ~1 week, positioned as an engineering case study (not a SaaS), and structured as a multi-project hub from day one. Do *not* make the Reflex landing page the only front door.**

---

## 0. How to read this doc

§1 is the answer and the one-paragraph rationale. §2 establishes what you already have (the research is worthless without this baseline). §3–§6 are the four requested lenses: hiring manager, market, interview, and risk. §7 is the head-to-head option comparison. §8 is the recommendation with scope and a timebox. §9 is the open decision only you can make.

If you read one section, read **§3.4** — the cold-start finding is the single sharpest argument in this document, and it is the one that decides *standalone static* vs *fold into Reflex*.

---

## 1. Executive summary

**Build it.** But the reason is not the one you'd expect, and the shape is not the obvious one.

The obvious reasoning — *"a website makes the project look more professional"* — is weak, and on its own I'd have said no. Your README is already better than most portfolio sites; adding a second surface that says the same thing in nicer fonts buys almost nothing.

Three findings change the answer to yes:

1. **Your live demo is a liability at first contact, not an asset.** Streamlit Community Cloud sleeps. An evaluator who clicks "Live Demo" from your resume and gets a *"this app has gone to sleep"* wake screen has formed an impression before your code loads. Research consistently puts portfolio review at **under 45 seconds** — a 30–60s cold start consumes the entire budget. A static site loads in ~200ms and is the only fix that survives whatever framework you're on. This alone justifies the build. **The Reflex migration does not fix this — it inherits it**, since Reflex Cloud's free tier sleeps the same way.
2. **You have ~21,000 words of genuinely good written material trapped in a format that only engineers will open.** README, ROADMAP, DEFINITION_OF_DONE, ENGINEERING_SYSTEM_PLAYBOOK, and `frontend-migration.md` are the substance of a strong site. They are currently addressed exclusively to people comfortable browsing GitHub — which excludes a large share of the manufacturing-quality hiring audience you're actually targeting. **The content cost of this site is close to zero. You've already paid it.**
3. **"We're going to build more" is the strongest argument, and it's an argument about *timing*, not existence.** A per-project README does not compose. A portfolio hub built now, with Quality Platform as its first case study, costs one extra route. Retrofitting a hub around three finished projects later costs a rebuild plus URL churn. This is the cheapest it will ever be.

**What it is not:** it is not a marketing site for a product, it is not a place to put pricing or testimonials, and it is not the Reflex landing page. Those distinctions are load-bearing — see §4.2 and §6.4.

---

## 2. Baseline — what you already have (2026-07-26)

You can't evaluate "should we add a surface" without knowing how strong the current surface is. It's strong.

| Asset | State | Portfolio weight |
|---|---|---|
| Working deployed app | 5 tools under one shell, live on Streamlit Cloud | High — but see §3.4 |
| Test suite | 815 tests (README badge says 410 — **stale**) | Very high, rare |
| CI quality gate | ruff + mypy strict + coverage, enforced on protected `main` | Very high, rare |
| Coverage gates | `io`/`schema`/`scoring`/Control Plan at **100%**, SPC at 100% | Very high, rare |
| Release discipline | 11 tagged semver releases, weekly, `v0.1.0`→`v0.12.0` | Very high, very rare |
| Codebase | ~24k LOC Python, uv workspace monorepo, shared typed core | High |
| Written docs | ~21,400 words across README/ROADMAP/CHANGELOG/docs | High — currently under-exploited |
| Trade-off documentation | `frontend-migration.md` — two independent research passes, reconciled | **Exceptional** — see §5.2 |
| Screenshots | 4 PNGs in `assets/` | Medium — enough to start, thin for a site |
| Real-data proof | SECOM semiconductor case study shipped (v0.9.0) | High — domain credibility |
| Standards fidelity | AIAG-VDA AP table cell-verified against the handbook | High for domain audience |

**The honest read:** the *substance* is well above the bar for a senior portfolio piece. The gap is entirely in **distribution and first-contact legibility** — which is exactly the gap a site closes, and exactly the gap the Reflex migration does *not* close.

**Drift is already observable.** The README claims 410 tests; the true figure is 815. That's a stale badge, harmless in isolation, but it's the leading indicator of the #1 failure mode for showcase sites (§6.2). Design for it now.

---

## 3. Lens 1 — The hiring manager

### 3.1 What the scan actually is

Commonly cited industry figures put portfolio review at **under 45 seconds** before a keep/discard decision, with hiring managers weighting portfolios above résumés for technical evaluation (figures in the 73–87% range circulate widely; treat these as directional marketing-survey numbers rather than peer-reviewed research — the *direction* is well-supported even if the precision isn't). The consistent finding across sources is that a reviewer is answering three questions, fast:

1. **Can you build?**
2. **Can you ship?**
3. **Can you explain it?**

### 3.2 How you score today

- **Can you build?** — ✅ Emphatically. Five working tools, real math, real exports.
- **Can you ship?** — ✅ **This is your standout.** 11 weekly tagged releases with a CI gate that can't be bypassed is a stronger shipping signal than most candidates with production jobs can show. Almost nobody's portfolio project has a changelog, let alone twelve of them.
- **Can you explain it?** — ⚠️ **Yes, but only to someone who reads 21,000 words of Markdown on GitHub.** This is the gap.

### 3.3 The audience you're currently excluding

Your target roles sit at the intersection of manufacturing quality and software. The people gatekeeping those roles split into two populations:

| Reviewer | Comfortable in GitHub? | What convinces them |
|---|---|---|
| Software eng manager | Yes | The CI gate, coverage bars, monorepo architecture, commit discipline |
| **Quality / manufacturing manager** | **Often no** | **Cpk stability gate, AIAG-VDA AP fidelity, SECOM real data, PPAP/APQP fluency** |
| Recruiter / HR screener | No | A URL that loads and looks credible in 10 seconds |

The second and third rows are a large fraction of the people deciding whether you get an interview for a *manufacturing quality* role, and GitHub serves them poorly. A README that opens with shields.io badges and a Mermaid flowchart reads as noise to a quality manager who'd be genuinely impressed by "we refuse to report Cpk on an out-of-control process."

**A site is the only surface that can speak to both audiences simultaneously** — engineering depth one click down, domain credibility on the surface.

### 3.4 ⚠️ The cold-start finding — the decisive one

Your README's most prominent CTA is a **Live Demo** button pointing at Streamlit Community Cloud.

Streamlit Community Cloud **sleeps inactive apps**. A cold visitor gets an interstitial wake screen and a 30–60 second wait before anything renders.

Map that against a <45-second evaluation budget:

```
0:00  Reviewer clicks "Live Demo" from your resume
0:02  "This app has gone to sleep" / wake button
0:05  Reviewer clicks wake, waits
0:35  App still booting
0:40  Reviewer closes tab
```

**The single best artifact in your portfolio never rendered.** This is not hypothetical — it is the default behaviour of the platform you're on, for any visitor who arrives when the app is cold, which is most of them.

Three consequences, all important:

- **This is the strongest single argument for the site**, and it's an *availability* argument, not an aesthetic one.
- **The Reflex migration does not solve it.** Reflex Cloud's free tier sleeps too. Migrating from a sleeping Streamlit app to a sleeping Reflex app leaves this failure mode fully intact. If the migration's justification is "recruiter polish," this is the hole in it.
- **Therefore the front door must be static.** A CDN-hosted static site is always instantly up. It carries the screenshots, the story, and the architecture — so even if the demo is asleep, **the 45 seconds still land**. The live app becomes a bonus for the motivated visitor, correctly labelled ("*first load may take ~30s while the demo wakes*"), instead of a gate that fails silently.

This single finding flips the answer from "nice to have" to "build it."

---

## 4. Lens 2 — The market

### 4.1 The competitive landscape is real, crowded, and mature

The AIAG / IATF-16949 core-tools software space has established, well-funded incumbents shipping exactly your module list:

| Vendor | Coverage |
|---|---|
| **ETQ Reliance** | Full IATF 16949 — APQP, PPAP, FMEA, MSA, SPC, Control Plans |
| **ComplianceQuest** | Salesforce-based automotive QMS — CAPA, audits, APQP/PPAP, FMEA, MSA, SPC |
| **ISOQualitas PLM** | Design/process FMEAs, Control Plans linked to PFMEAs, AIAG/VDA-compliant |
| **InfinityQS** | SPC specialist, real-time process variation |
| **Total Lean Management** | Inspection + SPC reporting |

### 4.2 The strategic implication (this is the important part)

**Do not position this site as a product.** The moment your site has a "Pricing" page, a "Sign Up" button, or product-marketing voice, you have invited a direct comparison against ETQ Reliance — and you will lose that comparison instantly and unnecessarily, because you're a solo builder without ERP/MES integration, gage data acquisition, audit trails, or e-signature compliance.

**Position it as an engineering case study.** Then the comparison isn't "is this better than ETQ?" — it's "*does this person understand the domain these vendors serve, and can they build software at a professional bar?*" That question you win decisively, and the incumbent landscape becomes evidence *for* you: it proves the domain is real, commercially serious, and non-trivial.

The framing difference in practice:

| ❌ Product framing (loses) | ✅ Case-study framing (wins) |
|---|---|
| "The modern QMS platform" | "A working implementation of the AIAG core-tools loop" |
| Pricing tiers | Architecture decisions & trade-offs |
| "Get started free" | "Read the engineering log" / "Open the demo" |
| Fake customer logos | The SECOM dataset, real semiconductor data |
| Testimonials | Coverage gates and release history |

### 4.3 The labour-market tailwind

Manufacturing hiring in 2026 explicitly rewards the **domain + Python + data** intersection: employers want people who can "collect, interpret, and apply operational data," with Python called out repeatedly alongside SPC and yield analysis, and **74% of manufacturers report difficulty hiring data-capable engineers**.

That intersection is rarer than either skill alone. Most quality engineers can't build software; most software engineers don't know what Cpk is or why the stability gate matters. **You sit precisely on the scarce intersection, and your current README does not lead with it.** A site's headline should.

### 4.4 Market verdict

There is **no product opportunity here worth chasing** — the space is well-served, and pursuing it would trigger the `GO-FULL` escalation in `frontend-migration.md` §11 for no good reason. There is a **strong credibility opportunity**: the incumbents' feature lists are proof that the vocabulary you speak is commercially valuable. Use the market as *context*, never as a *target*.

---

## 5. Lens 3 — The interview

### 5.1 What actually happens in the room

Project deep-dive rounds run **45–60 minutes**: you present a project, then get interrogated. Interviewers assess two things — **technical depth** (do you understand *why* it's built this way?) and **judgment** (did you weigh alternatives and accept trade-offs deliberately?). The expected artifacts are an end-to-end architecture diagram, data flows, key design decisions, and the alternatives you rejected.

### 5.2 You have an unusually strong hand — and it's not the code

Most candidates fail deep-dives on judgment, not depth. They can describe what they built but not what they *didn't* build or why. You have written evidence of exactly that, which almost nobody has:

| Artifact | What it demonstrates | Interview power |
|---|---|---|
| **`docs/research/frontend-migration.md`** | Two independent research passes (Claude + Kimi), a reconciliation, a Go/No-Go gate, and a *documented escalation path deliberately not taken* | **Exceptional.** This is a staff-level artifact. |
| **Roadmap reroute (2026-07-10)** | Killed the AI-copilot headline in favour of MSA + real SECOM data — chose substance over buzzword | Very high — shows priority judgment |
| **The Cpk stability gate** | Refuses to report capability on an out-of-control process | **Domain judgment, not code.** Separates you from every dev who just implemented a formula. |
| **Schema promotion timing** | Contracts stayed in the FMEA app until they earned promotion to `quality_core` | High — deferred abstraction, correctly |
| **2:1 keep-to-throwaway analysis** | Quantified migration cost before committing | High — engineering economics |
| **OWASP formula-injection escaping in exports** | Security at the export boundary, coverage-gated | High — unprompted security thinking |
| **"Cut scope, not quality"** | Documented weekly discipline, honoured across 11 releases | High — shows it's a real system, not a slogan |

### 5.3 The finding

**The highest-value page on this site is not the hero. It's an engineering-decisions page.**

A hero converts a 5-second glance into a 45-second scan. A decisions page converts a 45-second scan into a **45-minute interview conversation you've already rehearsed** — because you wrote the arguments down months earlier, with dates.

That page is nearly free to produce: `frontend-migration.md`, the roadmap reroute rationale, the stability gate, and the schema-promotion decision already exist as prose. It needs curation and a URL, not authoring.

**Second-order benefit worth naming:** publishing decision docs with dates on them makes your judgment *verifiable*. "I considered React + Supabase and rejected it pending a product signal" is a claim. A dated document laying out the Go/No-Go gate is evidence. In a deep-dive, that difference is enormous.

---

## 6. Lens 4 — Risks and the honest counter-arguments

### 6.1 Opportunity cost (the real one)

Every hour on the site is an hour not on Week 12 or v1.0.0. The counter: the site is **~80% content assembly, ~20% engineering**, and the content already exists. It draws from a different budget than the migration does, and it is not competing for the same kind of attention.

But the site **must not** grow into a second engineering project. That failure mode is the reason for the hard timebox in §8.

### 6.2 ⚠️ Maintenance drift — the #1 killer, already visible

A site claiming `v0.9.0 · 410 tests` while the repo is at `v0.12.0 · 815 tests` is **actively worse than no site**: it converts your best signal (release discipline) into evidence of neglect.

You already have this bug. Your README badge says 410; reality is 815.

**Mitigations, in order of laziness:**
1. **State no numbers the site can't derive.** Link to GitHub Releases and the CI badge rather than hardcoding counts. Shields.io badges are already live-sourced — reuse them verbatim.
2. **Single source of truth.** Pull README/ROADMAP Markdown into the site at build time rather than copy-pasting. Rebuild on push.
3. **Date-stamp anything that can't be derived,** so a stale claim reads as a snapshot rather than a lie.

### 6.3 Polish/substance mismatch

A gorgeous site over a thin project is a *negative* signal — it reads as someone who optimises appearance over engineering. **Not your risk** (your substance is deep), but it sets the correct ceiling: design effort should be *proportionate*, and stop well short of bespoke animation work. Clean, fast, legible, dark-mode-correct. That's the bar. Anything beyond it is spend with no return.

### 6.4 Credibility traps to avoid absolutely

- ❌ **Fabricated social proof** — no invented testimonials, customer logos, or user counts. An evaluator who catches one fabricated element discards everything else you've claimed.
- ❌ **Pricing pages for a product that doesn't sell** — see §4.2.
- ❌ **Inflating scope** — "used by manufacturers" when it isn't. Your real story is strong enough; embellishment only creates downside.
- ❌ **A contact form that goes nowhere.** Use a `mailto:` or a link to LinkedIn. Dead forms are caught more often than you'd think.

### 6.5 SEO expectations — calibrate down

Ranking for "FMEA software" against ETQ's marketing budget is not happening, and chasing it is wasted effort. **Realistic and sufficient:** you rank for *your own name* + project name, and the site is what a recruiter finds when they Google you. That's the actual job. Static rendering delivers it; a sleeping app shell does not.

### 6.6 Hosting a second surface

Marginal. Static hosting on GitHub Pages / Vercel / Cloudflare Pages is free at this scale and requires no runtime. The only recurring cost is a domain (~$12/yr), and that's optional at the start.

---

## 7. Options compared

| # | Option | Effort | Cold-start fixed | Multi-project ready | Verdict |
|---|---|---|---|---|---|
| **A** | **Status quo** — README + Streamlit demo | none | ❌ | ❌ | Insufficient — §3.4 |
| **B** | **Reflex landing page only** (Week 12, already scoped S–M) | S–M | ❌ **inherits the sleep problem** | ❌ | **Necessary but not sufficient** |
| **C** | **Static showcase site, standalone** | S–M (~1 wk) | ✅ | ✅ if structured now | ✅ **RECOMMENDED** |
| **D** | **Full bespoke Next.js marketing site** | L | ✅ | ✅ | Over-buy — §6.3 |
| **E** | **C, but built as a per-project microsite** | S | ✅ | ❌ **rebuild at project #2** | Rejected — fails the stated premise |

### 7.1 Why B and C are complements, not alternatives

This is the crux, and it's worth being precise: **they serve different jobs and both should exist.**

- **B (Reflex landing page)** is the *app's* front door — what a user sees on arriving at the running application. Week 12 already scopes it. Keep it. It's small.
- **C (static site)** is the *project's* front door — what a recruiter, hiring manager, or Google finds. It must be instantly available, which means it cannot live inside the app.

```
  [ static site ]  ← resume link, Google, LinkedIn — always instant
        │
        ├─→ screenshots, architecture, decisions, case study   (always up)
        │
        └─→ "Open live demo"  →  [ Reflex app ]  ← may wake for ~30s
                                       └─→ Reflex landing (option B) → the 5 tools
```

This is the standard product-company split — marketing on a CDN, app on separate infra — and here it's not architectural cargo-culting: it's the direct fix for §3.4.

### 7.2 Recommended stack for C

Ladder logic, lowest rung that clears the bar:

1. ~~Plain GitHub Pages + Jekyll default theme~~ — free, but reads as an afterthought. Under-sells.
2. **MkDocs Material** — Python-native, fits your stack, renders existing Markdown near-verbatim, excellent search. **Best pure-laziness pick**, weakest hero.
3. ✅ **Astro (+ Starlight for the docs section)** — static by default, ships ~zero JS, renders your Markdown directly, real designed landing page, trivially deployable to Cloudflare/Vercel/GH Pages. **Clears the polish bar at S–M effort. Recommended.**
4. ~~Next.js~~ — a whole React app and a second toolchain to serve static pages. Over-buy (§6.3), and duplicates what Reflex already gives you.

> **Note on the ponytail ladder:** normally rung 2 (MkDocs) wins outright and I'd stop there. It doesn't here because the *deliverable is presentation quality* — a default docs theme fails the stated driver in a way it wouldn't for internal docs. Astro is the correct rung for this specific job, not an upgrade for its own sake.

**One caveat worth naming:** Astro is a JS toolchain, and your quality gate is Python-only. Keep the site **out of the main CI gate** — it's a content artifact, not gated software. Don't let it drag a JS test/type stack into a repo that has deliberately avoided one.

---

## 8. Recommendation

### 8.1 Decision

✅ **GO — build a standalone static showcase site (Option C), in addition to (not instead of) the Week 12 Reflex landing page.**

### 8.2 Scope — a hard, closed list

| Page | Content | Source | Priority |
|---|---|---|---|
| `/` | Hero: the domain+Python intersection (§4.3). Live badges. Screenshots. Loop diagram. Two CTAs: demo + GitHub. | README | **P0** |
| `/decisions` | Curated engineering log — migration research, roadmap reroute, stability gate, schema promotion | `docs/research/`, ROADMAP | **P0** — highest interview ROI (§5.3) |
| `/case-study/secom` | The platform run on real semiconductor data | ROADMAP §9, SECOM app | **P1** |
| `/architecture` | Monorepo, shared core, quality gate, coverage bars | README, DEFINITION_OF_DONE | **P1** |
| `/projects` | Hub index — Quality Platform + placeholders | new (~30 lines) | **P1** — the "more coming" answer (§1.3) |
| ~~pricing / testimonials / signup / blog~~ | — | — | ❌ **excluded** (§6.4) |

### 8.3 Timebox

**One week, hard stop.** If P1 isn't done, ship P0 and stop. The site is a distribution artifact, not a project — and a site that consumed three weeks has already cost more than it returns.

### 8.4 Non-negotiables

1. **Static rendering.** No runtime, no cold start. The entire point.
2. **Live-sourced badges**, not hardcoded numbers (§6.2).
3. **Honest demo labelling** — *"first load may take ~30s while the demo wakes."* Setting the expectation converts a failure into a minor caveat.
4. **Hub structure from day one**, even with one entry (§1.3).
5. **Case study voice, never product voice** (§4.2).
6. **Outside the Python CI gate** (§7.2).

### 8.5 Also fix, independently of this decision

- **The stale README badge** (410 → 815). Two minutes, and it's the exact drift class §6.2 warns about.
- **Screenshot refresh** after Week 12. Four Streamlit screenshots become obsolete the day Reflex ships — which is a small argument for sequencing the site *after* the migration (§9).

---

## 9. Decisions taken (2026-07-26, SME)

Sequencing and shape were open when this doc was drafted. They are now settled:

| Decision | Choice | Consequence |
|---|---|---|
| **Sequencing** | **Full site first**, Week 12 after | Schedule allows the complete build, not just P0. Week 12 slips by ~1 week. |
| **Scope** | **Portfolio hub**, Quality Platform as flagship | Hub routing built now (§8.2 `/projects`). |
| **Location** | **Separate repo**, Cloudflare/Vercel | Independent release cadence; see §9.1 — this changes the drift mitigation. |
| **Cold-start verification** | Not needed — behaviour known | §3.4 stands as written. |

### 9.1 ⚠️ Consequence of the separate-repo choice — drift mitigation changes

§6.2 recommended *"pull README/ROADMAP Markdown into the site at build time"* as the primary defence against stale claims. **A separate repo breaks that mitigation as written** — the content is no longer local at build time. The 410-vs-815 bug is exactly what happens when a second surface can't see the first.

Replacement, in order of laziness:

1. ✅ **Live-sourced badges only** (§6.2 mitigation 1) becomes *mandatory*, not merely preferred. Shields.io endpoints already read GitHub live — no sync required, no drift possible.
2. ✅ **Fetch at build time over HTTPS** — pull raw Markdown from `raw.githubusercontent.com` during the Cloudflare/Vercel build. Rebuild on a schedule or via a repo-dispatch webhook from `quality-platform`. Keeps one source of truth across two repos.
3. **Git submodule** — works, but adds friction to every clone for one directory of Markdown. Only if option 2 proves flaky.
4. ❌ **Copy-paste** — guarantees the drift this section exists to prevent. Do not.

**Rule for the split:** any fact that can change (test count, version, coverage, release date) is *derived or linked*, never typed. Anything typed by hand must be stable prose or date-stamped.

### 9.2 Consequence of the site-first choice — screenshots

All four screenshots in `assets/` are Streamlit-era and go obsolete the day Reflex ships. Building the site first means shipping on them knowingly.

- Keep the screenshot layer **swappable** — one directory, referenced by name, no per-image bespoke layout. Refresh is then a file replacement, not a redesign.
- Add a **Week 12 exit-criterion**: *refresh showcase screenshots + redeploy site.* Otherwise the site silently misrepresents the app the moment `v1.0.0` lands, which is the §6.2 failure mode wearing a different hat.

---

## 10. Summary of findings

| # | Finding | Confidence |
|---|---|---|
| 1 | **The sleeping demo is silently costing you first impressions.** Cold start (30–60s) exceeds the entire ~45s evaluation budget. Decisive argument for a static front door. | **High** |
| 2 | **The Reflex migration does not fix finding #1** — Reflex Cloud's free tier sleeps identically. B and C are complements, not alternatives. | **High** |
| 3 | **The site's content already exists** (~21,400 words + 4 screenshots). This is content assembly, not authoring. | **High** |
| 4 | **"More projects coming" is the strongest reason to build now** — hub structure costs one route today, a rebuild later. | **High** |
| 5 | **Case-study framing beats product framing.** Product voice invites a losing comparison with ETQ/ComplianceQuest/InfinityQS. | **High** |
| 6 | **The decisions page is the highest-ROI page**, above the hero — it converts a scan into a rehearsed 45-min deep-dive. | **Medium-High** |
| 7 | **A large part of your hiring audience can't read GitHub.** Quality managers and recruiters need a non-GitHub surface. | **Medium-High** |
| 8 | **Your shipping signal (11 weekly releases + enforced gate) is your rarest asset** and is currently under-surfaced. | **High** |
| 9 | **Maintenance drift is the top failure mode, and it's already present** (410 vs 815 tests). Design against it from line one. | **High** |
| 10 | **SEO ambition should be limited to your own name.** Ranking for "FMEA software" is not achievable and not needed. | **High** |

---

## Sources

- [How to Create a Software Engineer Portfolio in 2026 — Zencoder](https://zencoder.ai/blog/how-to-create-software-engineer-portfolio)
- [Developer Portfolio Guide 2026 — Hakia](https://hakia.com/skills/building-portfolio/)
- [What Hiring Managers Actually Expect from Portfolios in 2026 — TechVersions](https://techversions.com/web-technology/what-hiring-managers-actually-expect-from-beginner-web-development-portfolios-in-2026/)
- [Best Automotive Quality Software: Complete Guide 2026 — ISOQualitas](https://isoqualitas.com/en/best-automotive-quality-software-complete-guide-to-choose-in-2026/)
- [Best automotive quality management systems (QMS) 2026 — FitGap](https://us.fitgap.com/search/quality-management-systems-qms/automotive)
- [QMS Software for Manufacturing 2026: The Selection Guide — CSP](https://www.csp-sw.com/blog/qms-software-for-manufacturing-2026-the-selection-guide)
- [10 manufacturing skills companies are hiring for most in 2026 — Manufacturing Today](https://manufacturing-today.com/news/10-manufacturing-skills-companies-are-hiring-for-most-in-2026/)
- [Top Engineering Skills in High Demand in 2026 — SGS Consulting](https://sgsconsulting.com/blogs/top-engineering-skills-high-demand-2026)
- [Preparing for the technical deep dive interview — SWE Diary](https://swediary.substack.com/p/preparing-for-the-technical-deep)
- [Project Deep Dives — Playbooks for Software Engineers](https://playbooks.lgtm.fyi/interviews/pdd/)
- [Project Deepdives (Tips for Interview) — Medium](https://medium.com/interviewingsoftwareengineers/project-deepdives-tips-for-interview-3dd5399ee854)

**Internal:** `README.md`, `ROADMAP.md`, `docs/research/frontend-migration.md`, `docs/DEFINITION_OF_DONE.md`, `docs/ENGINEERING_SYSTEM_PLAYBOOK.md`, `git tag`, `.github/workflows/ci.yml`
