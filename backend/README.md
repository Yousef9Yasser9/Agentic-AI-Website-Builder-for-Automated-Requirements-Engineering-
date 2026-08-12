# Backend

The backend is a FastAPI application responsible for platform authentication,
project ownership, AI workflow orchestration, generated application management,
administrator operations, Ollama model settings, and system monitoring.

## Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful URLs:

- Health: `http://127.0.0.1:8000/api/health`
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

When `frontend/dist` exists, FastAPI mounts it at `/` for a same-origin production
deployment. During development, Vite runs separately and proxies API requests.

## Structure

```text
backend/
|-- app/
|   |-- main.py                  FastAPI application and router registration
|   |-- auth/
|   |   |-- config.py            Environment-backed auth and SMTP settings
|   |   |-- database.py          SQLAlchemy engine, sessions, initialization
|   |   |-- deps.py              Current-user and administrator dependencies
|   |   |-- email_service.py     SMTP delivery and development OTP fallback
|   |   |-- models.py            User and OTP persistence models
|   |   |-- schemas.py           Authentication and admin API schemas
|   |   |-- security.py          Password hashing and JWT operations
|   |   |-- seed.py              First administrator creation
|   |   `-- service.py           Registration, verification, login, reset logic
|   |-- routes/
|   |   |-- auth_routes.py       Account and OTP endpoints
|   |   |-- projects_routes.py   Project CRUD, ownership, and artifacts
|   |   |-- workflow_routes.py   AI workflow stage generation
|   |   |-- generation_routes.py Source generation and generation logs
|   |   |-- build_routes.py      Build, start, stop, and server status
|   |   |-- settings_routes.py   Administrator model settings and Ollama status
|   |   |-- system_routes.py     Storage report and cleanup
|   |   |-- admin_routes.py      Administrator dashboards and management
|   |   `-- helpers.py           Shared error and project-access wrappers
|   |-- schemas/
|   |   `-- project_schema.py    Builder request models
|   `-- services/
|       `-- builder_service.py   Main workflow and process orchestration
`-- README.md
```

## Authentication

Platform users authenticate through `/auth`, not `/api/auth`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Create an unverified account and send an OTP |
| POST | `/auth/verify-otp` | Verify registration or a reset code |
| POST | `/auth/resend-otp` | Send a replacement OTP |
| POST | `/auth/login` | Return JWT token and user data |
| POST | `/auth/logout` | Client-compatible logout response |
| GET | `/auth/me` | Return the authenticated user |
| POST | `/auth/forgot-password` | Send a password-reset OTP |
| POST | `/auth/reset-password` | Validate OTP and set a new password |

JWT bearer tokens are read by dependencies in `auth/deps.py`. Administrator-only
routes use `require_admin`.

### OTP Email

`email_service.py` sends verification codes through SMTP when `SMTP_HOST` and
`SMTP_FROM` are configured. When SMTP is absent, the OTP is logged and printed to
the backend terminal for local development.

For real email delivery, configure:

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=account@example.com
SMTP_PASSWORD=app-password
SMTP_FROM=account@example.com
SMTP_TLS=true
```

OTP expiry and attempt limits are controlled by `OTP_EXPIRE_MINUTES` and
`OTP_MAX_ATTEMPTS`.

## Project APIs

All project endpoints require a JWT. Regular users can access only projects owned
by their user ID; administrators can access all projects.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/projects` | List accessible projects |
| POST | `/api/projects` | Create a project |
| GET | `/api/projects/{project_id}` | Read a project |
| DELETE | `/api/projects/{project_id}` | Delete a project |
| POST | `/api/projects/{project_id}/save` | Save project data |
| GET | `/api/projects/{project_id}/state` | Load stage state |
| POST | `/api/projects/{project_id}/stage` | Change active stage |
| POST | `/api/projects/{project_id}/plain-text` | Update the idea |
| GET | `/api/projects/{project_id}/artifact/{name}` | Download an artifact |

