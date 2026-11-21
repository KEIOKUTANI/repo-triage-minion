# Demo Script & Hackathon #5 Submission Guide (1–5 Minutes)

## 1. 2–3 Minute Demo Video Walkthrough

1. **0:00–0:30 — Problem & Architecture**
   - Show `README.md` and `sample_target_repo/app.py` (contains an intentional hardcoded secret, a `ZeroDivisionError` `TODO`, and missing `LICENSE`/`tests`).
2. **0:30–1:15 — Automated Tests & Multi-Block Verification**
   - Run:
     ```bash
     PYTHONPATH=src python -m unittest discover -s tests -v
     PYTHONPATH=src python -m repo_triage_minion.cli verify-blocks sample_target_repo \
       --config agents.example.json --agent triage-echo
     ```
   - Highlight: `openminion 0.1.23`, deterministic tool snapshot, session continuity & isolation, 9 streaming events, and `AgentOutputValidationError` handling.
3. **1:15–2:30 — Real Model-Backed Run (Required by Hackathon Objective)**
   - Export `OPENAI_API_KEY` (or `GEMINI_API_KEY` / `CORTENSOR_API_KEY` / local Ollama) and run:
     ```bash
     PYTHONPATH=src python -m repo_triage_minion.cli triage sample_target_repo \
       --config agents.example.json --agent triage-openai --stream \
       --followup "Which single issue should we fix first before release?"
     ```
   - Show the live tool-backed triage output + follow-up answer in the same durable session.
4. **2:30–3:00 — Building Blocks Findings & Feedback**
   - Briefly show `BUILDING_BLOCKS_TESTED.md` and `WHAT_WE_LEARNED.md` (especially the `default_channel` minimal-config finding and SQLite `ResourceWarning` finding).

---

## 2. Final Submission Checklist (Cortensor Hackathon #5)

- [ ] Register on DoraHacks: https://dorahacks.io/hackathon/2418/detail
- [ ] Star & Fork `https://github.com/openminion/openminion`
- [ ] Follow `@OpenMinion` & `@cortensor` on GitHub and X, and join Cortensor Discord (`https://discord.gg/cortensor`)
- [ ] Push `repo-triage-minion/` to your public GitHub repository (do **not** commit `.venv/` or any API keys)
- [ ] Record the 1–5 minute demo video showing a real model-backed run
- [ ] Submit PR to the dedicated Cortensor Hackathon #5 submission repository + submit build on DoraHacks before **2026-12-19 16:59 JST**
- [ ] *(Optional Bonus)* Open a GitHub issue on `openminion/openminion` for Finding #1 (`default_channel` minimal config) or Finding #2 (SQLite `ResourceWarning`), wait for maintainer acknowledgment, and submit a fix PR!
