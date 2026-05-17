# OpenHands Fork Specification

## Low-Footprint Custom Workflow + Phase Models + ContextKing (Web UI)

## 1. Scope and goals

### Goal
Create a maintainable fork of OpenHands that reliably enforces your workflow in **Web UI conversations** and supports:
1. Workflow gates (`PLAN.md` -> implementation -> `REVIEW.md` -> tests -> finish/PR).
2. Separate models for planning, implementation, and review.
3. Robust ContextKing (CK) behavior in UI sessions.
4. Minimal footprint so upstream rebases remain easy.

### Non-goals
1. Rewriting OpenHands agent-runtime internals.
2. Hard forking `openhands-sdk` or `openhands-agent-server` unless unavoidable.
3. Building a separate orchestration product outside OpenHands UI.

---

## 2. Research baseline

### 2.1 Upstream versions analyzed

1. `OpenHands/OpenHands` at commit `e3d9abfd014ffd4283d03071fdb88c1c8edc77f6`.
2. `Fredrik-C/ContextKing` at commit `e193c7f7353461bf5b246317b26755128d13e3e0`.

### 2.2 Key OpenHands behavior confirmed in source

1. Conversation agent type only has `default` and `plan` (`AgentType` enum).
   Source: `openhands/app_server/app_conversation/app_conversation_models.py`.
2. Planning mode is a dedicated flow with special planning prompt boundaries and planning tools.
   Source: `live_status_app_conversation_service.py` (`PLANNING_AGENT_INSTRUCTION`, planning tool selection, `system_prompt_planning.j2` override).
3. Sub-conversations inherit sandbox/git/LLM model from parent unless explicitly overridden.
   Source: `_inherit_configuration_from_parent()` in `live_status_app_conversation_service.py`.
4. Hook loading is workspace-file based and tolerant of failures (`None` on failure).
   Source: `hook_loader.py` and `live_status_app_conversation_service.py`.
5. Skills are loaded through agent-server `/api/skills` with all source flags enabled by default.
   Source: `app_conversation_service_base.py` and `skill_loader.py`.
6. Frontend already supports plan sub-conversation UX but only `code|plan` mode.
   Sources: `conversation-store.ts`, `use-handle-plan-click.ts`, `use-handle-build-plan-click.ts`, `conversation-websocket-context.tsx`.
7. Frontend/Backend start payload already carries `agent_type` and optional `llm_model`.
   Sources: `v1-conversation-service.types.ts`, `v1-conversation-service.api.ts`, `AppConversationStartRequest`.
8. Runtime profile switching exists (`/{conversation_id}/switch_profile`), proving per-conversation model switching is already supported operationally.
   Source: `app_conversation_router.py`.

### 2.3 OpenHands docs signals (official)

1. Hooks are repo-scoped via `.openhands/hooks.json` and can block `Stop`.
   Docs: `https://docs.openhands.dev/openhands/usage/customization/hooks`
2. Agent-server hooks endpoint reads `.openhands/hooks.json` from `project_dir`.
   Docs: `https://docs.openhands.dev/sdk/guides/agent-server/api-reference/hooks/get-hooks`
3. Agent-server skills endpoint supports source-merging and load flags (`load_public/load_user/load_project/load_org`).
   Docs: `https://docs.openhands.dev/sdk/guides/agent-server/api-reference/skills/get-skills`
4. `AGENTS.md` is always-on context loaded into system prompt at conversation start.
   Docs: `https://docs.openhands.dev/overview/skills` and `https://docs.openhands.dev/sdk/guides/skill`
5. Model routing exists in SDK (`llms_for_routing`) but is an SDK-level pattern, not directly exposed as a simple UI phase selector.
   Docs: `https://docs.openhands.dev/sdk/guides/llm-routing`

### 2.4 ContextKing protocol baseline

1. CK protocol requires keyword-map/file-first workflow (`ck get-keyword-map` -> `ck find-files` etc.) and allows grep fallback only inside narrowed scope.
   Source: `https://github.com/Fredrik-C/ContextKing/blob/e193c7f7353461bf5b246317b26755128d13e3e0/rules/ck-code-search-protocol.md`

### 2.5 CK-first compliance note for this research run

CK command execution in this workspace was not reliable for repo discovery (`ck find-scope` produced a shell error and empty index), so local discovery used `rg` fallback for this session. This is a local-environment limitation, not a recommended production behavior.

---

## 3. Why your current UI enforcement can appear inconsistent

Based on upstream behavior, these are the high-probability causes:

1. **Hook source is workspace-file dependent**: if `.openhands/hooks.json` is missing/incorrect in resolved `project_dir`, no hooks apply.
2. **Graceful degradation hides failures**: hook-loading errors are logged and startup continues; enforcement silently disappears.
3. **Only `code|plan` phase model exists in UI state**: no first-class review phase in standard UI flow.
4. **Sub-conversation model inherits parent by default**: plan/review model separation does not happen automatically.
5. **SDK/agent-server split**: many behaviors are now in external packages; patching wrong layer can create churn.

---

