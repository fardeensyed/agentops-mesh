# Troubleshooting Log — AgentOps Mesh

Real issues hit during development, kept for future reference.

## 1. PowerShell vs CMD line continuation
**Error:** `^` caused "term not recognized" in PowerShell
**Cause:** `^` is CMD's line-continuation char. PowerShell uses backtick `` ` ``
**Fix:** Use `` ` `` in PowerShell, or write commands on one line

## 2. Git push failed — "src refspec main does not match"
**Cause:** Ran `git commit` from inside `sdk/agentops/` — created a 
nested git repo. Also local branch was `master` not `main`.
**Fix:**

**Lesson:** Always run git commands from the project root.

## 3. Context pollution between tests
**Error:** Test 10 showed stale span ID instead of None
**Cause:** ContextVar state from Test 9 leaked into Test 10 — no 
cleanup between tests
**Fix:** Added `clear_context()` at start of the test
**Lesson:** Shared global state needs explicit teardown between tests

## 4. ClickHouse "Authentication failed" on /play
**Cause:** Default ClickHouse user has no password, but login form 
expected one
**Fix:** Set `-e CLICKHOUSE_PASSWORD=agentops123` when starting the 
Docker container, or leave password blank if using true default

## 5. FastAPI WinError 10013 — socket access forbidden
**Cause:** Port 8000 blocked by Windows permissions
**Fix:** Used port 8001 instead — no admin rights needed to change ports

## 6. db.py silently using SQLite instead of PostgreSQL
**Cause:** File content got reset/regenerated to a different fallback 
version without noticing
**Fix:** Always verify file contents with `Get-Content` after any edit 
if behavior seems wrong
**Lesson:** Silent fallbacks (like `os.getenv(... , "sqlite:///...")`) 
can mask real connection issues — verify actual DB being used

## 7. Postgres "password authentication failed" — port conflict
**Cause:** A native Windows PostgreSQL service (postgresql-x64-18) was 
already bound to port 5432, intercepting connections meant for Docker
**Fix:** Ran Docker's Postgres container on port 5433 instead:

Updated `DATABASE_URL` to use port `5433`.
**Lesson:** `netstat -ano | findstr :PORT` reveals ALL listeners on 
a port — critical for diagnosing "wrong service answered" bugs.
**Reminder:** This project's Postgres always runs on port 5433, not 
the default 5432.

