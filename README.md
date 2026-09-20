# OcéEns II

Teaching evaluation platform built for the EPF engineering school.

## Overview

**OcéEns II** lets program managers, facilitators, campus management and administrators
create and run evaluation surveys for EPF's programs, and lets students answer them.
Answers can be exported, visualised, and summarised through an LLM. The interface follows
EPF's official visual identity.

The application itself is in French: its pages, its seeded demo content and the survey
questions are written in French. The documentation is in English — see `CONTEXT.md` for
where that boundary sits.

### Technical stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (Python 3.12) |
| **Authentication** | Microsoft Entra ID (Azure AD) via OAuth2.0 / MSAL, Microsoft Graph — or a dev sign-in, see below |
| **Database** | SQLite (via SQLAlchemy + SQLModel) |
| **Templating** | Jinja2 (server-side rendering) |
| **Frontend** | HTML / CSS / JavaScript, no framework |
| **Server** | Uvicorn |
| **Logging** | Standard Python `logging`, through the Uvicorn handlers |
| **Exports** | Pandas (CSV) |
| **Verbatim summaries** | Separate daemon calling an LLM (`requests-cache`, `markdown-it-py`) |

---

## Roles

- `student`: answers the surveys they are invited to.
- `program_manager:<code>`: manages the surveys of their program(s).
- `facilitator:<code>`: runs the surveys of their program(s).
- `campus_manager:<campus>`: campus-wide scope.
- `admin`: general administration.

A user can hold several roles, each with its own scope (program codes or campuses
separated by `;`). The scope is stored inside the role string itself, after the colon.

---

## Running it from a fresh clone

The application starts with no Azure application and no LLM key: `.env.example` ships
`AUTH_MODE=dev`, which replaces Microsoft Entra ID with a local sign-in page.

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — it installs Python 3.12 itself if the machine
  has no such interpreter