Project state is stored atomically in
`checkpoints/<project_id>/checkpoint.json`.

## Workflow APIs

Workflow routes use `/api/projects/{project_id}`:

- `POST /generate/cleaned-spec`
- `POST /generate/requirements`
- `POST /generate/user-stories`
- `POST /generate/architecture`
- `POST /generate/data-model`
- `POST /generate/srs`
- `POST /ui-selection`
- `POST /generate/code`
- `POST /recover/regenerate-stage`
- `POST /generate/post-analysis`
- `GET /logs`

The service validates prerequisites before each stage and saves every successful
result to the checkpoint.

The current UI selection stage is a frontend-direction checkpoint. It should
confirm the generated app's domain, visual identity, role dashboards, navigation,
and page presentation style before code generation. It is not meant to force every
app into the same admin template.

The frontend now exposes admin-only project and operations routes through a
restricted shell. The backend still enforces access with JWT dependencies:
regular users can access only their own projects, while admins can access every
checkpoint and administrator endpoint.

### Backward Recovery

`POST /api/projects/{project_id}/recover/regenerate-stage` accepts:

```json
{
  "stage": "ARCHITECTURE",
  "reason": "Generated code failed because the architecture missed doctor pages."
}
```

Supported recovery targets are currently upstream structural stages such as
`ARCHITECTURE` and `DATA_MODEL`. The backend saves a pre-recovery checkpoint
history entry, regenerates the requested stage with Ollama, re-cascades affected
downstream stages, preserves the existing UI selection when possible, and then
clears the active recovery diagnosis.

During code generation and build validation, `failure_classifier.py` can label
failures as `CODE_BUG`, `ARCHITECTURE_MISMATCH`, or `DATA_MODEL_GAP`. Code bugs
stay in the bounded repair loop. Architecture or data-model gaps can trigger
automatic recovery or be surfaced through `project_data.recovery_diagnosis` for
manual review.

## Generation and Build

`builder_service.py` coordinates:

1. Cleaned-spec interpretation through the configured Ollama architect model.
2. Requirements, user stories, architecture, data model, SRS, post-analysis, and
   code generation through the configured Ollama models.
3. Blueprint and manifest creation.
4. Project-specific source generation.
5. Static source validation.
6. Optional frontend refactoring when `enable_llm_refactor` is enabled.
7. Runtime test generation and bounded self-healing when
   `enable_runtime_healing` is enabled.
8. Generated virtual environment and dependency installation.
9. Database creation and idempotent seed execution.
10. Managed Uvicorn preview process.

Build and preview routes:

| Method | Path |
| --- | --- |
| POST | `/api/projects/{project_id}/build` |
| POST | `/api/projects/{project_id}/start-server` |
| POST | `/api/projects/{project_id}/stop-server` |
| GET | `/api/projects/{project_id}/server-status` |

A generated application is not marked `build_done` unless seed execution, runtime
validation, and the final source gate all pass.

Current defaults are tuned for the stronger PC workflow: `llama3.1:8b` handles
planning/requirements/user stories/architecture/data model/SRS/post-analysis and
`qwen2.5-coder:14b` handles code generation. Single-model mode is off by default.
LLM refactor is off by default; runtime healing is on by default.

## Administrator APIs

Administrator routes use `/api/admin`:

- `/stats`
- `/users`
- `/users/{user_id}`
- `/projects`
- `/generated-apps`
- `/system/health`
- `/logs`
- `/models/test`

Additional administrator-only endpoints:

- `GET/PUT /api/settings/models`
- `GET /api/ollama/status`
- `GET /api/system/size-report`
- `POST /api/system/cleanup`

## Builder Modules

The backend service delegates specialized work to `builder/`:

- `prompts.py`: workflow and repair prompts.
- `checkpoint_manager.py`: atomic checkpoint persistence.
- `failure_classifier.py`: classifies generated-app failures so the backend knows
  whether to repair code or regenerate upstream context.
