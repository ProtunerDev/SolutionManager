# Pre-Mortem: SolutionManager
**Date:** 2026-05-21  
**Analyst:** Claude Code  
**Branch:** main  

> A pre-mortem assumes the project has already failed and works backward to find why.  
> Each section is written from a different point of view.

---

## 1. The Developer's View — Code Quality & Maintainability

### 1.1 Session as a state machine (will break)
The multi-step workflow (ORI1 → MOD1 → compare → save solution) is built entirely on Flask `session` keys:
- `session['uploaded_files']`
- `session['differences_file']`
- `session['temp_solution_id']`
- `session['files']`
- `session['compatibility_check']`

**What breaks:** A second browser tab, a session expiry, or a page refresh at the wrong step leaves orphaned keys. `routes.py:443` accesses `session['differences_file']` without any existence check — guaranteed `KeyError` in the wild.

**Fix:** Add guards on every session key access. Store multi-step state in the DB (tied to a `workflow_id`) instead of the session.

---

### 1.2 `PostgreSQLFileStorage` is a silent no-op
`app/utils/file_storage.py` — both `store_file()` and `get_file()` return `False`/`None` with a deprecation `logger.warning()`. If `STORAGE_TYPE=local` is set (new dev machine, misconfigured deploy, missing env var), the app boots cleanly, uploads return HTTP 200, and **no files are stored or retrievable**. The failure is invisible to the user and the operator.

**Fix:** Raise `NotImplementedError` or `RuntimeError` instead of returning `False`. Fail loudly.

---

### 1.3 Dead code in `store_differences`
`s3_storage.py` has unreachable code after a `return True` inside `store_differences()`. A second `except` block will never execute, silently swallowing errors that can never be caught.

**Fix:** Remove the dead block.

---

### 1.4 `upload_temp_file` logic is fragile
`upload_temp_file()` calls `store_file()` (which returns `True`/`False`), then checks `if s3_key:` — but `s3_key` is `True`, not an actual key string. It re-computes the key path by calling `_get_s3_key()` again. Works today, breaks silently if the key generation logic ever changes.

**Fix:** Have `store_file()` return the S3 key string on success, `None` on failure.

---

### 1.5 1,333-line `routes.py` — single point of failure
All business logic lives in one file. One syntax error fails every route. One import failure kills the entire app. Impossible to unit test individual flows.

**Fix:** Extract workflows into service classes: `CompareService`, `SolutionService`, `DownloadService`.

---

## 2. The Security Engineer's View

### 2.1 Hardcoded password in production code (CRITICAL)
**`app/database/db_manager.py:60`:**
```python
"password": current_app.config.get('DB_PASSWORD', 'Jmadriz63')
```
A real credential is hardcoded as a fallback default. If `DB_PASSWORD` is absent from the environment (deploy misconfiguration, missing `.env.production`), the app silently connects using this hardcoded value. This credential is now in git history permanently.

**Fix:** Remove the fallback. If `DB_PASSWORD` is missing, raise a startup error. Rotate the credential immediately.

---

### 2.2 No authorization — any user deletes any solution
All routes use `@login_required` but there is **zero ownership checking**. Any authenticated user can:
- `DELETE /delete_solution/<any_id>` — deletes another user's solution
- `GET /solution_detail/<any_id>` — reads another user's data
- `POST /apply_solution/<any_id>` — applies another user's solution to their own car

There is no `solution.owner_id` field and no check at any route.

**Fix:** Add `created_by` (Supabase user UUID) to the `solutions` table. Check ownership on every write route.

---

### 2.3 AWS credentials in `.env` committed to the repo
The `.env` file (tracked in git with status `M`) contains:
```
AWS_ACCESS_KEY_ID=AKIAWWDVX7DFG5RANDHA
AWS_SECRET_ACCESS_KEY=5W9XYhj...
```
These are live credentials. Any collaborator, CI log leak, or accidental `git push` exposes them.

**Fix:** Rotate the keys now. Add `.env` to `.gitignore` if not already excluded. Use IAM roles or a secrets manager for production.

---

### 2.4 `debug_config` route exposes internals
`routes.py:1275` — `/debug_config` is behind `@login_required` but any authenticated user can call it and see the full app configuration including DB params, S3 bucket name, and Supabase keys rendered to the browser.

**Fix:** Remove this route entirely, or restrict to an admin role and only enable in non-production environments.

---

### 2.5 No rate limiting on auth endpoints
`app/auth/routes.py` — login, password reset, and user invitation endpoints have no rate limiting beyond what Supabase imposes. An attacker can enumerate valid email addresses via timing differences and brute-force passwords at will.

**Fix:** Add Flask-Limiter to auth routes (`/auth/login`, `/auth/forgot-password`).

---

## 3. The Data Engineer's View — Integrity & Consistency

### 3.1 S3 ↔ PostgreSQL split-brain
`s3_storage.py` writes to S3 **first**, then writes metadata to PostgreSQL as a separate, independent step with no transaction wrapper. If the DB write fails after the S3 upload succeeds:
- The file exists in S3 and is billable
- The file is invisible to the app (no metadata row)
- No error is surfaced, no rollback happens
- The orphaned S3 object stays forever

**Fix:** Write to the DB first (as a "pending" record), then upload to S3, then mark the DB record "complete". Use a cleanup job for stuck "pending" records.

---

