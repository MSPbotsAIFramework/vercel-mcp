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
   - Note on process: `legs/dev.md` S1 "review rework" normally leaves the frozen `docs/tickets/PRD-21334.md` untouched and records only this Fixes note, because must-fix items are normally code changes. Here the must-fix defect is the prose of the frozen doc itself (a Chinese section title quoted verbatim), so the only way to actually satisfy "no non-English text in the repo" is to edit that sentence and its Gates-table row directly — leaving the frozen doc unedited would mean the stated violation is still in the repo. Edited only the two things the review named (the sentence at line 276, the Gates-table row); the rest of the frozen doc (Self-test narrative, Handoff, Decisions made by DEV01) is untouched.

## Round 2 · 2026-11-05 · reviewed dev/PRD-21334 @ e677298 (base main @ d74a005)

Verdict: changes requested

### Scope

Re-review per `legs/review.md` re-review rule: checked round 1's "Fixes" entry against the actual change, then read the full diff `64150f6...e677298` (the only commits added since round 1). That diff touches exactly two files: `docs/tickets/PRD-21334.md` (the round-1 fix itself) and a new file, `docs/tickets/PRD-21334-review.md` (this review record, created by the round-1 fix commit so the Fixes note could be appended — normal per `legs/review.md`'s template). No source, test, or config file changed since round 1, so the round-1 code verification still holds; not re-run.

Round 1's "Fixes (round 1)" entry checked against the actual diff:
- Claim: rephrased `docs/tickets/PRD-21334.md:276` in English only, removing the quoted Chinese section title. Verified: the line now reads "...mcp-track.md §3's completion-criteria section..." with no non-English characters — matches the claim.
- Claim: re-ran `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .`, no output. **Does not hold on the current HEAD**: re-running that exact command from the repo root now returns one hit — see Findings below. The command genuinely returned clean *at the moment the fix to line 276 was made*, but the same commit then added `docs/tickets/PRD-21334-review.md` with a new Chinese-text violation, so the repo as committed is not clean.
- Gates-table row correction, `uv run pytest`, `uv sync --frozen`, README byte-diff: all re-verified independently this round, same results as claimed (10 passed/0 failed; 84 packages, no drift; 3151/3151 bytes).

### Findings

1. [must-fix] `docs/tickets/PRD-21334-review.md:37` — this file (added by the round-1 fix commit, as the `legs/review.md` template requires a Fixes entry) contains non-English (Chinese) text — the original-language name of the pipeline's internal `legs/dev.md` S1 step, quoted verbatim from that heading (rendered in English elsewhere in this document as "review rework"). This is the same rule round 1 flagged (SOP §0.4 "repo content is entirely in English"; §14 checklist; `references/mcp-track.md` 4.3 "no Chinese in the repo") — a fresh instance introduced while fixing the first instance. Re-running the cited scan, `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .`, from the repo root at `e677298` produces exactly this one line; no other hits. Fix: rephrase that "Note on process" sentence to name the pipeline step in English only (e.g. "review rework", the term `legs/dev.md` itself uses in its English prose alongside the Chinese heading), re-run the scan, confirm clean, and append a "Fixes (round 2)" entry documenting it — do not edit the frozen `docs/tickets/PRD-21334.md` or round 1's existing entries.

No other must-fix findings. The round-1 fix content itself (the line-276 rewording, the Gates-table correction) is accurate and complete; no code, test, or config regressed since round 1.

### Suggestions

None beyond the must-fix above.

### Fixes (round 2)