- `blueprint_generator.py`: implementation blueprint and file manifest.
- `architecture_guard.py`: preserves domain roles, separates role pages, and
  protects write endpoints. Staff, manager, doctor, teacher, agent, and other
  normal operating roles are not collapsed into Admin.
- `data_model_guard.py`: schema normalization.
- `contract_validator.py`: generated-app source contracts.
- `runtime_test_generator.py`: generated live runtime tests.
- `runtime_app_server.py`: isolated Uvicorn test process.
- `runtime_self_healing.py`: bounded project-aware repair loop.
- `self_healing_agent.py`: repair parsing, backups, and file application.
- `seed_runner.py`: generated seed execution.
- `cleanup_manager.py`: storage cleanup.
- `ollama_client.py`: Ollama communication.

`generated_apps/generator/repo_generator.py` produces the generated repository.
Its active path emits plain source rather than Jinja files, preserves prompt roles
where possible, applies exact generated-app read/write role rules, and creates
domain-specific frontends for both admin and normal users.

`generated_apps/generator/engine_rules.py` centralizes generated-app entity
classification, read/write role inference, ownership scoping, and navigation
visibility. Keep future permission changes there when possible.

Checkpoint history files are written beside the main checkpoint so recovery flows
can preserve evidence before regenerating upstream stages.

## Configuration

The backend loads the root `.env`.

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | JWT signing key |
| `ALGORITHM` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session lifetime |
| `OTP_EXPIRE_MINUTES` | OTP lifetime |
| `OTP_MAX_ATTEMPTS` | OTP attempt limit |
| `DATABASE_URL` | Platform authentication database |
| `FIRST_ADMIN_EMAIL` | Initial administrator email |
| `FIRST_ADMIN_PASSWORD` | Initial administrator password |
| `FIRST_ADMIN_FULL_NAME` | Initial administrator name |
| `SMTP_*` | OTP email transport |

Default model settings:

- Architect: `llama3.1:8b`
- Coder: `qwen2.5-coder:14b`
- Architect context: `8192`
- Coder context: `8192`
- Reviewer context: `8192`
- Code output cap: `8192`
- Requirements timeout: `3600` seconds
- Architecture timeout: `7200` seconds
- Data model timeout: `7200` seconds
- SRS timeout: `3600` seconds
- Code generation timeout: `3600` seconds
- Refactor timeout: `1800` seconds
- Post-analysis timeout: `3600` seconds
- JSON repair timeout: `1800` seconds
- Single-model mode: disabled
- LLM refactor: disabled
- Runtime healing: enabled

Administrators can update model settings through the settings API.

Default local platform admin for this checkout:

```text
Email: admin@example.com
Password: change_me_admin_password
```

This is controlled by `FIRST_ADMIN_EMAIL` and `FIRST_ADMIN_PASSWORD` in `.env`
and is only seeded automatically when no admin user exists yet.

Generated applications seed their own demo accounts after build. The standard
generated-app admin is:

```text
Email: admin@example.com
Password: Admin1234!
```

## Storage and Processes

- Platform SQLite database: `.tmp/builder_auth.db` by default.
- Checkpoints: `checkpoints/`.
- Generated apps: `generated_apps/projects/`.
- Latest generated copy: `generated_apps/projects/latest/`.
- Runtime logs: in-memory project logs and generated server log files.
- Preview ports: allocated per project by the builder service.

The service tracks child Uvicorn processes and stops existing project servers before
generation, rebuild, or restart operations.

## Verification

Compile backend-critical modules:

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  backend\app\main.py `
  backend\app\services\builder_service.py `
  builder\architecture_guard.py `
  builder\data_model_guard.py `
  builder\runtime_self_healing.py `
  generated_apps\generator\repo_generator.py
```

Check health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```
