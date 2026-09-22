---
name: context-index
description: Load this whenever it is unclear which other Skill is relevant, or at the start of a new task type not covered by the table below, to decide what else to load.
---

# ORYQ Context Index

| You are about to... | Load Skill(s) |
|---|---|
| Fix a reported bug | `known-bugs` → then the relevant domain skill below → the actual code |
| Add/change a product feature | `product-context` → `architecture-context` |
| Touch auth, JWT, RLS, RBAC, CORS | `security-context` (mandatory) |
| Touch the database / write a migration | `database-schema` + `security-context` |
| Touch scan.py / LLM providers / scoring / sentiment / hallucinations | `ai-llm-system` (mandatory — this system has a documented history of silent failures) |
| Decide "should I build X piece of infra" | `technical-debt` (is it already deferred on purpose?) |
| Plan next work / asked for status | `current-state-and-roadmap` |
| Unsure why something is built a certain way | `decisions-log` |
| Write or evaluate tests | `testing-strategy` |
| Prepare a production deploy | `architecture-context` + `hard-constraints` rule (pinned versions) |

Rules (`source-of-truth`, `hard-constraints`) are always loaded automatically and don't need to
be requested — this table is only for the conditional Skills.

For a repeatable multi-step procedure rather than background knowledge, check
`.agents/workflows/` instead of a Skill.
