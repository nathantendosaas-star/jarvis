# JARVIS Local Model Bridge — Handoff Notes

Built against `LOCAL_MODEL_INTEGRATION_SPEC.md`. This covers Tasks 1, 2, and
4 in full, and the local-agent side of Task 3 (backend hookup into
`backend/src/services/ai.py` is a repo-context change Jules should do inside
the actual FastAPI backend, not this standalone bridge — see "What's left"
below).

## Files in this drop

| File | Purpose |
|---|---|
| `jarvis_agent_pro.py` | Original CLI agent, unchanged in CLI behavior, extended with staged writes, restricted command mode, and an async streaming engine |
| `task_router.py` | Heuristic local-vs-cloud classifier (spec §2 routing) |
| `cloud_review.py` | Spec Task 4 — diffs staged files and sends them to a cloud model for approve/reject |
| `bridge_server.py` | FastAPI app — the actual HTTP/WebSocket bridge (spec Task 1) |
| `requirements.txt` | `pip install -r requirements.txt --break-system-packages` |

## Running it

```bash
ollama serve
ollama run jarvis-local   # confirm the tag responds
uvicorn bridge_server:app --host 0.0.0.0 --port 8008 --reload
```

Set `JARVIS_UI_ORIGINS` to the real frontend origin(s) before deploying —
defaults to `http://localhost:5173,http://localhost:3000` for local dev.
Set `OPENROUTER_API_KEY` (and optionally `OPENROUTER_MODEL`) if you want
`/api/local-agent/review-staged` to actually call a cloud reviewer instead of
returning "no reviewer configured".

## What the browser UI talks to

**Simple case — one task, one response:**
```
POST /api/local-agent/execute
{ "task": "add a docstring to parse_response", "require_review": true }
```
Returns the spec's `{status, final_answer, staged_files, execution_log}`
shape, plus `routed_to` and `route_reason` so the UI can show *why* something
got routed local vs. rejected to cloud.

**Live/streaming case (recommended for the chat UI):**
```
WS /ws/local-agent/execute
first client message: { "task": "...", "require_review": true }
```
Server pushes one JSON event per line as the model generates tokens and takes
actions — `token` events let the UI render the model "thinking" in real
time instead of showing a spinner for the whole multi-step task; `tool_call`
/ `observation` events let the UI show what the agent is actually doing
step by step. Full event list is documented in the docstring on
`stream_agentic_workflow_async` in `jarvis_agent_pro.py`.

**Reviewing staged changes:**
```
GET  /api/local-agent/staged              -> current manifest
POST /api/local-agent/review-staged       -> cloud verdicts per staged file
POST /api/local-agent/staged/apply        { "original_path": "utils.py" }
POST /api/local-agent/staged/discard      { "original_path": "utils.py" }
```
The bridge intentionally does NOT auto-apply cloud-approved changes — it
returns verdicts and lets the caller (UI or a small orchestration step in
`ai.py`) decide whether to auto-apply approved ones or still show them to
Nathan for a manual click. That's a product decision, not something to bake
into the bridge.

## Deliberate deviations from the literal spec (and why)

1. **`execute_command` is hard-restricted for bridge-triggered runs.** The
   spec doesn't call this out, but a browser-triggered, unattended task
   shouldn't get the same shell latitude as a human typing directly into the
   CLI. `restrict=True` is always passed when the bridge calls
   `execute_command`, which limits it to `SAFE_COMMAND_PREFIXES` (read-only
   / build-tool commands) no matter what `AUTO_APPROVE_COMMANDS` is set to.
   The CLI path (`main()` / sync `run_agentic_workflow`) is untouched.

2. **Task routing is a heuristic classifier, not another LLM call
   (`task_router.py`).** Spending a model call to decide whether to use a
   model is wasteful, and a 1.5B model isn't a reliable judge of its own
   limits. Current rules are intentionally conservative (see
   `FORCE_CLOUD_PATTERNS`) — auth, payments, schema, security, deploy, and
   multi-file/refactor language always route to cloud. Tune the pattern
   lists once you have real usage data from Nathan's actual tasks.

3. **The async engine is a separate code path from the sync CLI loop**, not
   a rewrite of it. `run_agentic_workflow` (sync) is untouched, so the
   existing CLI keeps working exactly as before. `stream_agentic_workflow_async`
   is the new engine both `/execute` and the WebSocket use — no duplicated
   loop logic between the two bridge endpoints, but zero risk to the CLI.

## What's left for Jules

1. **`backend/src/services/ai.py` hookup** (spec Task 3): add the online/offline
   check (internet reachability + `GET /api/local-agent/health` on this
   bridge) and route to `POST /api/local-agent/execute` (or the WS endpoint)
   when offline, tagging responses `[LOCAL MODEL - Staged for Review]` in
   the chat UI as the spec describes.
2. **Frontend wiring**: point the JARVIS React UI's WebSocket client at
   `/ws/local-agent/execute` and render the event stream (a simple reducer
   over `token`/`tool_call`/`observation`/`final` events is enough for v1).
3. **Auth on the bridge itself** — right now this bridge has zero auth,
   which is fine bound to `localhost` but not if it's ever exposed beyond
   that. Add an API key header check or bind it to a private network before
   any non-localhost deployment.
4. **Decide the auto-apply policy** for cloud-approved staged changes
   (see "Reviewing staged changes" above) and wire it into whichever layer
   makes sense — bridge, backend, or UI.
5. Real-world tune `task_router.py`'s pattern lists and `MAX_LOCAL_WORD_COUNT`
   against actual tasks Nathan throws at it; the current thresholds are
   reasonable starting points, not measured.

## Verified locally before handoff

- All four files import/compile cleanly, `bridge_server.py`'s FastAPI app
  registers all six REST routes plus the WebSocket route.
- `task_router.classify_task_verbose` correctly routes simple asks (rename,
  typo fix) to `local` and complex/high-stakes asks (auth, payments, schema
  migration, multi-clause requests) to `cloud`.
- Staged write/edit → manifest → apply/discard cycle tested end-to-end:
  staged edits do not touch the real workspace file until `apply_staged_file`
  is called, and the manifest correctly reflects additions/removals.
- Not yet tested against a live Ollama instance (none available in this
  environment) — verify the token-streaming path
  (`stream_ollama_async`/`stream_agentic_workflow_async`) against a real
  `jarvis-local` model before considering this done.
