---
name: add-a-feature
description: Standard procedure for adding a new feature or capability to ORYQ.
---

# Workflow: Add a Feature

1. Load `product-context` — does this fit the actual product/ICP, or is it scope creep from the
   aspirational PRD v2.0/TRD v2.0 vision that doesn't match the solo-founder stage?
2. Load `architecture-context` and `technical-debt` — can this be built on what already exists,
   or does it require infrastructure that's deliberately deferred? If deferred infra is genuinely
   needed now, say so explicitly rather than silently adding it.
3. Convert the request into functional + non-functional requirements and edge cases (empty
   states, invalid input, concurrent requests, provider failure) before writing code.
4. State the plan: what files/endpoints/tables are affected, what could break.
5. Implement the smallest version that satisfies the requirement.
6. Test — see `testing-strategy` Skill. For anything touching the scan pipeline, run a real scan
   against the reference brand case before declaring done.
7. Never show fabricated/placeholder data as if it were real — an honest "Pending" state is
   always correct over a fake plausible number (see `hard-constraints` rule).
8. Update `current-state-and-roadmap` Skill if this completes or changes a roadmap item.
9. Add an entry to `decisions-log` if you made a non-obvious technical choice along the way.
