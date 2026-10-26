# MCP business coverage implementation plan

**Goal:** Complete LifeQuest business tools with safe remote Streamable HTTP; preserve stdio/SSE.
**Architecture:** Focused registration modules use existing authentication and serialization helpers and domain Services. No duplicated rewards or resource mutations.
**Spec:** Approved conversation design and 2026-09-14-lifequest-mcp-design.md.
**Constraints:** Isolated test databases/files; UTF-8; China dates; no production operations; no merge; root VERSION only.

## Task 1: Daily business
- [ ] Add failing registry and real lifecycle tests for shop, coins, backpack, review and daily detail reads.
- [ ] Implement app/mcp/daily.py registration using existing Service methods and schemas.
- [ ] Verify purchase replay/refund balances, ownership and serialization.

## Task 2: Collaboration and progression
- [ ] Add failing tests for notebook metadata/members and existing batch2 cultivation/immortal actions.
- [ ] Implement app/mcp/collaboration.py and progression.py using existing schemas/Services.
- [ ] Verify role boundaries, successful actions, prerequisite errors and replay where supported.

## Task 3: Remote transport and security
- [ ] Add failing tests for Streamable HTTP initialization/list/call, token expiry/revocation, session switches and credential isolation.
- [ ] Implement create_http_app and streamable-http CLI; strict Bearer protection for new transport and compatible SSE.
- [ ] Revalidate token sessions on each business call and prevent remote fallback to environment credentials.
- [ ] Run existing/new MCP tests with isolated state.

## Task 4: Delivery
- [ ] Document API/tool coverage, configuration, compatibility and security semantics.
- [ ] Increment VERSION from 1.14.7 to 1.15.0 and sync frontend.
- [ ] Run full backend pytest, frontend check:version/build and git diff --check.
- [ ] Review changes, fix findings, commit scoped files, push feature branch and create PR; no merge or deploy.
