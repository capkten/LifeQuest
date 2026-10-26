# MCP business coverage implementation plan

**Goal:** Complete LifeQuest business tools with safe remote Streamable HTTP; preserve stdio/SSE.
**Architecture:** Focused registration modules use existing authentication and serialization helpers and domain Services. No duplicated rewards or resource mutations.
**Spec:** Approved conversation design and 2026-09-14-lifequest-mcp-design.md.
**Constraints:** Isolated test databases/files; UTF-8; China dates; no production operations; no merge; root VERSION only.

## Task 1: Daily business
- [x] Add failing registry and real lifecycle tests for shop, coins, backpack, review and daily detail reads.
- [x] Implement app/mcp/daily.py registration using existing Service methods and schemas.
- [x] Verify purchase replay/refund balances, ownership and serialization.

## Task 2: Collaboration and progression
- [x] Add failing tests for notebook metadata/members and existing batch2 cultivation/immortal actions.
- [x] Implement app/mcp/collaboration.py and progression.py using existing schemas/Services.
- [x] Verify role boundaries, successful actions, prerequisite errors and replay where supported.

## Task 3: Remote transport and security
- [x] Add failing tests for Streamable HTTP initialization/list/call, token expiry/revocation, session switches and credential isolation.
- [x] Implement create_http_app and streamable-http CLI; strict Bearer protection for new transport and compatible SSE.
- [x] Revalidate token sessions on each business call and prevent remote fallback to environment credentials.
- [x] Run existing/new MCP tests with isolated state.

## Task 4: Delivery
- [x] Document API/tool coverage, configuration, compatibility and security semantics.
- [x] Increment VERSION from latest origin/main 1.15.0 to 1.16.0 and sync frontend.
- [x] Run full backend pytest, frontend check:version/build and git diff --check.
- [x] Review changes and fix findings.
- [x] Commit scoped files and push `feat/mcp-business-coverage`; no merge or deploy.
- [ ] Create PR against main (prepared body; GitHub API login is required, Git SSH push succeeded).

## Updated remote baseline audit

Fetched origin/main `260f15e` after discovering local main was behind. Rebased feature branch, preserving existing 4 focus tools and all latest task schedules, weekly review, action center and explicit note-link capabilities. Added execution and retreat registration modules and real tests for those flows. Shared retreat settlement fixes are necessary to prevent instant rewards, repeated/concurrent settlement and linked-task reward bypass; existing Services remain the sole business implementation.

## Verification evidence

- Exact backend requirements on Python 3.12.14 / SQLAlchemy 2.0.23, disposable Docker container with no external network or production volumes: **716 passed** in 463.50s.
- Frontend: **247 tests passed**; `npm run check:version` and `npm run build` passed for **1.16.0**.
- Independent security and transaction review findings were fixed and regression tested.
- Final MCP subset: **102 passed** in 61.46s, including 173 unique registered tools, real stdio/SSE/HTTP transport tests, late management additions and note revision conflicts.
