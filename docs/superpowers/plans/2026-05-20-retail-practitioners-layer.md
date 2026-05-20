# Retail Practitioners Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a retail-friendly practitioner layer so the A-share analysis skill can learn executable habits from public retail-oriented investors without treating them as authorities or stock-picking proof.

**Architecture:** Keep institutional authors and retail practitioners in separate knowledge-base folders. `kb/retail-practitioners/` stores source-quality rules, reusable templates, and practitioner profiles; the skill reads the layer only for execution fit, ETF/portfolio alternatives, behavioral discipline, and risk-framing. Practitioner content must never override factual data, official announcements, backtests, or the user's own journal.

**Tech Stack:** Markdown knowledge base, YAML frontmatter, existing `a-stock-analyst` skill references.

---

### Task 1: Add Retail Practitioner Knowledge Base

**Files:**
- Create: `kb/retail-practitioners/_index.md`
- Create: `kb/retail-practitioners/_template.md`
- Create: `kb/retail-practitioners/source-quality.md`

- [ ] Create the directory and index.
- [ ] Define admission rules, hard red flags, scoring rubric, review cadence, and usage limits.
- [ ] Add a reusable profile template with fields for public track record, monetization, conflicts, use cases, and forbidden uses.

### Task 2: Seed Initial Practitioner Profiles

**Files:**
- Create: `kb/retail-practitioners/etf-save-the-world.md`
- Create: `kb/retail-practitioners/yinhang-luosiding.md`
- Create: `kb/retail-practitioners/wangjing-boge.md`
- Create: `kb/retail-practitioners/shen-qian.md`

- [ ] Add ETF/index-plan practitioners for allocation and drawdown discipline.
- [ ] Add a portfolio/value-practice profile for real-world position sizing and low-excitement execution.
- [ ] Keep all profile weights conservative and mark them unsuitable as direct stock recommendation sources.

### Task 3: Wire the Layer into the Skill

**Files:**
- Modify: `.claude/skills/a-stock-analyst/SKILL.md`
- Modify: `.agents/skills/a-stock-analyst/SKILL.md`
- Modify: `.claude/skills/a-stock-analyst/references/decision-tree.md`
- Modify: `.agents/skills/a-stock-analyst/references/decision-tree.md`
- Modify: `.claude/skills/a-stock-analyst/references/output-format.md`
- Modify: `.agents/skills/a-stock-analyst/references/output-format.md`

- [ ] Add retail practitioners as an execution-fit layer, not a factual authority layer.
- [ ] Add a retail-executability check in candidate and single-stock analysis.
- [ ] Add ETF/industry-leader/waiting alternatives to the report format.

### Task 4: Update Risk and Project Docs

**Files:**
- Modify: `kb/playbooks/risk-checklist.md`
- Modify: `kb/biases/known-biases.md`
- Modify: `README.md`
- Modify: `TODO.md`

- [ ] Add practitioner/source conflict checks to risk review.
- [ ] Document common retail-practitioner biases.
- [ ] Update README system composition.
- [ ] Record remaining follow-up work in TODO.

### Task 5: Verify

**Commands:**
- `find kb/retail-practitioners -maxdepth 1 -type f | sort`
- `diff -qr .claude/skills/a-stock-analyst .agents/skills/a-stock-analyst`
- `git status --short`

- [ ] Confirm files exist.
- [ ] Confirm `.claude` and `.agents` skill copies stay in sync.
- [ ] Confirm only intended files changed.