### 3.2 Phantom solution auto-creation
Both `_save_file_metadata()` and `_save_differences_metadata()` contain:
```python
INSERT INTO solutions (id, vehicle_info_id, description, status)
VALUES (%s, 1, 'Auto-created solution for file upload', 'active')
ON CONFLICT (id) DO NOTHING
```
If a solution doesn't exist, the code silently creates a fake record attached to `vehicle_info_id=1`. Corrupt phantom data accumulates in the DB with no audit trail and no relation to real vehicle data.

**Fix:** Remove this fallback entirely. If the solution doesn't exist, raise an error and abort the upload.

---

### 3.3 No connection pooling — connection exhaustion under load
`s3_storage.py` opens a raw `psycopg2` connection on **every single DB call** (in `_save_file_metadata`, `_save_differences_metadata`, `get_file_info`, `delete_solution_files`). No pooling, no reuse, no maximum. Under moderate load, PostgreSQL hits its connection limit and all requests fail.

**Fix:** Use `psycopg2.pool.ThreadedConnectionPool` or switch to SQLAlchemy with a connection pool. Centralize all DB access through `DatabaseManager`.

---

### 3.4 Temp files accumulate in S3 forever
`cleanup_temp_files()` (`routes.py:32`) is only called when a new upload begins. If a user abandons the workflow mid-step, the temp files under `solutions/{uuid}/` in S3 are never deleted. 

At scale: 1,000 abandoned sessions × ~10MB ECU files = 10GB of unclaimed billable storage per month.

**Fix:** Add an S3 lifecycle rule to expire objects under `solutions/temp-*/` after 24 hours. Also call `cleanup_temp_files()` on session cleanup.

---

## 4. The Operations / DevOps View

### 4.1 `S3FileStorage.__init__` makes a blocking network call on every instantiation
Every request that touches file storage calls `_test_connection()` → `s3_client.head_bucket()` with no timeout set. If S3 is slow or rate-limiting:
- Every request hangs
- App appears completely unresponsive
- No circuit breaker or fallback

**Fix:** Move the connection test to app startup (once), not per-request instantiation. Set an explicit `connect_timeout` on the boto3 client.

---

### 4.2 `MAX_CONTENT_LENGTH=16MB` with no user-facing error
Config sets `MAX_CONTENT_LENGTH=16777216` (16MB). ECU binary files can exceed this. When they do, Flask returns a raw HTTP 413 with no friendly error page. Users see a generic browser error with no guidance.

**Fix:** Add an `@app.errorhandler(413)` that returns a clear message. Consider raising the limit for authenticated users if ECU files can legitimately exceed 16MB.

---

### 4.3 Procfile vs nixpacks mismatch
- `Procfile`: `waitress-serve --port=$PORT run:app`
- `nixpacks.toml`: `cmd = "gunicorn run:app"`

Two different WSGI servers depending on deploy target. Different behavior under load, different timeout defaults, different worker models. Neither is wrong but the divergence creates a "works on Railway, fails on Heroku" class of bugs.

**Fix:** Standardize on one WSGI server across all deploy targets. Document the choice in `CLAUDE.md`.

---

### 4.4 No health check endpoint
There is no `/health` or `/ping` route. Load balancers and container orchestrators (Railway, Render, Heroku) cannot distinguish between "app is starting" and "app is broken". A crashed worker restarts silently with no alert.

**Fix:** Add `@bp.route('/health')` returning `{"status": "ok"}` with a DB connectivity check.

---

## 5. The User Experience View

### 5.1 Workflow loss with no warning
The multi-step upload flow has no timeout warning, no progress save, and no way to resume. A user who spends 10 minutes filling in vehicle data, uploads two binary files, and then loses their session or refreshes the page starts from zero.

**Fix:** Save workflow progress to the DB at each step. Allow resuming from the last completed step.

---

### 5.2 No feedback on file processing time
Binary comparison (`BinaryHandler`) and S3 uploads can take several seconds for large files. There is no loading indicator or progress feedback. Users see a blank page and assume it's broken.

**Fix:** Add a loading spinner or progress indicator for the compare and upload steps.

---

### 5.3 Silent failures look like success
Several error paths return a redirect to `home` with a generic flash message (or no message). A failed S3 upload, a failed DB write, or a missing file all produce the same user experience as success. Users cannot tell if their solution was actually saved.

**Fix:** Every error path that aborts a workflow must flash a specific, actionable message. Never redirect to `home` silently on error.

---

## 6. Priority Fix Order

| # | Risk | Effort | Priority |
|---|------|--------|----------|
| 1 | Hardcoded DB password in code | 5 min | **CRITICAL** |
| 2 | Rotate exposed AWS keys | 10 min | **CRITICAL** |
| 3 | `local` storage silent no-op | 5 min | High |
| 4 | No ownership check on delete/edit | 2h | High |
| 5 | S3 + DB write not atomic | 4h | High |
| 6 | Phantom solution auto-creation | 30 min | High |
| 7 | Session flow guards (KeyError risk) | 2h | High |
| 8 | S3 init blocking network call | 1h | Medium |
| 9 | No connection pooling | 2h | Medium |
| 10 | S3 temp file accumulation | 1h | Medium |
| 11 | No health check endpoint | 30 min | Medium |
| 12 | Remove `debug_config` route | 5 min | Medium |
| 13 | Rate limiting on auth routes | 1h | Medium |
| 14 | Dead code in `store_differences` | 5 min | Low |
| 15 | Procfile vs nixpacks unification | 30 min | Low |

---

*Generated by Claude Code — 2026-05-21*
