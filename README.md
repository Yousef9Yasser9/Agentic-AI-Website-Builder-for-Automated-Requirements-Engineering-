# AI Website Builder

AI Website Builder is a local, full-stack platform that turns a plain-language
application idea into a structured specification, architecture, data model,
documentation, and a runnable FastAPI web application.

The platform uses Ollama for local AI inference. Generated applications are written
as project-specific Python and standalone HTML/CSS/JavaScript source. The active
generation path does not publish Jinja templates or replace generated code with a
generic application shell.

## Current Project Folder

This cleaned checkout is the final working folder:

```text
C:\Users\Mahmood zuairy\OneDrive - Arab Academy for Science and Technology\sem 8\Project 2\ai-website-builde neww (2)\ai-website-builder-final
```

All backend, frontend, builder, checkpoint, and generated-app commands should be
run from that folder unless a command explicitly says to enter `frontend`.

## Final Capabilities

- Email and password authentication with JWT sessions.
- Email OTP verification, resend, forgot-password, and reset-password flows.
- Restricted administrator workspace: admin users see only admin pages and are
  redirected away from normal builder/user routes.
- Role-aware generated applications that preserve prompt roles such as Student,
  Teacher, Patient, Doctor, Staff, Customer, and Admin.
- Project ownership and administrator-wide project management.
- Eleven-stage guided application design workflow.
- Local Ollama model configuration and service monitoring.
- Requirements, user stories, architecture, data model, SRS, and post-build analysis.
- Ollama-driven cleaned-spec, requirements, user-story, architecture, data-model,
  SRS, and code-generation stages with backend-side JSON repair and shape guards.
- Project-specific FastAPI, SQLAlchemy, JWT, and plain frontend source generation.
- Domain-aware generated frontends with different visual identities, role dashboards,
  and page presentations for each app.
- Generated application build, seed, runtime test, healing, and preview controls.
- Static validation before generated applications are allowed to start.
- Backward recovery for bad generated context: the backend can regenerate
  architecture or data-model stages and re-cascade downstream stages when a
  failure diagnosis shows the problem is upstream, not just a code bug.
- Administrator dashboards for users, projects, generated apps, models, logs, and system health.
- Light, dark, and operating-system theme preferences.

## Technology

| Area | Technology |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Client state | TanStack Query, Zustand, React Context |
| Backend | FastAPI, Pydantic, SQLAlchemy |
| Authentication | JWT, bcrypt, email OTP |
| Builder AI | Ollama local API |
| Builder storage | JSON checkpoints and generated project folders |
| Default database | SQLite |
| Generated apps | FastAPI, SQLAlchemy, JWT, domain-specific plain HTML/CSS/JavaScript |
| Validation | pytest, live HTTP tests, source contracts, self-healing |

## Quick Start

### Requirements

- Python 3.10 or newer.
- Node.js 18 or newer.
- Ollama installed and running at `http://127.0.0.1:11434`.
- Ollama planning model: `llama3.1:8b`.
- Ollama code-generation model: `qwen2.5-coder:14b`.

Recommended model pulls for a stronger PC:

```powershell
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:14b
```

### Install

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

