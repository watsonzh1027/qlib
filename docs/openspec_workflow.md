# OpenSpec Workflow Guide

Source: openspec/AGENTS.md

## When to Use OpenSpec
- Your request mentions: proposal, spec, change, plan.
- Adds capabilities, breaking changes, architecture shifts, performance/security impact.
- The request is ambiguous and needs an authoritative spec.

I will open and follow `@/openspec/AGENTS.md` before drafting any proposal.

## What Is Produced
- A change proposal in `openspec/proposals/` with zero-padded number and slug, e.g. `0002-new-feature.md`.
- Typical sections: Status, Summary, Motivation, Goals/Non-Goals, Design/Architecture, Data Flow, Implementation Plan, File Changes, Configuration, Testing, Risks, Dependencies, Rollout, Success Metrics, Future Work, References, Approval Checklist.
- References to related docs (e.g., `docs/data_feeder.md`, `openspec/project.md`).

## Proposal Lifecycle
- DRAFT: Initial proposal based on your request.
- REVIEW: You comment or request edits (e.g., change intervals).
- APPROVED: You explicitly approve; status set to APPROVED.
- IMPLEMENTATION: Code changes in small steps, following one-error-at-a-time.
- DONE: Docs updated; proposal marked completed.

## How We Collaborate
- You provide goals, constraints, and acceptance criteria.
- I draft/update the proposal and ask targeted questions if unclear.
- After approval, I implement in small, reviewable steps:
  - I only modify files in the working set; otherwise I will ask you to add them or use `#codebase`.
  - Changes are grouped by file with minimal diffs (`...existing code...` where unchanged).
  - I ask for confirmation after each fix before proceeding (one-error-at-a-time).
- After each resolved problem, an `issues/<NNNN>-<desc>.md` entry is created per standards.

## Conventions Followed
- Keep the managed block in `AGENTS.md` intact so `openspec update` can refresh it.
- OpenSpec numbering: `0001`, `0002`, ...
- Assume `conda activate qlib` before commands and ensure Qlib compatibility.
- Short, impersonal responses; minimal diffs in code suggestions.

## What I Need From You
- Explicit approval to move a proposal from DRAFT to APPROVED.
- Add files to the working set (or use `#codebase`) before I modify them.
- Explicit permission to proceed to the next step/error after each review.