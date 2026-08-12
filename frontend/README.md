# Frontend

The frontend is a React and TypeScript single-page application for public product
pages, authentication, the normal user builder workspace, project management,
generated application controls, settings, and a restricted administrator
workspace.

## Run

From the project root:

```powershell
cd .\frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

The Vite server proxies `/api` and `/auth` to
`http://127.0.0.1:8000`. Set `VITE_API_URL` only when the backend is on a different
origin.

Production commands:

```powershell
npm run build
npm run preview
```

## Technology

- React 18 and TypeScript.
- Vite 5.
- React Router 6.
- Tailwind CSS 3.
- TanStack Query for server state.
- Zustand for local UI state.
- Axios for HTTP.
- Framer Motion for interaction and transition animation.
- Lucide React for icons.

## Structure

```text
frontend/
|-- src/
|   |-- components/
|   |   |-- auth/            Authentication controls and OTP/password inputs
|   |   |-- builder/         Workflow shell, navigation, previews, timelines
|   |   |-- common/          Shared feature and metric presentation
|   |   |-- layout/          Public, user, and administrator layouts
|   |   |-- projects/        Project cards, lists, and creation modal
|   |   |-- routes/          Public, protected, and administrator guards
|   |   |-- settings/        Model status and cleanup controls
|   |   |-- stages/          Workflow stage editors and result views
|   |   |-- theme/           Theme synchronization
|   |   `-- ui/              Reusable visual components
|   |-- contexts/
|   |   `-- AuthContext.tsx  Session, user, OTP, and reset actions
|   |-- hooks/               Query hooks for projects, workflow, status, logs
|   |-- pages/
|   |   |-- auth/            Login, register, OTP, forgot/reset password
|   |   |-- admin/           Administrator management screens
|   |   `-- *.tsx            Public and authenticated application screens
|   |-- routes/
|   |   `-- AppRoutes.tsx    Route table
|   |-- services/            Typed API clients
|   |-- stores/              Builder, theme, and toast Zustand stores
|   |-- types/               Shared TypeScript models
|   |-- utils/               Stage and formatting helpers
|   |-- App.tsx
|   |-- index.css
|   `-- main.tsx
|-- index.html
|-- package.json
|-- tailwind.config.ts
|-- vite.config.ts
`-- README.md
```

## Routes

### Public

| Path | Page |
| --- | --- |
| `/` | Landing page |
| `/login` | Login |
| `/register` | Registration |
| `/verify-otp` | Registration or reset OTP verification |
| `/forgot-password` | Request password reset |
| `/reset-password` | Complete password reset |

`PublicRoute` keeps authenticated users out of login and registration screens.

### Authenticated User

These routes render inside `AppLayout`, require `ProtectedRoute`, and are for
normal users. Admin users are redirected back to `/admin` if they open these
paths manually.

| Path | Page |
| --- | --- |
| `/dashboard` | User dashboard |
| `/builder` | Eleven-stage builder |
| `/projects` | Project list |
| `/projects/:id` | Project details |
| `/generated-apps` | Generated application library |
| `/templates` | Starter ideas |
| `/docs` | In-application help |
| `/profile` | Account profile |
| `/settings` | User-visible preferences |

### Administrator

`AdminRoute` requires an authenticated user whose role is `admin`.

| Path | Page |
| --- | --- |
| `/admin` | Administrator overview |
| `/admin/users` | User management |
| `/admin/projects` | All projects |
| `/admin/projects/:id` | Admin project detail view |
| `/admin/generated-apps` | Generated app management |
| `/admin/system` | System and storage status |
| `/admin/models` | Ollama model configuration |
| `/admin/logs` | Platform logs |

`/system` redirects to `/admin/system`.

Admin users see an admin-only sidebar: Console, Users, All Projects, Generated
Apps, Models, System Health, and Logs. Normal builder links such as Dashboard,
Builder, Templates, Docs, Profile, and Settings are hidden in admin mode. This is
intentional so the platform admin experience is a restricted operations console,
not a normal user workspace with one extra link.

## Authentication Flow

`AuthContext` owns the current platform user and exposes:

- `login`
- `logout`
- `register`
- `verifyOtp`
- `resendOtp`
- `forgotPassword`
- `resetPassword`
- `refreshUser`

The canonical token key is `access_token`. `authService.ts` migrates the older
`ai_builder_token` key once and removes it. Axios adds the bearer token to requests.
On a `401`, the API client clears stored tokens and emits `auth:session-expired`.

Registration does not automatically create an administrator account. Administrator
accounts are seeded by the backend configuration or managed by an existing admin.

Default local platform admin for this checkout:

```text
Email: admin@example.com
Password: change_me_admin_password
```

Generated apps have their own demo admin after build and seed:

```text
Email: admin@example.com
Password: Admin1234!
```

## API Services

