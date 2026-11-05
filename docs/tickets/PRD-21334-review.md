# PRD-21334 · Code review

## Round 1 · 2026-11-05 · reviewed dev/PRD-21334 @ 64150f6 (base main @ d74a005)

Verdict: changes requested

### Scope

Full branch diff `d74a005...64150f6` in `MSPbotsAIFramework/vercel-mcp` (single-repo `vendor-mcp` ticket, no platform component). Reviewed against the product design, tech design, `docs/tickets/PRD-21334.ac.json`, and the Self-test section in `docs/tickets/PRD-21334.md`, per `legs/review.md` R3 and the MCP-specific checklist in `references/mcp-track.md` 4.3 (credential handling, structured errors, README Connector section, no-Chinese rule, SOP §14 checklist).

Verified independently (not just re-reading the Self-test claims):
- `uv run pytest` on `dev/PRD-21334` @ `64150f6`: 10 passed, 0 failed — matches the Gates table.
- README's "MSPbots Connector" section is byte-identical to `~/.claude/skills/vendor-mcp-development/reference/readme-connector-section.md` (3151/3151 bytes, confirmed by direct comparison, not just `diff`'s exit code).
- `mcp/server/transport_security.py:50` confirms `TransportSecuritySettings(enable_dns_rebinding_protection=False)` is the library default in the installed `mcp` version — the Self-test's claim about this SOP §7 item is accurate.
- Credential handling (`middleware.py`, `client.py`): headers read per-request into a `contextvars.ContextVar`, reset in `finally`, no module-level token storage — matches SOP §3.1/§3.3/§3.4 and AC11; `tests/test_middleware.py::test_concurrent_requests_do_not_leak_credentials_across_contextvars` genuinely forces interleaving (`asyncio.sleep(0.02)` in the mocked handler) rather than asserting on a race that can't actually occur.
- `env.py:_env_summary` is a hard allow-list (`id`/`key`/`target`/`type`), so AC8's "never return a decrypted value" guarantee holds structurally, not just by convention; `tests/test_tools.py::test_list_env_vars_never_returns_decrypted_value` mocks an upstream response that *includes* `value`/`decryptedValue` and asserts both are absent from the tool output — a real test of the guarantee, not a tautology.
- Error envelope (`errors.py`) and status-code mapping match the Data & API contract table; `handle_tool_errors` never lets an exception escape the tool boundary and genericizes unexpected-exception messages (no credential/body leakage).
- `destructiveHint`/`readOnlyHint`/`idempotentHint` annotations in `tools/*.py` match the Data & API contract table and AC12 (including the one documented, reasoned deviation: `vercel_cancel_deployment` carries both `destructiveHint` and `idempotentHint`, which follows AC12's own wording rather than the contract-table typo it points out in Self-test).
- Dockerfile: multi-stage, non-root `app` user, `curl` installed, `EXPOSE 8080`, `HEALTHCHECK` against `/health`, default `MCP_HTTP_PORT`/`MCP_HTTP_HOST` env vars — matches SOP §8 / §14 checklist.
- No real credentials in `.env.example`, `docker-compose.yml`, or `git log -p` (manual review; `gitleaks` is not installed in this environment, same gap the Self-test already noted).

### Findings

1. [must-fix] `docs/tickets/PRD-21334.md:276` — the repo contains non-English (Chinese) text: the sentence quotes the Chinese-language title of a section of the pipeline's internal `mcp-track.md` reference (its §3, "completion criteria"), embedded verbatim in this MCP repo's English-only ticket document. This violates the SOP's "repo content is entirely in English" rule (§0.4) and the §14 checklist item requiring no non-English text anywhere in the repo (code, docs included), and the review standard in `references/mcp-track.md` 4.3 ("no Chinese in the repo"). It also makes the Self-test Gates table's claim incorrect: running the exact command the table cites — `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .` — produces one line of output (this line), not the claimed "No output (clean)". Fix: rephrase the sentence to reference the SOP rule and the mcp-track.md section in English only, without quoting the original-language title, re-run the scan, and correct the Gates table entry to reflect what was actually found and fixed.

No other must-fix findings. The implementation matches the tech design's Change list and Data & API contract; all 6 automated test cases and the 1 live-verified manual case (TC16) in the ac.json ledger have real, checkable evidence; the 9 cases needing a real Vercel account are correctly marked `untested` rather than claimed as passing.

### Suggestions

None beyond the single must-fix above — no parameter stacking, no dead code (brand-new repo, nothing to clean up), reuse of `fastmcp`/`httpx`/`pydantic-settings` is appropriate and matches house convention.

### Fixes (round 1)

1. [must-fix #1] `docs/tickets/PRD-21334.md:276` — rephrased the sentence to reference mcp-track.md §3's completion-criteria section in English only, removing the quoted Chinese section title. Re-ran the exact cited scan, `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .`, from the repo root: no output (clean). Corrected the Self-test Gates table's "Chinese-character scan" row to record what round-1 review found and what was fixed, instead of the inaccurate original "No output (clean)" claim.
   - This was a documentation-text-only change — no source, test, or config file was touched (`git status --porcelain` after the edit shows only `docs/tickets/PRD-21334.md`). Gates unaffected by the fix were re-verified rather than assumed: `uv run pytest` on the fixed branch — 10 passed, 0 failed (same count as round-1 review); `uv sync --frozen` — "Checked 84 packages", no drift; README "MSPbots Connector" section re-diffed against `~/.claude/skills/vendor-mcp-development/reference/readme-connector-section.md` — still byte-identical (3151/3151 bytes). No automated or manual test case in `PRD-21334.ac.json` targets this line, so no case result changed.
   - Reviewed sha (round 1): 64150f6. Fix commit: see `docs(PRD-21334): fix review round 1 must-fix` on `dev/PRD-21334`.
   - Note on process: `legs/dev.md` S1 "评审返工" normally leaves the frozen `docs/tickets/PRD-21334.md` untouched and records only this Fixes note, because must-fix items are normally code changes. Here the must-fix defect is the prose of the frozen doc itself (a Chinese section title quoted verbatim), so the only way to actually satisfy "no non-English text in the repo" is to edit that sentence and its Gates-table row directly — leaving the frozen doc unedited would mean the stated violation is still in the repo. Edited only the two things the review named (the sentence at line 276, the Gates-table row); the rest of the frozen doc (Self-test narrative, Handoff, Decisions made by DEV01) is untouched.