## 4. Design principles for the fork

1. **Additive changes only** in app-server/frontend where possible.
2. **No mandatory fork of `openhands-sdk`/`openhands-agent-server`** for phase workflow v1.
3. **Backwards-compatible defaults**: if workflow config is absent, OpenHands behaves exactly as upstream.
4. **Server-side enforcement first**: UI controls are convenience; backend must guarantee policy.
5. **File-count minimization**: keep patch set concentrated in app conversation + settings + small frontend surface.

---

## 5. Proposed architecture (minimum viable fork)

## 5.1 New capability: workflow phases

Introduce a phase abstraction independent from existing agent kind.

1. Phases: `plan`, `implement`, `review`.
2. Agent mapping:
   1. `plan` -> existing `agent_type=plan`.
   2. `implement` -> existing `agent_type=default`.
   3. `review` -> `agent_type=default` + review-specific system suffix + constrained tools policy (optional in v1).

This avoids immediate deep SDK changes.

## 5.2 New capability: phase-specific model selection

Add workflow model config to user settings (app-server owned, not SDK-owned):

```json
{
  "workflow_settings": {
    "enabled": true,
    "plan_model": "anthropic/claude-sonnet-4-5-20250929",
    "implement_model": "openai/gpt-5-2025-08-07",
    "review_model": "openai/o4-mini",
    "strict_enforcement": true
  }
}
```

Resolution rules:

1. Explicit request `llm_model` wins.
2. Else if phase present and `workflow_settings.enabled=true`, use phase model.
3. Else inherit current upstream behavior.

## 5.3 New capability: server-side workflow policy injection

Do not rely only on repo-local files. Add server-level policy merge:

1. Workspace hooks from `.openhands/hooks.json` (current behavior).
2. Global workflow hooks file from env (new), e.g. `OH_WORKFLOW_HOOKS_FILE`.
3. Optional org-level policy source (future).
4. Merge with deterministic precedence and de-duplication.

Recommended precedence:

1. Global policy hooks (cannot be removed by repo accidentally).
2. Workspace hooks (can add stricter checks).

This keeps your stop-gates always active in UI sessions.

## 5.4 New capability: explicit UI phase flow

Extend frontend from 2-mode to 3-phase workflow.

1. Add `review` mode in store.
2. Add “Review” action/button that:
   1. Switches to review phase.
   2. Creates/reuses sub-conversation (or switches profile in same conversation).
   3. Sends deterministic review prompt (`review_prompt.md` equivalent).
3. Keep existing Plan/Build behavior compatible.

Implementation option (least intrusive): create review as sub-conversation similar to planning flow, preserving workspace/sandbox reuse.

## 5.5 ContextKing integration in fork

Server-side, phase-aware approach:

1. Inject CK protocol summary in `system_message_suffix` when workflow enabled.
2. Ensure pre-tool hook includes CK guard in global merged hook config.
3. Keep explicit fallback mechanism (`CK_FALLBACK_REASON=...`) for controlled escape hatch.
4. Add startup verification check (`ck --version`) in setup hook; fail clearly if strict mode enabled and CK missing.

---

## 6. Concrete patch map (low-footprint)

## 6.1 Backend files (OpenHands fork)

1. `openhands/app_server/settings/settings_models.py`
   1. Add `workflow_settings` model field (top-level app setting).
2. `openhands/app_server/settings/settings_router.py`
   1. Persist/return `workflow_settings`.
3. `openhands/app_server/app_conversation/app_conversation_models.py`
   1. Add optional `workflow_phase` on start request.
   2. (Optional) extend `AgentType` with `review` later; not required in v1.
4. `openhands/app_server/app_conversation/live_status_app_conversation_service.py`
   1. Add phase-model resolver.
   2. Merge global + workspace hook configs.
   3. Add strict failure mode toggle (if policy missing and strict enabled).
5. `openhands/app_server/app_conversation/hook_loader.py`
   1. Add hook merge utility + schema validation path.
6. `openhands/app_server/app_conversation/app_conversation_router.py`
   1. Optional phase endpoints:
      1. `POST /api/v1/app-conversations/{id}/workflow/review`
      2. `POST /api/v1/app-conversations/{id}/workflow/phase`

## 6.2 Frontend files (OpenHands fork)

1. `frontend/src/stores/conversation-store.ts`
   1. Extend `ConversationMode` to include `review`.
2. `frontend/src/api/conversation-service/v1-conversation-service.types.ts`
   1. Add `workflow_phase` and optional workflow metadata.
3. `frontend/src/api/conversation-service/v1-conversation-service.api.ts`
   1. Pass phase value when creating/sub-starting conversations.
4. `frontend/src/hooks/use-handle-plan-click.ts`
   1. Keep behavior; add phase-aware model override invocation.
5. `frontend/src/hooks/use-handle-build-plan-click.ts`
   1. Use configured implement phase model/profile if needed.
6. Add new hook/component for review action:
   1. `use-handle-review-click.ts` (new).
7. Agent switch UI components:
   1. `change-agent-button.tsx` + menu components to expose review mode.