- A `.env` file, copied from `.env.example` (see [Configuration](#configuration))

### With Docker Compose (recommended)

```bash
cp .env.example .env
docker compose up --build
```

The application listens on <http://localhost:8000>. Without a `.env`, `docker compose`
fails with `env file .env not found`: copying `.env.example` is the first command of a
fresh clone.

The SQLite database is persisted in a directory of the host, mounted into the container:
`./database/` by default, or the directory named by `LOCAL_DATABASE_DIR`.

```env
LOCAL_DATABASE_DIR=/path/to/database
```

To stop and clean up:

```bash
docker compose down
```

> The image runs the `oceens` entry point without `--reload`, and the source code is
> copied into the image rather than mounted: a code change needs a
> `docker compose up --build`. For a reload loop, run the application directly (below).
>
> The `.env` file is never copied into the image — Compose passes it through `env_file`.

### Without Docker

1. **Clone the project**

   ```bash
   git clone <repository-url>
   cd OceENS
   ```

2. **Copy the configuration**

   ```bash
   cp .env.example .env            # Windows (PowerShell): Copy-Item .env.example .env
   ```

3. **Install the dependencies** with [uv](https://docs.astral.sh/uv/), the same command on
   every system:

   ```bash
   uv sync
   ```

   `uv sync` creates `.venv`, installs the versions pinned in `uv.lock` and the `oceens`
   package itself, and fetches the Python of `.python-version` (3.12) if the machine has
   no such interpreter. Nothing needs to be activated: `uv run` uses that environment.

4. **Start the application**:

   ```bash
   uv run oceens
   ```

   Or with reload while developing:

   ```bash
   uv run uvicorn oceens.main:app --reload
   ```

   > The working directory no longer matters: the templates, the static files and the seed
   > CSV files are installed with the package and found next to it. The exception is the
   > SQLite database, which defaults to `database/` at the repository root — set
   > `LOCAL_DATABASE_DIR` to fix it somewhere else.

5. **Open** <http://localhost:8000>.

6. **(Optional) Start the LLM summaries daemon**:

   ```bash
   uv run oceens-summaries
   ```

   This process loops, writes to the database and calls an external LLM service: start it
   only when summaries are needed. Setting `RUN_SUMMARIES_DAEMON=1` in the `.env` makes
   the application start it as a child process on startup and stop it on shutdown.

   In production without Docker, `launch.sh` starts the application and the daemon in two
   separate `screen` sessions.

### What the first start does

On every start, the application creates the missing tables, adds the columns missing from
already-deployed tables, and seeds what must always be present: the programs (from
`src/oceens/seed_data/Program_list.csv`), the default LLM provider, the exchange rate and
the model price list. All of this is idempotent.

**On an empty database only**, it also inserts a demo dataset: users, surveys, modules,
respondents and answers, so that every screen has something to show. Four surveys are
seeded — three open, one closed with results (`MDID5`, Troyes campus).

The dataset includes three **single-role users**, each holding exactly one scoped role.
Like the rest of the demo dataset they are seeded on an empty database only: a scoped role
is a real permission over a real program, not something to hand out to a database already
in service.

| Mail | Role |
|------|------|
| `oceens.facilitator@epf.fr` | `facilitator:MDAI5` |
| `oceens.program.manager@epf.fr` | `program_manager:MDAI5` |
| `oceens.campus.manager@epf.fr` | `campus_manager:Troyes` |

Each scope matches a seeded survey, so signing in as any of them shows a populated
dashboard. The other demo users `antoine.gademer@epf.fr` (user 1) and
`yassine.gharbi@epfedu.fr` (user 6) combine `admin` with a business role; the seeded
students hold no role at all.

> **If you deployed a build between #84 and #38**, that version seeded the three addresses
> above into a populated database too. Anyone signing in with one of them inherits the
> scope. Check the `users` and `roles` tables and delete those rows if they are there.

---

## Dev sign-in

To work on a fork without an Azure application, the **dev sign-in** lets anyone sign in as
any user, without proof of identity. It must **never** be used in production.

It is turned on by `AUTH_MODE=dev`, and shaped by `DEV_LOGIN_KEY`, `SECRET_KEY` and
`ALLOWED_DOMAINS` — all four described in [Configuration](#configuration). In `dev` mode,
the `ENTRA_*` variables are not needed.

In `dev` mode the session cookie is no longer restricted to HTTPS (`http://localhost`
works), `/login` redirects to `/dev/login`, `/auth/callback` does not exist and `/logout`
clears the session then returns to `/`. A warning is logged at startup. A red,
non-dismissable banner is shown at the top of every page that includes the shared header:
it recalls the signed-in address, offers *Changer d'utilisateur* (`/dev/login`) and says
*accès ouvert à tous* when `DEV_LOGIN_KEY` is unset.

`POST /dev/login` expects a form with `email`, `name` (optional) and `key` (when
`DEV_LOGIN_KEY` is set). The user is fetched or created exactly as on return from Entra:
an unknown mail becomes a new student. Without `name`, the displayed name is derived from
the mail (`bob.leponge@epfedu.fr` → "Bob Leponge"). A new sign-in replaces the session —
that is how you switch user.

In a browser, `GET /dev/login` lists the users of the database, grouped by role name
without its scope (a user with no role appears under `student`, a user with several roles
under each of them). Clicking one signs in as them; a free-text field accepts any other
address, with an optional name. When `DEV_LOGIN_KEY` is set, a single key field appears
and serves every sign-in on the page; the key is never stored in the session.

```bash
AUTH_MODE=dev DEV_LOGIN_KEY=my-key uv run oceens

# Sign in as the seeded admin; -c saves the session cookie
curl -i -c cookies.txt \
  -d email=antoine.gademer@epf.fr -d key=my-key \
  http://localhost:8000/dev/login

# Reuse the cookie (-b) for the following requests
curl -b cookies.txt -c cookies.txt -L http://localhost:8000/
```

> [!WARNING]
> `dev` mode does not require `SECRET_KEY`. Without it the key is random and unknown; but
> if a *known* `SECRET_KEY` is set (shared, copied from an example…), anyone who knows it
> can forge a session cookie and bypass `DEV_LOGIN_KEY`. `dev` mode accepts that, because
> it is only ever meant to run locally.

---

## Authentication with Microsoft Entra ID (OAuth 2.0)

With `AUTH_MODE` unset or `entra`, sign-in goes through **Microsoft Entra ID** using MSAL:

```
1. The user clicks "Se connecter"
   → FastAPI generates a random state (UUID, CSRF protection)
   → Redirect to the Microsoft sign-in page

2. The user authenticates with Microsoft
   → Microsoft redirects to /auth/callback with a code + state

3. The server exchanges the code for an access token
   → Fetches the user's profile through Microsoft Graph
   → Reads the roles and their scopes from the database
   → Creates the session {name, email, roles}
   → Redirects to the matching dashboard

4. On sign-out (/logout)
   → Session and cookies are cleared
   → Sign-out on the Microsoft side
   → Back to the home page
```

Authentication alone authorises no business action: every route then checks the role and
its scope (program or campus) through `require_roles()` and the associated helpers.

---

## Configuration

Copy `.env.example` to `.env` and fill it in. That file is the reference: it lists every
variable the code reads, with its default.

| Variable | Required | Meaning |
|----------|----------|---------|
| `AUTH_MODE` | no (default `entra`) | `entra` or `dev`, case- and space-insensitive. Any other value: the application logs a critical error and exits with code 1. |
| `DEV_LOGIN_KEY` | no | Key required by the dev sign-in (form field `key`), otherwise `401`. Empty: sign-in is open. Ignored, with a warning, in `entra`. |
| `ALLOWED_DOMAINS` | no | Comma-separated mail domains allowed to sign in (`403` for any other), in `dev` as in `entra`. Defaults to `epf.fr,epfedu.fr` in `dev`, to empty in `entra`. |
| `SECRET_KEY` | in `entra` | Signs the session cookies. In `dev`, optional: when missing, a random key is drawn at each start, with a warning, and sessions are lost on restart. |
| `ENTRA_CLIENT_ID` | in `entra` | Azure application ID. |
| `ENTRA_CLIENT_SECRET` | in `entra` | Azure application secret. |
| `ENTRA_TENANT_ID` | in `entra` | Azure tenant (organisation) ID. |
| `REDIRECT_URI` | no (default `https://localhost/auth/callback`) | Callback URL registered in Azure. |
| `LOCAL_DATABASE_DIR` | no (default `database/`) | Directory holding `db_oceens.db`. A relative path is resolved from the repository root. With Docker Compose, the host directory mounted into the container. |
| `LLM_API_KEY` | no | Key of the default LLM provider. Empty: the application starts, but requested summaries are marked as configuration errors. |
| `RUN_SUMMARIES_DAEMON` | no | `1`/`true`/`yes`/`on` starts the summaries daemon alongside Uvicorn. |

`SECRET_KEY` signs the session cookies: anyone who knows it can forge an admin session. It
is **required unless `AUTH_MODE=dev`**: when missing or empty, the application logs a
critical error and exits at startup (exit code 1). Generate one with
`python -c "import secrets; print(secrets.token_urlsafe(32))"`.

> [!CAUTION]
> Never commit the `.env` file. It is already listed in `.gitignore`, as are the `*.db`
> files (`database/db_oceens.db`, `cache_llm.db`).

---

## Pages and routes

Pages and forms are server-rendered; the `/api` routes are called by the templates, by
`fetch()` or by a form post.

### Pages

| Route | Description |
|-------|-------------|
| `GET /` | Home page, authentication hub. |
| `GET /login`, `GET /auth/callback`, `GET /logout` | Microsoft Entra ID flow. In `dev` mode, `/login` redirects to `/dev/login` and `/auth/callback` does not exist. |
| `GET`/`POST /dev/login` | Dev sign-in: user list in `GET`, sign-in in `POST` (only with `AUTH_MODE=dev`). |
| `GET /dashboard/student` | Student dashboard. |
| `GET /dashboard/program-manager` | Program manager dashboard. |
| `GET /dashboard/facilitator` | Facilitator dashboard. |
| `GET /dashboard/campus-manager` | Campus management dashboard. |
| `GET /dashboard/teachers/analytics` | Satisfaction score per teacher, filterable by year / semester / program / teacher. Open to `campus_manager` and `program_manager`, each within their own scope. |
| `GET /dashboard/admin` | Administrator dashboard. |
| `GET /dashboard/survey-create` | Survey creation / setup. |

### Surveys

| Route | Description |
|-------|-------------|
| `POST /api/surveys` | Creates a survey. |
| `GET /api/surveys/{survey_id}` | The questionnaire itself. |
| `POST /api/surveys/{survey_id}` | Submits the answers. |
| `POST /api/surveys/{survey_id}/status` | Changes the status of a survey. |
| `DELETE`/`POST /api/surveys/{survey_id}/delete` | Deletes a survey. |
| `GET`/`POST`/`DELETE /api/surveys/{survey_id}/students` | Students invited to a survey. |
| `GET /api/surveys/{survey_id}/export` | CSV export of the answers. |
| `GET /api/surveys/{survey_id}/visualisation` | Visualisation of the answers. Accepts `?teacher=<name>` to open already filtered on a teacher. |
| `POST /api/surveys/{survey_id}/generate-summaries` | Requests the LLM summaries. |
| `POST /api/surveys/{survey_id}/destroy-summaries` | Deletes the generated summaries. |
| `GET /api/surveys/{survey_id}/cost` | Summary cost of that survey. |

### Administration

| Route | Description |
|-------|-------------|
| `POST /api/users` | Creates a user from a mail address (admin). |
| `PUT /api/users/{user_id}/role` | Changes the role of a user. |
| `GET /backend/prompts`, `/backend/prompts/new`, `/backend/prompts/{id}/edit` | LLM prompt screens (admin only). |
| `POST /api/prompts`, `PUT`/`DELETE /api/prompts/{id}` | Prompt CRUD. Editing and deleting are refused while the prompt is referenced in `summaries`. |
| `GET /backend/templates` | Survey templates. |
| `POST /api/templates`, `PUT`/`DELETE /api/templates/{id}`, `POST /api/templates/{id}/toggle-active`, `POST /api/templates/{id}/duplicate` | Survey template administration. |
| `POST`/`PUT`/`DELETE /api/sections`, `/api/sections/{id}` | Section administration. |
| `POST`/`PUT`/`DELETE /api/questions`, `/api/questions/{id}` | Question administration. |
| `GET /backend/providers` and `/new`, `/{id}/edit`, `/{id}/test`; `POST /backend/providers/create`, `/{id}/update`, `/{id}/delete` | LLM providers (admin). |
| `GET /backend/llm/prices`; `POST /backend/llm/settings/rate`, `/backend/llm/prices/save`, `/backend/llm/prices/{id}/delete` | Price list and exchange rate. |
| `GET /backend/llm/costs` | Global summary cost. |

Any `404` other than on `/` is redirected to `/` by an HTTP middleware, which then routes
to the right dashboard.

---

## LLM providers (verbatim summaries)

Verbatim summaries are generated by an LLM. The provider is **configurable from the
interface** (`/backend/providers`, admin only), without touching the code. The default
provider is **Ollama EPF** (`https://locallm.mde.epf.fr/ollama`), created automatically on
the first start.

### Supported API types

| `api_type` | Covers |
|------------|--------|
| `ollama`    | Ollama servers (local, EPF, third-party) |
| `openai`    | OpenAI **and any OpenAI-compatible endpoint**: vLLM, Groq, Mistral, LM Studio… |
| `anthropic` | Claude API (Anthropic) |

### Security principle: no key in the database

The SQLite database is not encrypted and ends up in backups. **No API key is stored in
it.** The `llm_providers` table only holds the *name* of the environment variable
(`api_key_env`, e.g. `OPENAI_API_KEY`); the value stays in the `.env` and is resolved only
at call time. That name is validated against an allow-list (`LLM_*` or `*_API_KEY`) so it
cannot point at a system secret (`SECRET_KEY`, `ENTRA_CLIENT_SECRET`…).

### Adding a provider

1. **Add the key to the `.env`** with a conforming name (`LLM_*` or `*_API_KEY`):

   ```env
   OPENAI_API_KEY=sk-...
   ```

2. **Restart the summaries daemon** (the `.env` is read at startup only):

   ```bash
   uv run oceens-summaries
   ```

3. **Create the provider** in `/backend/providers` → *+ Nouveau fournisseur*: name, API
   type, base URL, environment variable name (`OPENAI_API_KEY`) and a default model. The
   **key present / absent** indicator confirms the variable is loaded. The **Tester**
   button checks that the URL and the key answer, then sends a one-token generation to
   confirm the account can actually generate (see below).

4. **Attach a prompt** to the provider: in `/backend/prompts`, a `<select>` picks the
   provider of a prompt. A prompt without a provider (`provider_id` NULL) falls back to
   Ollama EPF.

> [!NOTE]
> A provider referenced by at least one prompt cannot be deleted (it would break the
> configuration of those prompts).

### Exhausted credit and other provider errors

Every provider reports its failures in its own format: an exhausted credit is a
`429 insufficient_quota` at OpenAI, but a `400 "Your credit balance is too low"` at
Anthropic. `oceens.services.llm_client` normalises those answers into categories (`quota`,
`rate_limit`, `auth`, `model`, `server`) and derives a readable message from them:

> ⚠️ Crédit ou quota épuisé chez le fournisseur : la clé est valide mais le compte ne peut
> plus générer. Rechargez le compte ou choisissez un autre fournisseur. (fournisseur
> OpenAI, modèle gpt-4o-mini, HTTP 429)

That message is written to `Summary.metadata_text` in place of the raw JSON — so it is
visible straight from the interface when a summary fails. The provider's raw answer stays
in the daemon logs for diagnosis.

> [!IMPORTANT]
> The **Tester** button does not merely list the models: at OpenAI as at Anthropic,
> `GET /v1/models` still answers perfectly with a zero balance. A one-token generation
> ping (negligible cost) is therefore sent afterwards — it is the only way to spot an
> exhausted credit **before** launching a summary campaign.

---

## Cost of the summaries

The cost of each summary is **measured, not estimated**. At generation time the daemon
records the token counters returned by the provider (`Summary.input_tokens`,
`output_tokens`, `model_used`): that is the only chance to capture them, no API lets you
ask for them afterwards. The amount is then obtained by crossing those counters with the
price list.

### Price list — `/backend/llm/prices`

Prices live in the database (table `llm_model_prices`) **in euros**, and are editable from
the administration: no release is needed to follow a price revision, nor to cover a
locally added provider.

Two components add up:

- a **flat cost per generation** (`flat_cost_min`, `flat_cost_max`), for a model whose cost
  is not per token;
- a **price per million tokens**, in and out.

Pre-filled at startup (`seed_model_prices`, idempotent — a price corrected by hand is
never rewritten):

| Model | Flat cost per generation | In €/M | Out €/M |
| --- | --- | ---: | ---: |
| `gemma4:26b` (Ollama EPF, self-hosted) | 0.02 – 0.05 € | 0.00 | 0.00 |
| `claude-opus-5` | — | 4.60 | 23.00 |
| `claude-sonnet-5` | — | 2.76 | 13.80 |
| `claude-haiku-4-5` | — | 0.92 | 4.60 |

The school's LLM is not free: self-hosted does not mean costless. GPU, electricity and
hardware amortisation come to 2–5 cents per summary, all included — hence a flat range
rather than a per-token price.

Anthropic publishes in dollars per million tokens; those prices are converted once, at the
`usd_to_eur` rate stored in `settings` (0.92 by default, editable in the administration
alongside the price list). The rate only applies at entry: changing it later does not
rewrite existing prices, so a price already applied to past summaries never changes
retroactively.

Other providers' prices (OpenAI, Mistral, Groq…) are **left to be entered**: they are not
guessed. A provider-specific price wins over a generic price for the same model name.

### Where to look

| Where | What |
| --- | --- |
| `/backend/llm/costs` | Global cost, broken down by survey and by model (admin) |
| The 💰 button on a survey row | Summary cost of that survey |

### What is not priced

A summary cannot be priced when its counters are missing (generated before this feature,
or a provider that does not expose them) or when its model has no recorded price. It is
then **counted separately**, never estimated nor flattened to zero: an invented amount
would be more harmful than a missing one, since it would be displayed with the authority
of a real amount. The screens state explicitly when a total is partial.

Not to be confused with a **zero** cost: a self-hosted model has a real, small flat cost
per generation, which is not the same information as "unknown".

> [!IMPORTANT]
> Tracking starts when the feature goes live: summaries generated before it have no
> counters in the database and cannot be priced retroactively.

---

## Logging

Application logs use the standard Python `logging` module and the `uvicorn` logger, so
that messages from the application, from `auth.py` and from `seed.py` inherit the format,
the colours and the handlers the server already configured.

| Level | Used for |
|-------|----------|
| `DEBUG` | Detailed information useful while developing and seeding. |
| `INFO` | Startup, shutdown and normal application operations. |
| `WARNING` | An expected resource is missing, or a non-blocking situation. |
| `ERROR` / `EXCEPTION` | An operation failed; `logger.exception()` keeps the traceback. |
| `CRITICAL` | Missing mandatory configuration, preventing startup. |

Example:

```python
import logging

logger = logging.getLogger("uvicorn")

logger.info("Opération terminée")

try:
    operation_risquee()
except Exception:
    logger.exception("Échec de l'opération")
```

New diagnostics should use the appropriate logger rather than `print()`. The application
level is currently set to `DEBUG` in `oceens.core.dependencies`. Application logs go through
the Uvicorn handler, usually written to `stderr`; with separate redirection, use for
instance `2> error.log` to collect them.

---

## Project structure

Everything that Python imports lives under `src/oceens/`, a single installable package.
The repository root keeps only what is not code: configuration, documentation and the
container files.

```
OceENS/
├── pyproject.toml                # Package metadata, dependencies and entry points
├── uv.lock                       # Exact resolved versions (committed)
├── .python-version               # Python 3.12, picked up by uv
├── launch.sh                     # Launch script (production, without Docker)
├── Dockerfile                    # Application image
├── docker-compose.yaml           # Service, port, env_file and volumes
├── .dockerignore                 # Files excluded from the Docker build
├── .env.example                  # Reference configuration, to copy to .env
├── .env                          # Environment variables (⚠️ never committed)
├── .gitignore                    # Files and directories ignored by Git
├── Template_2025.md              # Reference wording of the survey template
├── CONTEXT.md                    # Domain glossary and language boundary
├── AGENTS.md, CLAUDE.md          # Conventions for coding agents
├── tach.toml                     # The package boundary rule, checked by `tach check`
│
├── scripts/
│   └── check_cycles.py           #   Rejects import cycles between packages
│
├── docs/
│   ├── smoke-test.md             #   Manual validation procedure (no CI yet)
│   ├── adr/                      #   Architecture decision records
│   └── agents/                   #   Issue tracker, triage labels, domain docs
│
├── database/                     # Database directory (ignored by Git)
│   └── db_oceens.db
│
├── .venv/                        # Environment created by uv sync (not committed)
│
└── src/oceens/                   # The package — everything below is importable
    ├── README.md                 # The package boundary convention, next to the code
    ├── main.py                   # FastAPI factory, middlewares and router assembly
    ├── sondage_loader.py         # Loads a full survey for the export
    ├── survey_loader_from_xlsx.py     # Imports surveys from an Excel file
    ├── summaries_generator_daemon.py  # Asynchronous LLM summary processing (separate process)
    │
    ├── core/                     # Low-level access and security
    │   ├── auth.py                #     Microsoft Entra ID flow and dev sign-in
    │   ├── database.py            #     SQLite engine, schema migration, SessionDep
    │   ├── security.py            #     Roles, scopes, access control
    │   ├── dependencies.py        #     Shared Jinja templates and logger
    │   ├── settings_store.py      #     Application settings (exchange rate)
    │   └── seed.py                #     Initial data and program synchronisation
    │
    ├── models/                    # SQLModel schema, one file per table
    │   ├── __init__.py            #     Re-exports every class (see its docstring)
    │   └── User.py, Survey.py, ...
    │
    ├── routers/                   # Routes split by business domain
    │   ├── pages.py               #     Home page and dashboards per role
    │   ├── surveys.py             #     Surveys: CRUD, status, export, visualisation
    │   ├── students.py            #     Students invited to a survey
    │   ├── users.py               #     User creation and roles
    │   ├── summaries.py           #     LLM summary triggering
    │   ├── prompts.py             #     Prompt administration
    │   ├── survey_templates.py    #     Survey template administration
    │   ├── sections_questions.py  #     Section and question administration
    │   └── llm/                   #     LLM administration (URLs unchanged)
    │       ├── _access.py         #       Shared access control of the LLM screens
    │       ├── providers.py       #       LLM providers (CRUD + connection test)
    │       ├── prices.py          #       Per-model price list
    │       └── costs.py           #       Global cost and per-survey cost
    │
    ├── services/                  # Business logic
    │   ├── helpers.py             #     Navigation, statistics, filters, sorting
    │   ├── visualisation_data.py  #     Aggregations and visualisation context
    │   ├── llm_client.py          #     Multi-provider LLM client (ollama/openai/anthropic)
    │   ├── llm_costs.py           #     Summary cost (measured tokens × price list)
    │   └── export_csv.py          #     CSV export of the answers
    │
    ├── seed_data/                 # Seed data read at startup (was import/)
    │   ├── Program_list.csv       #     Programs, synchronised on every start
    │   └── seed_answers*.csv      #     Demo answers of the seeded surveys
    │
    ├── llm_utils/                 # LLM tooling outside the application (was llm-utils/)
    │   └── README.md              #     (cost tracking moved into the app, see above)
    │
    ├── templates/                 # HTML templates (Jinja2)
    │   ├── index.html                  # Home / sign-in page
    │   ├── dev_login.html              # Dev sign-in page
    │   ├── dashboard/
    │   │   ├── admin.html
    │   │   ├── student.html
    │   │   ├── program_manager.html
    │   │   ├── facilitator.html
    │   │   ├── campus_manager.html
    │   │   ├── teachers-analytics.html # Teacher satisfaction
    │   │   ├── survey.html             # Answering a survey
    │   │   ├── survey_create.html      # Survey creation
    │   │   └── visualisation.html      # Answer visualisation
    │   ├── backend/                    # Administration pages (admin only)
    │   │   ├── prompts.html            # LLM prompt list
    │   │   ├── prompt_form.html        # Shared create/edit form
    │   │   ├── templates.html          # Survey templates
    │   │   └── llm/                    # LLM screens (providers, prices, costs)
    │   │       ├── providers.html
    │   │       ├── provider_form.html
    │   │       ├── prices.html         # Editable price list
    │   │       └── costs.html          # Global and per-survey cost
    │   └── template_parts/             # Fragments shared between dashboards
    │       ├── part_site_header.html
    │       ├── part_dashboard_navigation.html
    │       ├── part_theme_switcher.html
    │       └── ...
    │
    └── static/
        ├── css/                   # admin.css, student.css, program_manager.css, survey.css,
        │                          # survey_create.css, visualisation.css, prompt_form.css,
        │                          # llm_backend.css, theme.css, site_header.css,
        │                          # dashboard_navigation.css, responsive.css
        ├── js/
        │   └── survey.js
        └── img/
```

---

## Notable features

### Teacher analytics

`/dashboard/teachers/analytics` (`campus_manager`, `program_manager`) aggregates the
satisfaction score per `(teacher, survey)` from the `QCU_Satisfaction` answers that carry
an `Answer.teacher` (ME sections). The teacher list is sorted with `teacher_sort_key()`,
case- and accent-insensitive, and stays filterable by school year, semester, program and
teacher.

### Teacher filter in the visualisation

A client-side selector filters the visualisation without reloading: only the modules of
the chosen teacher stay visible, the Campus and Formation sections being hidden. The page
reads `?teacher=<name>` on load to pre-filter itself; links from the analytics screen pass
that parameter, so clicking a teacher's score opens their view directly.

### Surveys imported from Excel

Surveys loaded by `oceens.survey_loader_from_xlsx` have no `QCU_Attendance` question:
`oceens.services.visualisation_data` then uses `satisfaction_responses_count` as a fallback
denominator for the teacher score. Teacher names are normalised with `.title()` both at
import and at aggregation, merging case variants (`"GADEMER Antoine"` and
`"Gademer Antoine"` = a single entry). Questions are sorted by `question_id` in the
template, which puts the charts before the verbatims whatever the insertion order.

### Campus management scope

The `campus_manager` dashboard only shows closed surveys with at least one respondent. The
questionnaire link and the QR code are hidden there (`can_view_survey_link=False`): this
role reads results without distributing surveys. The `{% if can_view_survey_link |
default(true) %}` guard leaves the other dashboards unchanged.

### Orphan student cleanup

When a survey is deleted, students no longer attached to **any other** survey are deleted
too, to avoid accumulating unused accounts (`oceens.services.helpers`,
`_delete_orphan_students`). A safeguard protects users holding a privileged role (`admin`,
`program_manager`, `facilitator`, `campus_manager`): a teacher or a manager who answered a
survey is never erased.

### Adding a user by mail

The *Utilisateurs* tab of the administrator dashboard offers a **+ Ajouter un utilisateur**
button: a mail is enough to create the account, with the `student` role by default
(`POST /api/users`, admin only). The mail is validated (format + allowed domain) and
duplicates are refused.

---

## Deployment checklist

- [ ] `.env` created with the real Azure credentials and a dedicated `SECRET_KEY`
      (required unless `AUTH_MODE=dev`, otherwise the application refuses to start)
- [ ] `AUTH_MODE` unset or `entra`
- [ ] Valid SSL certificate (Let's Encrypt or equivalent)
- [ ] `https_only=True` in the SessionMiddleware (automatic unless `AUTH_MODE=dev`)
- [ ] Database present (`database/db_oceens.db`) or its directory mounted
- [ ] Environment variables kept secret, including `LLM_API_KEY`
- [ ] **Docker Compose**: `.env` loaded through `env_file`, never copied into the image;
      `LOCAL_DATABASE_DIR` pointing at the right directory
- [ ] `oceens-summaries` started if LLM summaries are used

---

## Validating a change

The repository has no automated test suite and no CI. Before proposing a change, run the
manual procedure in **[docs/smoke-test.md](docs/smoke-test.md)**: static checks, startup
from a fresh clone, Docker, exit codes on invalid configuration, and the LLM key. Then
test the routes your change touches, on a throwaway SQLite database (never a copy of
production), with the relevant roles and survey statuses.

Two of those static checks are machine-checked architecture rules rather than behaviour:

```
uv run tach check
uv run python scripts/check_cycles.py
```

No import may reach past a package's public surface, and no two packages may depend on
each other. **[src/oceens/README.md](src/oceens/README.md)** states the rule and how to
write an interface that satisfies it.

---

## Resources

- [FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI and Uvicorn logging guide](https://apitally.io/blog/fastapi-logging-guide)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Microsoft Graph](https://learn.microsoft.com/en-us/graph/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Pandas](https://pandas.pydata.org/)

---

**OcéEns team** — EPF