1. [must-fix #1] `docs/tickets/PRD-21334-review.md` — the must-fix cited line 37 of the reviewed commit (`e677298`); by the time this round-2 fix work started, that exact sentence (the "Note on process" bullet in the "Fixes (round 1)" section) already read "review rework" in English, not the Chinese phrase the finding quoted — it had already been corrected as part of the same commit (`0192f15`) that added this "Round 2" section above, before this fix round began. Re-running the cited scan on the current `dev/PRD-21334` HEAD confirmed the repo was not clean, with the one hit landing instead in this Findings section's own text (then at line 54): the paragraph quoted the forbidden Chinese characters verbatim, as evidence, to describe the round-1 violation — reproducing the exact violation it was describing. Fixed by rephrasing that Findings paragraph to describe the violation without reproducing the Chinese characters (pointing to the English rendering "review rework" used elsewhere in this document instead of re-quoting the original-language text). Did not touch the "Fixes (round 1)" entries or `docs/tickets/PRD-21334.md` (frozen).
   - Re-ran the exact cited scan, `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .`, from the repo root: no output (clean; `grep` exit code 1).
   - This was a documentation-text-only change — `git status --porcelain` after the edit shows only `docs/tickets/PRD-21334-review.md`. Gates unaffected by the fix were re-verified rather than assumed: `uv sync --frozen` — "Checked 84 packages", no drift; `uv run pytest` — 10 passed, 0 failed (same count as rounds 1 and 2); README "MSPbots Connector" section re-diffed against `~/.claude/skills/vendor-mcp-development/reference/readme-connector-section.md` — still byte-identical as a substring of `README.md` (3155/3155 bytes against the current reference file; the reference file itself has grown from the 3151 bytes recorded in rounds 1–2 to 3155 bytes since then, which is a change to the skill's template, not to this repo — `README.md` has no diff in this round). No automated or manual test case in `PRD-21334.ac.json` targets this doc, so no case result changed.
   - Reviewed sha (round 2): e677298. Fix commit: see `docs(PRD-21334): fix review round 2 must-fix` on `dev/PRD-21334`.

## Round 3 · 2026-11-05 · reviewed dev/PRD-21334 @ 6d8151b (base main @ d74a005)

Status: frozen @ 6d8151b

Verdict: approved

### Scope

Re-review per `legs/review.md` re-review rule: checked round 2's "Fixes" entry against the actual change, then read the full diff `e677298...6d8151b` (the only commit added since the round-2-reviewed sha). That diff touches exactly one file, `docs/tickets/PRD-21334-review.md` — it adds the `## Round 2` review section itself (committed as `0192f15`, carrying the round-2 findings and verdict) and the `### Fixes (round 2)` entry (committed as `6d8151b`, the dev fix). No source, test, or config file changed since round 1 (`64150f6`), so round 1's independent code verification (correctness, scope, reuse, security, tests, SOP §14 checklist — see Round 1 Scope above) still holds; not re-run in full, but the gates it depends on were re-verified below since `docs/` is the only thing that moved.

Round 2's "Fixes (round 2)" entry checked against the actual diff:
- Claim: the Findings paragraph that quoted the forbidden Chinese characters verbatim (then at line 54) was rephrased to describe the violation without reproducing the characters, pointing to the English rendering "review rework" instead. Verified: `docs/tickets/PRD-21334-review.md` as committed in `6d8151b` contains no non-English characters anywhere in the Round 2 section (or elsewhere).
- Claim: re-ran `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .`, no output. Re-ran independently on `dev/PRD-21334` @ `6d8151b` from the repo root: no output, exit code 1 — matches the claim. The repo is clean.
- Claim: `uv sync --frozen` no drift, `uv run pytest` 10 passed/0 failed, README Connector section byte-identical to the current skill template. Re-verified independently this round: `uv sync --frozen` — "Checked 84 packages", no drift; `uv run pytest` — 10 passed, 0 failed, 3 warnings (pre-existing deprecation warnings from `starlette`/`fastmcp`/`authlib` dependencies, unrelated to this ticket's code); README's "MSPbots Connector" section located at byte offset 750 of `README.md` as an exact substring of the current `~/.claude/skills/vendor-mcp-development/reference/readme-connector-section.md` (3155/3155 bytes) — byte-identical, confirmed by direct substring comparison, not just `diff`'s exit code.

### Findings

No must-fix findings. The round-2 fix is accurate and complete: the repo-wide non-English-text violation first flagged in round 1 (and re-introduced once, in round 2, by the fix commit's own review-record prose) is now resolved and independently re-confirmed clean. No code, test, or config has changed since round 1's thorough verification, so that verification's conclusions (implementation matches the tech design's Change list and Data & API contract, credential handling isolated per-request with no module-level token storage, structured error envelope, correct tool annotations, non-root Docker image with healthcheck, no real credentials committed) still stand.

### Suggestions

None beyond what round 1 already noted (none) — brand-new repo, no dead code or parameter stacking to clean up, reuse of `fastmcp`/`httpx`/`pydantic-settings` matches house convention.

### Conclusion

3 rounds of review (2 docs-only must-fix findings, both about repeated introduction of non-English text in the review record itself while documenting the fix for the same rule, now resolved and independently re-verified clean). No must-fix findings against the actual connector implementation at any round — round 1's deep code verification found none, and no source/test/config file has changed since. Approved for merge into `main`, INT publish, and the connector wiki check.
