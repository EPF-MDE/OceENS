# Manual smoke test

The repository has no automated test suite (the first tests are #85, the wider CI #78).
CI checks the architecture rules and nothing else, so nothing upstream exercises
behaviour. This procedure runs entirely **outside the process**: start from a fresh clone,
start the application, and observe what it answers and with which exit code.

Run it before proposing a change that touches startup, configuration, dependencies or the
container.

## Conventions per system

Commands are given for **Windows (PowerShell)** then for **macOS / Linux (bash)**. Only
three things differ:

| | Windows (PowerShell) | macOS / Linux (bash) |
|---|---|---|
| Setting a variable for one command | `$env:VAR = "x"` then `Remove-Item Env:VAR` | `VAR=x command` |
| Reading the exit code | `$LASTEXITCODE` | `echo $?` |
| Copying / renaming a file | `Copy-Item`, `Rename-Item` | `cp`, `mv` |

Everything runs through `uv run`, which uses the environment of `uv.lock` without
activating it. That is deliberate: on Windows, `Activate.ps1` is blocked by default by
PowerShell's execution policy, and that is not what this test is about.

## Static checks

Identical on both systems (a single line, no continuation):

```
uv run python -m compileall -q src
git diff --check
uv run tach check
uv run python scripts/check_cycles.py
```

The last two are the package boundary checks, and `src/oceens/README.md` states the rule
they enforce. Both exit non-zero on a violation: `tach check` names the offending import,
`check_cycles.py` names the two packages that depend on each other.

## 1. Local start, without credentials

In a fresh clone of the branch, with no virtual environment yet: `uv sync` creates it,
installs the locked dependencies and the `oceens` package itself, and fetches Python 3.12
if the machine has no such interpreter.

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env
uv sync
uv run oceens
```

**macOS / Linux (bash)**

```bash
cp .env.example .env
uv sync
uv run oceens
```

`oceens` is the entry point installed with the package; it serves on port 8000. For
another port, or for `--reload`, call the server directly:
`uv run uvicorn oceens.main:app --port 8000`.

Expected, with no Entra credential and no LLM key:

| Route | Answer |
|---|---|
| `GET /` | 200 |
| `GET /dev/login` | 200 |
| `GET /nope` | 303 to `/` (404 middleware → `/`) |

The startup logs create the tables, insert the demo dataset, and contain neither an error
nor an exception trace.

On an empty database, signing in from `/dev/login` as each of the three single-role users
(`oceens.facilitator@epf.fr`, `oceens.program.manager@epf.fr`,
`oceens.campus.manager@epf.fr`) lands on that role's dashboard, with at least one survey
listed.

## 2. Start with Docker

This needs a **running Docker daemon** — Docker Desktop on Windows (with the WSL 2
backend) as on macOS, the native daemon on Linux. The command is the same everywhere:

```
docker compose up --build
```

Expected: the image builds, the container starts without restart-looping, and `/`,
`/dev/login` and `/nope` answer as in step 1.

Without a `.env`, `docker compose` fails with `env file .env not found` — by design, the
first command of a fork is copying `.env.example`.

To stop and clean up:

```
docker compose down
```

## 3. Exit codes on invalid configuration

An invalid startup configuration must exit with **code 1**, so that a supervisor or a CI
sees the failure.

The `.env` must be moved aside for the last two cases: `load_dotenv()` would read
`AUTH_MODE=dev` back from it and the application would start normally, with code 0.

**Windows (PowerShell)**

```powershell
# Invalid AUTH_MODE
$env:AUTH_MODE = "bogus"
uv run python -c "import oceens.main"; $LASTEXITCODE   # 1
Remove-Item Env:AUTH_MODE

# ENTRA_* missing, without .env
Rename-Item .env .env.bak
'AUTH_MODE','ENTRA_CLIENT_ID','ENTRA_CLIENT_SECRET','ENTRA_TENANT_ID' |
  ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
uv run python -c "import oceens.main"; $LASTEXITCODE   # 1

# SECRET_KEY missing in entra mode, without .env
$env:ENTRA_CLIENT_ID = "x"; $env:ENTRA_CLIENT_SECRET = "x"; $env:ENTRA_TENANT_ID = "x"
Remove-Item Env:SECRET_KEY -ErrorAction SilentlyContinue
uv run python -c "import oceens.main"; $LASTEXITCODE   # 1
'ENTRA_CLIENT_ID','ENTRA_CLIENT_SECRET','ENTRA_TENANT_ID' |
  ForEach-Object { Remove-Item "Env:$_" }
Rename-Item .env.bak .env
```

**macOS / Linux (bash)**

```bash
# Invalid AUTH_MODE
AUTH_MODE=bogus uv run python -c "import oceens.main"; echo $?   # 1

# ENTRA_* missing, without .env
mv .env .env.bak
env -u AUTH_MODE -u ENTRA_CLIENT_ID -u ENTRA_CLIENT_SECRET -u ENTRA_TENANT_ID \
  uv run python -c "import oceens.main"; echo $?   # 1

# SECRET_KEY missing in entra mode, without .env
env -u AUTH_MODE -u SECRET_KEY ENTRA_CLIENT_ID=x ENTRA_CLIENT_SECRET=x ENTRA_TENANT_ID=x \
  uv run python -c "import oceens.main"; echo $?   # 1
mv .env.bak .env
```

Expected: the log line `INVALID AUTH_MODE 'bogus'` for the first case,
`MISSING ENTRA INFO. Please check .env` for the second,
`MISSING SECRET_KEY. Required with AUTH_MODE=entra, please check .env` for the third. As a
control, `AUTH_MODE=dev` exits with 0, even without a `SECRET_KEY`.

## 4. Without an LLM key

`.env.example` ships an **empty** `LLM_API_KEY`: the application starts normally, only the
summaries are unavailable. With the summaries daemon (`uv run oceens-summaries`) running,
a summary request is marked as a configuration error (`http_status` 500, "variable
d'environnement absente ou vide") and no call is made to the provider.

## 5. With an LLM key

Each student gets their own key from <https://locallm.mde.epf.fr> by signing in with their
EPF account, then sets it in their `.env`:

```
LLM_API_KEY=<your key>
```

A quick check, without going through the interface. The command fits on one line and is
the same in both shells:

```
uv run python -c "from types import SimpleNamespace; from oceens.services import llm_client as c; p = SimpleNamespace(name='Ollama EPF', api_type='ollama', base_url='https://locallm.mde.epf.fr/ollama', api_key_env='LLM_API_KEY', default_model='gemma4:26b'); print(c.check_model(p, 'gemma4:26b')); print(c.ping_generation(p, 'gemma4:26b'))"
```

Expected: `True`, then `(True, None, None)`. `check_model` alone is not enough — the model
list still answers normally for an account with no credit, only the generation call
reveals it. With an empty key, the same command raises `LLMConfigError`: that is the
behaviour of step 4.

Then, end to end: request the summaries of a survey with
`uv run oceens-summaries` running. The rows move from `http_status` 0 to 200 and the
summary is rendered as HTML. Never commit the key: `.env` is ignored by Git.

## Next

Test the routes your change touches, on a throwaway SQLite database (never a copy of
production), with the relevant roles and survey statuses.