## 6.3 No-fork (external package) changes in MVP

1. `openhands-sdk` unchanged.
2. `openhands-agent-server` unchanged.

This is intentional for upgrade safety.

---

## 7. End-to-end workflow behavior (target)

1. User starts task in Web UI.
2. If workflow enabled:
   1. Backend tags conversation as workflow-managed.
   2. Global workflow hooks are merged and active.
3. Plan phase:
   1. Plan sub-conversation uses `plan_model`.
   2. Generates `PLAN.md`.
4. Build phase:
   1. Implement phase uses `implement_model`.
   2. Executes plan.
5. Review phase:
   1. Review phase uses `review_model`.
   2. Produces/updates `REVIEW.md` with required verdict token.
6. Stop:
   1. Stop hook enforces `PLAN.md`, `REVIEW.md`, tests, optional PR gate.

---

## 8. Rollout strategy

## Phase 0: instrumentation (1-2 days)

1. Add diagnostics endpoint/logging to show effective hook config + phase-model resolution for each start request.
2. Add explicit warning banner/event when hook loading fell back to none.

## Phase 1: enforcement foundation (2-4 days)

1. Add `workflow_settings` in backend + frontend settings retrieval.
2. Add global hook merge and strict mode.
3. Validate stop gate always triggers in UI conversations.

## Phase 2: per-phase models (2-3 days)

1. Add `workflow_phase` request field and resolver.
2. Wire plan/build actions to phase models.
3. Add review action using either sub-conversation or profile switch.

## Phase 3: review UX + hardening (3-5 days)

1. Review mode UI and prompts.
2. Add tests + telemetry + fallback messaging.
3. Document operator playbook.

---

## 9. Testing specification

## 9.1 Unit tests

1. Phase model resolution priority rules.
2. Hook merge precedence/de-duplication.
3. Strict mode behavior when policy/hooks unavailable.
4. Parent/sub-conversation inheritance with phase override.

## 9.2 Integration tests

1. Start conversation with workflow enabled -> verify effective hooks include stop gate.
2. Plan sub-conversation uses phase model.
3. Build action uses implement model.
4. Review action uses review model.
5. Stop denied when any artifact missing; allowed when all gates pass.

## 9.3 UI/E2E tests

1. Mode switch `code <-> plan <-> review`.
2. Build button still works with plan preview.
3. Review button flow writes/updates `REVIEW.md`.

---

## 10. Upgrade/rebase strategy

1. Keep fork changes in a dedicated namespace where possible:
   1. `openhands/app_server/workflow/*` (new files).
2. Keep invasive edits small and localized to:
   1. app conversation service/router/models,
   2. settings model/router,
   3. narrow frontend mode/components.
3. Rebase policy:
   1. Weekly fast-forward from upstream `main`.
   2. Run fork CI matrix after each rebase.
4. Prefer feature flags (`workflow_settings.enabled`) so upstream behavior remains intact by default.

---

## 11. Risks and mitigations

1. **Risk**: Upstream app-conversation refactors may move startup internals.
   1. **Mitigation**: Keep phase/hook logic in helper functions with minimal call-site touches.
2. **Risk**: CK binary missing in some sandbox images.
   1. **Mitigation**: strict mode startup check + actionable failure reason.
3. **Risk**: Review phase might mutate code unexpectedly.
   1. **Mitigation**: review prompt boundaries + optional tool restrictions.
4. **Risk**: UI state complexity with multiple sub-conversations.
   1. **Mitigation**: isolate plan/review conversation IDs explicitly instead of assuming index `0`.

---

## 12. Recommended implementation choice

### Recommendation
Implement a **thin, additive fork** that:
1. Enforces global workflow hooks server-side.
2. Adds phase-aware model resolution in app-server.
3. Extends UI from 2-phase (`code|plan`) to 3-phase (`code|plan|review`) with minimal UX additions.
4. Keeps SDK/agent-server package forks out of MVP.

This achieves your goals with the smallest long-term maintenance footprint.

---

## 13. Reference links

1. OpenHands repository: https://github.com/OpenHands/OpenHands
2. OpenHands hooks docs: https://docs.openhands.dev/openhands/usage/customization/hooks
3. OpenHands skills overview (`AGENTS.md` always-on context): https://docs.openhands.dev/overview/skills
4. OpenHands SDK skills/context guide: https://docs.openhands.dev/sdk/guides/skill
5. OpenHands model routing guide: https://docs.openhands.dev/sdk/guides/llm-routing
6. OpenHands agent-server get-hooks API: https://docs.openhands.dev/sdk/guides/agent-server/api-reference/hooks/get-hooks
7. OpenHands agent-server get-skills API: https://docs.openhands.dev/sdk/guides/agent-server/api-reference/skills/get-skills
8. ContextKing repository: https://github.com/Fredrik-C/ContextKing
9. ContextKing protocol file (pinned commit): https://github.com/Fredrik-C/ContextKing/blob/e193c7f7353461bf5b246317b26755128d13e3e0/rules/ck-code-search-protocol.md
