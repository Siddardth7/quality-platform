# Launch Day Assets

## LinkedIn Post

---

I built a tool that automates aerospace Process FMEA — and it's now live. Here's what it does and why it matters.

**What is FMEA?**
Failure Mode and Effects Analysis is the structured risk assessment method mandated across aerospace (AS9100), automotive (IATF 16949), and medical device manufacturing. For every component or process step, you document how it can fail, what happens when it does, and how likely you are to catch it before the customer does. On a complex manufacturing line, this produces 30–100+ failure modes in an Excel sheet that someone has to manually score and prioritize.

**The problem I set out to solve:**
Engineering teams spend hours in Excel — calculating RPN scores (Severity × Occurrence × Detection), sorting rows, color-coding cells, building charts. It's repetitive, error-prone, and produces no reusable visualization. I wanted to reduce that to a 30-second upload.

**What I built:**
A Python-based FMEA Risk Prioritization Tool with a live Streamlit web interface:

→ Upload any CSV/Excel FMEA file (or load the built-in 30-row composite panel aerospace demo)
→ Automatic RPN calculation per AIAG FMEA-4 standard
→ Three criticality flags applied to every failure mode:
   — High RPN (>100): the standard corrective action threshold
   — Severity ≥ 9: mandatory flag regardless of RPN (safety rule from AIAG FMEA-4)
   — Action Priority H: a simplified AIAG 5th Ed. AP "High" tier implementation
→ Color-coded ranked table (Red = immediate action, Yellow = recommended, Green = monitor)
→ Interactive Pareto chart — see which 20% of failure modes drive 80% of risk
→ Severity × Occurrence heatmap — visual risk matrix with failure mode density
→ Live sidebar filters: RPN threshold slider + Severity ≥ 9 toggle
→ One-click PDF export (3-page report with charts) + Excel export (color-coded workbook)

**The engineering behind it:**
Every threshold in this tool has a documented source. RPN > 100 comes from AIAG FMEA-4 and is the standard corrective action cutoff used by Boeing, GE, and Honeywell supplier quality programs. The Severity ≥ 9 flag exists because a failure mode with S=9, O=1, D=1 gives RPN=9 — which RPN alone would rank near the bottom — but if it occurs even once, it's a safety incident. The Pareto 80/20 application helps teams focus corrective action investment where it produces the highest risk reduction per engineering hour.

**Built with:** Python · Streamlit · Plotly · pandas · fpdf2 · openpyxl · kaleido · pytest
**61 tests.** Every AIAG flagging rule has unit test coverage.

Try it live: https://fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app/
Full source: https://github.com/Siddardth7/fmea-risk-analyzer

If you work in aerospace, automotive, or any manufacturing quality role — I'd love your feedback on whether the risk thresholds match what your team uses in practice.

#Aerospace #Manufacturing #ProcessEngineering #FMEA #QualityEngineering #Python #Streamlit #RiskAnalysis #OpenSource #CompositeManufacturing

---

## Resume Bullet (copy-paste ready)

**FMEA Risk Prioritization Tool** | Python · Streamlit · Plotly · fpdf2 · openpyxl  
[[GitHub](https://github.com/Siddardth7/fmea-risk-analyzer)] [[Live Demo](https://fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app/)]

Built a production-grade Process FMEA analysis tool that automates RPN scoring (S×O×D), AIAG FMEA-4 criticality flagging (High RPN, Severity ≥ 9, Action Priority H), and risk visualization for aerospace manufacturing. Delivered as a Streamlit web application with interactive Pareto and Severity×Occurrence heatmap charts, live sidebar filtering, and one-click PDF/Excel report export. Engineered with a 4-layer architecture (validation → analysis → visualization → export), 61 pytest unit tests, and full AIAG source documentation for every threshold decision. Deployed on Streamlit Cloud.

---

## Deployment Checklist

- [x] `https://fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app/` live and loads demo dataset
- [x] GitHub repo is **public**
- [x] Tagged `v1.0-launch`
- [ ] Excel download produces color-coded .xlsx — verify post-deploy
- [ ] PDF download produces 3-page report with charts — verify post-deploy
- [ ] Screenshots captured and committed to `assets/` (see assets/README_ASSETS.md)
- [ ] README screenshot images updated once assets/ are captured
- [ ] Repo pinned to GitHub profile
- [ ] LinkedIn post published
- [ ] Resume updated
