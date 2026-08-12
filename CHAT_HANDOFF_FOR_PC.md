# AI Website Builder Chat Handoff

Date: 2026-06-22

This is the final updated working copy to use:

```text
C:\Users\Mahmood zuairy\OneDrive - Arab Academy for Science and Technology\sem 8\Project 2\ai-website-builde neww (2)\ai-website-builde neww (9)\ai-website-builde neww (2)\ai-website-builde neww (1)\ai-website-builder
```

This copy includes the latest frontend visualization work and the newer backend Agile-recovery work from the PC session.

## Project Identity

This repository is the AI Website Builder graduation project.

It is not one generated web app. It is the platform that takes a user prompt and generates complete web apps through an AI pipeline.

Main goal:

- User enters a web app idea.
- The builder runs structured stages.
- Ollama generates specs, architecture, data model, SRS, UI direction, code, build, and preview.
- The final generated apps should be domain-specific, not generic admin dashboards.

## Current Direction

The target final architecture is:

```text
Waterfall by default, Agile when needed.
```

Normal path:

```text
Idea -> Spec -> Requirements -> User Stories -> Architecture -> Data Model -> SRS -> UI -> Code -> Build -> Preview
```

Recovery path:

```text
Code fails -> diagnose root cause -> regenerate Architecture or Data Model -> re-cascade affected stages -> retry Code
```

## Current Frontend State

The frontend has the premium visualization upgrade.

Completed:

- Depth shadows added to Tailwind.
- Ambient floating orbs added.
- Scroll reveal motion added.
- Workflow preview rebuilt as a real pipeline diagram.
- Build timeline rebuilt as a semantic status timeline.
- Visual progress strips added to projects.
- Landing page visuals improved.
- Docs page visuals improved.
- Subtle ambient visuals added to auth and empty states.
- Old per-stage rainbow helper removed.
- Builder/stage workspace kept calm with existing blue/violet accent.
- Backend API contracts preserved.

## Current Backend State

Backend entry point:

```text
backend/app/main.py
```

Main backend service:

```text
backend/app/services/builder_service.py
```

Important backend folders:

```text
backend/app/routes
backend/app/auth
backend/app/schemas
backend/app/services
builder
generated_apps/generator
checkpoints
generated_apps/projects
```

This updated copy also includes Agile-recovery backend additions such as:

- `builder/failure_classifier.py`
- Recovery schema in `backend/app/schemas/project_schema.py`
- Recovery route changes in `backend/app/routes/generation_routes.py`
- Recovery logic references in `backend/app/services/builder_service.py`
- Failure diagnosis references in healing/runtime logic

## Workflow Stages

```text
PLAIN_TEXT
CLEANED_SPEC
REQUIREMENTS
USER_STORIES
ARCHITECTURE
DATA_MODEL
SRS_DOCUMENTATION
UI_SELECTION
CODE_GENERATION
BUILD_AND_RUN
PREVIEW
```

## Important API Endpoints

Health:

```text
GET /api/health
GET /api/ollama/status
```

Auth:

```text
POST /auth/register
POST /auth/verify-otp
POST /auth/resend-otp
POST /auth/login
GET  /auth/me
POST /auth/forgot-password
POST /auth/reset-password
```

Projects:

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
DELETE /api/projects/{project_id}
POST   /api/projects/{project_id}/plain-text
POST   /api/projects/{project_id}/stage
```

Workflow:

```text
POST /api/projects/{project_id}/generate/cleaned-spec
POST /api/projects/{project_id}/generate/requirements
POST /api/projects/{project_id}/generate/user-stories
POST /api/projects/{project_id}/generate/architecture
POST /api/projects/{project_id}/generate/data-model
POST /api/projects/{project_id}/generate/srs
POST /api/projects/{project_id}/ui-selection
POST /api/projects/{project_id}/generate/code
```

Build and preview:

```text
POST /api/projects/{project_id}/build
POST /api/projects/{project_id}/start-server
POST /api/projects/{project_id}/stop-server
GET  /api/projects/{project_id}/server-status
GET  /api/projects/{project_id}/logs
```

Admin/settings:

```text
GET /api/settings/models
PUT /api/settings/models
GET /api/admin/stats
GET /api/admin/users
GET /api/admin/projects
GET /api/admin/generated-apps
GET /api/admin/system/health
```

## Run Commands

Do not copy an old `.venv` between machines. Recreate it if needed.

Backend:

```powershell
cd "C:\Users\Mahmood zuairy\OneDrive - Arab Academy for Science and Technology\sem 8\Project 2\ai-website-builde neww (2)\ai-website-builde neww (9)\ai-website-builde neww (2)\ai-website-builde neww (1)\ai-website-builder"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

Frontend:

```powershell
cd "C:\Users\Mahmood zuairy\OneDrive - Arab Academy for Science and Technology\sem 8\Project 2\ai-website-builde neww (2)\ai-website-builde neww (9)\ai-website-builde neww (2)\ai-website-builde neww (1)\ai-website-builder\frontend"
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

Backend URL:

```text
http://127.0.0.1:8000
```

API health:

```text
http://127.0.0.1:8000/api/health
```

## Ollama Setup

```powershell
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:14b
ollama list
```

Recommended baseline model settings:

```text
model_architect = llama3.1:8b
model_coder = qwen2.5-coder:14b
model_ctx_architect = 3072
model_ctx_coder = 8192
model_predict_code_cap = 4096
timeout_requirements_sec = 600
timeout_architecture_sec = 1200
timeout_data_model_sec = 1200
timeout_srs_sec = 900
timeout_code_generation_sec = 3600
single_model_mode = false
enable_llm_refactor = false
enable_runtime_healing = false
```

For a second quality test:

```text
enable_llm_refactor = true
enable_runtime_healing = true
timeout_code_generation_sec = 7200
timeout_refactor_sec = 3600 or 7200
```

## Admin And OTP Notes

Admin seed is controlled by `.env`:

```env
FIRST_ADMIN_EMAIL=admin@example.com
FIRST_ADMIN_PASSWORD=your_password
FIRST_ADMIN_FULL_NAME=Platform Admin
```

Set these before first backend run on a fresh PC.

OTP behavior:

- If SMTP is configured, OTP is sent to email.
- If SMTP is not configured, OTP prints in the backend terminal as `[DEV OTP]`.

SMTP keys:

```env
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_TLS=true
```

## What To Test

For every generated app, check:

- All stages finish.
- Architecture has enough pages and endpoints.
- Data model matches entities, roles, and rules.
- UI selection is domain-specific.
- Code generation finishes without timeout.
- Build succeeds.
- Server starts.
- Generated app opens.
- Seed data exists.
- Admin login works.
- Normal user login works.
- Role permissions are correct.
- Frontend does not look like the same generic table for every app.
- If code generation fails, check whether recovery diagnosis appears.

## What To Capture If Something Fails

Send to Codex:

- Exact prompt used.
- Screenshot of failed stage.
- Backend terminal error.
- Generation log from UI.
- `checkpoints/<project_id>/checkpoint.json` if needed.
- Generated app path from `generated_apps/projects/<project_id>/v1`.
- Browser console error if generated app frontend fails.

## Folder Warning

There are multiple copied folders in the parent directory.

The final updated copy is the nested `(9)` copy:

```text
ai-website-builde neww (9)\ai-website-builde neww (2)\ai-website-builde neww (1)\ai-website-builder
```

Do not delete older folders until the final updated copy has been tested and backed up.