cd frontend
npm install
cd ..
```

Create the local configuration:

```powershell
Copy-Item .env.example .env
```

Set a strong `SECRET_KEY`, administrator credentials, and SMTP credentials in
`.env`. Without SMTP, OTP codes are printed in the backend console for local
development.

### Local Admin Login

The current local `.env` and `.tmp/builder_auth.db` in this checkout are ready
with this platform administrator account:

```text
Email: admin@example.com
Password: change_me_admin_password
```

The first-admin seed only creates this account when no admin exists yet. If you
change `FIRST_ADMIN_PASSWORD` later, delete `.tmp/builder_auth.db` or update the
admin password through the app/database for the new value to apply.

Generated web apps have their own seeded demo admin after the app build/seed
step:

```text
Email: admin@example.com
Password: Admin1234!
```

### Admin Workspace

When the platform admin logs in, the frontend uses a restricted admin shell. It
shows only administrator pages:

- `/admin`: platform console.
- `/admin/users`: user management.
- `/admin/projects`: all checkpoints and project ownership.
- `/admin/projects/:id`: admin view of any project checkpoint.
- `/admin/generated-apps`: generated app servers and status.
- `/admin/models`: Ollama architect/coder model settings.
- `/admin/system`: storage, health, and cleanup.
- `/admin/logs`: recent generation and system logs.

Admin users are redirected back to `/admin` if they manually open normal routes
such as `/dashboard`, `/builder`, `/projects`, `/templates`, `/profile`, or
`/settings`. Normal users are still blocked from `/admin/*`.

### Run Development Servers

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, in a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/api/health`
- API documentation: `http://127.0.0.1:8000/docs`
- Ollama: `http://127.0.0.1:11434`

The Vite development server proxies `/api` and `/auth` requests to port `8000`.

## Workflow

The builder saves progress after every stage:

1. `PLAIN_TEXT`: initial application idea.
2. `CLEANED_SPEC`: normalized product specification.
3. `REQUIREMENTS`: functional and non-functional requirements.
4. `USER_STORIES`: traceable stories and acceptance criteria.
5. `ARCHITECTURE`: roles, pages, modules, routes, and theme.
6. `DATA_MODEL`: entities, fields, and relationships.
7. `SRS_DOCUMENTATION`: generated software requirements document.
8. `UI_SELECTION`: automatic domain-aware frontend direction and style confirmation.
9. `CODE_GENERATION`: blueprint, manifest, and application source.
10. `BUILD_AND_RUN`: environment setup, database seed, and runtime validation.
11. `PREVIEW`: managed generated-application server.

Every successful stage is also saved into checkpoint history. That lets recovery
logic inspect previous stage snapshots before it regenerates an upstream stage.

## Generation Guarantees

The active generator:

- Uses the configured Ollama architect model for product interpretation,
  requirements, user stories, architecture, data model, SRS, and post-analysis.
- Uses the configured Ollama coder model for from-scratch source generation.
- Rejects pasted prompts that contain multiple separate app briefs. Create one
  builder project per app so roles, entities, and forbidden modules do not mix.
- Produces backend, auth, schemas, CRUD, seed, and frontend files from the project
  context.
- Emits standalone `.html`, `.css`, `.js`, and Python files and rejects Jinja
  expressions and `.j2` output in generated apps.
- Preserves domain roles from the prompt instead of collapsing every app to only
  `Customer` and `Admin`.
- Uses one `User` account table with `User.role` for login roles, while related
  domain records point back to the correct role owner.
- Supports JSON login and OAuth2-compatible form login in generated apps.
- Applies exact read/write role checks and ownership filtering for scoped entities.
- Creates domain-specific frontends for both admin and normal users:
  healthcare, school, commerce, property, workflow, finance, restaurant, event,
  and unique fallback styles.
- Renders normal-user pages as catalogs, cards, timelines, boards, or ledgers
  when that fits the entity instead of always using a generic admin table.
- Keeps admin pages as management surfaces, but styles them as domain command
  dashboards rather than one repeated shell.
- Creates idempotent seed data without dropping tables.
- Provides authenticated dashboard statistics.
- Records generated-file hashes in `_builder_artifacts/generation_manifest.json`.

The current default model split is `llama3.1:8b` for planning, requirements,
architecture, data model, SRS, and post-analysis, plus `qwen2.5-coder:14b` for
code generation. LLM refactor is disabled by default because it is a slower
quality pass. Runtime healing is enabled by default so generated apps get a
bounded repair attempt when validation points to a fixable runtime problem.

Generated applications are not marked runnable until they pass:

- Required-file validation.
- Python compilation.
- Plain-HTML and authentication contract validation.
- Seed execution and repeatability checks.
- Live page, API, database, role, and ownership tests.
- Bounded project-aware repair attempts when runtime tests fail.

## Project Structure

```text
ai-website-builder-final/
|-- backend/                  FastAPI API, authentication, admin, and orchestration
|   |-- app/
|   |   |-- auth/             JWT, OTP, SMTP, users, database
|   |   |-- routes/           HTTP route modules
|   |   |-- schemas/          API request and response models
|   |   `-- services/         Builder service and process management
|   `-- README.md             Backend documentation
|-- frontend/                 React and TypeScript application
|   |-- src/
|   |   |-- components/       UI, layout, auth, admin, builder, stages
|   |   |-- contexts/         Authentication state
|   |   |-- hooks/            Query and workflow hooks
|   |   |-- pages/            Public, user, auth, and admin screens
|   |   |-- routes/           React Router configuration
|   |   |-- services/         Typed backend API clients
|   |   |-- stores/           Theme, builder, and toast state
|   |   |-- types/            Shared TypeScript contracts
|   |   `-- utils/            Formatting and stage helpers
|   `-- README.md             Frontend documentation
|-- builder/                  Prompts, checkpoints, tests, validation, healing
|-- generated_apps/
|   |-- generator/            From-scratch source generator and contracts
|   `-- projects/             Generated application workspaces
|-- checkpoints/              Persisted builder project state
|-- scripts/
|   |-- archive/              Historical one-off repair scripts
|   |-- diagnostics/          Local environment diagnostic tools
|   `-- examples/             Small integration examples
|-- routers/                  Legacy generator compatibility resources
|-- templates/                Legacy compatibility resources
|-- .env.example              Environment variable reference
|-- requirements.txt          Python dependencies
|-- schema.json               Project schema reference
`-- README.md                 Main project documentation
```

Runtime-generated directories such as `.venv`, `.tmp`, `frontend/node_modules`,
`frontend/dist`, checkpoints, and generated projects are not source modules.

## Persistent Data

- Authentication database: `.tmp/builder_auth.db` by default.
- Project checkpoints: `checkpoints/<project_id>/checkpoint.json`.
- Generated repository: `generated_apps/projects/<project_id>/v1`.
- Convenience copy: `generated_apps/projects/latest`.
- Builder artifacts: generated repository `_builder_artifacts/`.
- Model settings: `.tmp/model_settings.json`.

Do not commit `.env`, database files, virtual environments, generated project
workspaces, or frontend dependency/build directories.

## Common Commands

If your terminal is currently in the outer folder:

```powershell
cd ".\ai-website-builder-final"
```

If you are elsewhere, jump to the final project root directly:

```text
C:\Users\Mahmood zuairy\OneDrive - Arab Academy for Science and Technology\sem 8\Project 2\ai-website-builde neww (2)\ai-website-builder-final
```

Run Ollama first, if it is not already running:

```powershell
ollama serve
```

Check installed Ollama models:

```powershell
ollama list
```

Check Ollama HTTP status:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

First-time project setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
cd ..
Copy-Item .env.example .env
```

Run the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Run the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open the builder:

```text
http://127.0.0.1:5173
```

Frontend production build:

```powershell
cd frontend
npm run build
```

Frontend production preview:

```powershell
cd frontend
npm run preview
```

Compile critical Python modules:

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  backend\app\main.py `
  backend\app\services\builder_service.py `
  generated_apps\generator\repo_generator.py
```

Check backend health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Open backend API documentation:

```text
http://127.0.0.1:8000/docs
```

Generated apps are normally started from the Builder UI with the Build/Preview
buttons. If you need to inspect the latest generated source:

```powershell
cd generated_apps\projects\latest
Get-ChildItem
```

Recommended local testing settings:

- Keep the default split-model mode on the stronger PC:
  `llama3.1:8b` for architect stages and `qwen2.5-coder:14b` for code generation.
- If you must test on a weaker laptop with only one model installed, temporarily
  enable `single_model_mode` from the admin Models page and expect lower coding
  quality.
- Keep LLM refactor off while testing many prompts. Runtime healing is currently
  enabled by default and can be turned off only if the PC is too slow.
- Use the suggested domain UI in the UI phase unless it detects the wrong domain.
- Turn on slower debug/refactor passes only after the first app builds and runs.
- Current default generation timeouts are: requirements and user stories 60
  minutes, architecture 120 minutes, data model 120 minutes, SRS 60 minutes,
  code generation 60 minutes, refactor 30 minutes, post-analysis 60 minutes, and
  JSON repair 30 minutes. These are upper limits, not target durations; normal
  generations should finish earlier on a strong PC.

## Environment Variables

Important variables are documented in `.env.example`:

- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `OTP_EXPIRE_MINUTES`, `OTP_MAX_ATTEMPTS`
- `DATABASE_URL`
- `FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_PASSWORD`, `FIRST_ADMIN_FULL_NAME`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS`

Use real SMTP credentials when OTP codes must arrive by email. Local console OTP
output is only a development fallback.

## Documentation

- [Backend documentation](backend/README.md)
- [Frontend documentation](frontend/README.md)

These three README files are the maintained project documentation. Historical
status reports and temporary Markdown notes have been removed. Generated app
READMEs and checkpoint files such as `srs.md` are runtime artifacts, not
maintained source documentation.

## ?? Project Demo

[?? Watch Project Demo](https://drive.google.com/file/d/1j1P60JvhCxq1vTNt0lA-ReeMu72F-Xfy/view?usp=sharing)