| File | Responsibility |
| --- | --- |
| `api.ts` | Axios instance, auth header, timeout, errors, health |
| `authService.ts` | Login, registration, OTP, password reset |
| `projectsService.ts` | Project CRUD and artifacts |
| `workflowService.ts` | Workflow stage generation through cleaned spec, requirements, stories, architecture, data model, SRS, UI selection, and post-analysis |
| `buildService.ts` | Build and preview process controls |
| `settingsService.ts` | Model and platform settings |
| `adminService.ts` | Administrator dashboards and management |

The shared Axios timeout is one hour because local model inference and generated
app builds can take a long time. The long workflow stage calls use `timeout: 0`,
so the browser client does not stop Ollama while the backend is still working.
Backend-side stage timeouts still control the real upper limits.

## State Ownership

- `AuthContext`: authenticated user and account operations.
- TanStack Query: remote projects, generation, status, and logs.
- `builderStore`: current project, active stage, and mobile sidebar state.
- `themeStore`: `light`, `dark`, or `system` preference.
- `toastStore`: global feedback messages.
- Component state: local forms, dialogs, and presentation behavior.

Avoid duplicating server data in Zustand. Add remote data through a service and query
hook; reserve stores for cross-screen UI state.

## Theme System

The theme preference is stored as `ai_builder_theme`.

- `light`: force light variables.
- `dark`: force dark variables.
- `system`: follow `prefers-color-scheme`.

`initializeTheme()` runs before React renders. `ThemeController` keeps system changes
synchronized while the application is open.

Theme tokens and global component styles are defined in `src/index.css` and extended
through `tailwind.config.ts`.

## Builder UI

`BuilderPage` composes reusable workflow infrastructure from:

- `StageStepper`
- `StageNavigation`
- `ProgressHeader`
- `PromptEditor`
- `WorkflowPreview`
- `GenerationTimeline`
- `BuildTimeline`

Stage-specific components live in `components/stages/`. They read and update the
project through hooks and typed services rather than calling Axios directly.

### UI Selection Phase

The UI phase is the checkpoint for the generated app's frontend direction. It
should confirm:

- detected app domain, such as clinic, school, restaurant, finance, property, or
  workflow;
- visual identity, colors, fonts, and overall mood;
- separate admin and normal-user dashboard structures;
- navigation per role;
- page presentation style, such as catalog, cards, timeline, board, ledger, or
  admin console.

For normal testing, choose the suggested domain UI when it matches the prompt.
Switch or regenerate only when the detected domain is wrong or the structure feels
too generic. The goal is for future generated apps to look and feel different from
each other, not to reuse one admin-table layout.

The final generated-app frontend is produced by the backend generator as plain
HTML/CSS/JavaScript inside each generated project. The React frontend controls the
builder workflow; it is not copied as the generated app UI.

### Recovery Signals

Project data can include `recovery_diagnosis` when the backend determines that a
failed generated app is caused by upstream context instead of a simple code bug.
The diagnosis can identify:

- `CODE_BUG`: stay in code repair/healing.
- `ARCHITECTURE_MISMATCH`: regenerate architecture and downstream stages.
- `DATA_MODEL_GAP`: regenerate data model and downstream stages.

The backend endpoint for manual recovery is
`POST /api/projects/{project_id}/recover/regenerate-stage`. The frontend type
contract is already present in `types/project.ts`; any future recovery card or
button should use that field rather than guessing from raw error text.

## Model Settings

The admin Models page edits the same values stored in `.tmp/model_settings.json`.
Current recommended defaults:

- Architect model: `llama3.1:8b`.
- Coder model: `qwen2.5-coder:14b`.
- Single-model mode: disabled by default for the stronger PC split-model setup.
- LLM refactor: disabled by default because it is a slower quality pass.
- Runtime healing: enabled by default so generated apps get bounded repair
  attempts after validation failures.

For a weak laptop with only one model installed, temporarily enable
single-model mode from the admin Models page. For the 5070-class GPU test PC,
keep the split setup.

## Component Conventions

- Reusable presentation belongs in `components/ui`.
- Route-level composition belongs in `pages`.
- Backend communication belongs in `services`.
- Query orchestration belongs in `hooks`.
- Shared contracts belong in `types`.
- Global local state belongs in `stores` or a focused context.
- Route authorization belongs in `components/routes`.

Keep pages thin and move repeated loading, empty, error, dialog, badge, and button
patterns into the existing UI components.

## Environment and Proxy

Development proxy configuration in `vite.config.ts`:

```text
/api  -> http://127.0.0.1:8000
/auth -> http://127.0.0.1:8000
```

For a remote backend:

```dotenv
VITE_API_URL=https://api.example.com
```

For same-origin production, leave `VITE_API_URL` empty and let FastAPI serve
`frontend/dist`.

## Verification

Build and type-check:

```powershell
cd frontend
npm run build
```

Run the production bundle locally:

```powershell
npm run preview
```

Check the backend from the browser or terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

If requests fail in development, verify that Vite is on port `5173`, FastAPI is on
port `8000`, and Ollama is on port `11434`.
