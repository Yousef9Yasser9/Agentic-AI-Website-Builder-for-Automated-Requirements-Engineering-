# AI Website Builder Frontend Handoff For Claude

This document is a complete frontend handoff for the AI Website Builder platform.
It is written so another assistant or developer can modify the frontend safely
without breaking the backend contract, authentication flow, admin/user separation,
or the 11-stage builder workflow.

## Project Purpose

AI Website Builder is a local AI application builder. A user describes a product
idea, then the platform moves through an 11-stage workflow:

1. Description
2. Cleaned Spec
3. Requirements
4. User Stories
5. Architecture
6. Data Model
7. SRS Documentation
8. UI Selection
9. Code Generation
10. Build and Run
11. Preview

The React frontend is the control center for the builder. It does not become the
generated web app. Generated apps are produced separately by the backend generator
under `generated_apps/projects/`.

## Current Frontend Stack

- React 18
- TypeScript
- Vite 5
- React Router 6
- Tailwind CSS 3
- TanStack Query 5
- Zustand
- Axios
- Framer Motion
- Lucide React icons

Main commands from project root:

```powershell
cd .\frontend
npm install
npm run dev
npm run build
npm run preview
```

Local URLs:

- Frontend dev server: `http://127.0.0.1:5173`
- Preview build server: `http://127.0.0.1:4173`
- Backend API expected at: `http://127.0.0.1:8000`

Vite proxies these paths to the backend:

- `/api`
- `/auth`

Config file: `frontend/vite.config.ts`

## Current Source Structure

```text
frontend/
|-- index.html
|-- package.json
|-- tailwind.config.ts
|-- vite.config.ts
|-- src/
|   |-- App.tsx
|   |-- main.tsx
|   |-- index.css
|   |-- routes/
|   |   `-- AppRoutes.tsx
|   |-- contexts/
|   |   `-- AuthContext.tsx
|   |-- services/
|   |   |-- api.ts
|   |   |-- authService.ts
|   |   |-- projectsService.ts
|   |   |-- workflowService.ts
|   |   |-- generationService.ts
|   |   |-- buildService.ts
|   |   |-- settingsService.ts
|   |   `-- adminService.ts
|   |-- hooks/
|   |   |-- useProject.ts
|   |   |-- useWorkflow.ts
|   |   |-- useGenerationLogs.ts
|   |   `-- useOllamaStatus.ts
|   |-- stores/
|   |   |-- builderStore.ts
|   |   |-- themeStore.ts
|   |   `-- toastStore.ts
|   |-- types/
|   |   |-- auth.ts
|   |   |-- project.ts
|   |   |-- workflow.ts
|   |   |-- generation.ts
|   |   `-- settings.ts
|   |-- components/
|   |   |-- auth/
|   |   |-- builder/
|   |   |-- common/
|   |   |-- layout/
|   |   |-- projects/
|   |   |-- routes/
|   |   |-- settings/
|   |   |-- stages/
|   |   |-- theme/
|   |   `-- ui/
|   `-- pages/
|       |-- auth/
|       |-- admin/
|       |-- LandingPage.tsx
|       |-- DashboardPage.tsx
|       |-- BuilderPage.tsx
|       |-- ProjectsPage.tsx
|       |-- ProjectDetailsPage.tsx
|       |-- GeneratedAppsPage.tsx
|       |-- TemplatesPage.tsx
|       |-- DocsPage.tsx
|       |-- ProfilePage.tsx
|       `-- SettingsPage.tsx
```

## Application Entry Points

- `src/main.tsx`: React bootstrapping.
- `src/App.tsx`: application providers and route mounting.
- `src/routes/AppRoutes.tsx`: full route table and route guards.
- `src/index.css`: global design tokens, theme variables, component classes, animations.
- `tailwind.config.ts`: Tailwind token extensions, colors, fonts, shadows, keyframes.

## Routing Model

Routes are grouped into three areas: public, normal authenticated user, and admin.

### Public Routes

| Path | Purpose |
| --- | --- |
| `/` | Landing page |
| `/login` | Login |
| `/register` | Register |
| `/verify-otp` | Verify registration or reset OTP |
| `/forgot-password` | Request reset code |
| `/reset-password` | Reset password |

Public auth routes use `PublicRoute` so authenticated users are redirected away
from login/register pages.

### Normal User Routes

Normal user routes are inside `ProtectedRoute` and `AppLayout`. Admin users are
redirected back to `/admin` if they manually open normal user routes.

| Path | Purpose |
| --- | --- |
| `/dashboard` | User workspace overview |
| `/builder` | 11-stage AI builder workflow |
| `/projects` | Project list and creation |
| `/projects/:id` | Project details and artifacts |
| `/generated-apps` | Generated app runtime controls |
| `/templates` | Prompt/template starters |
| `/docs` | In-app documentation |
| `/profile` | User profile and preferences |
| `/settings` | User settings |

### Admin Routes

Admin routes use `AdminRoute` and require `user.role === "admin"`.

| Path | Purpose |
| --- | --- |
| `/admin` | Admin dashboard |
| `/admin/users` | User management |
| `/admin/projects` | All projects |
| `/admin/projects/:id` | Admin project detail view |
| `/admin/generated-apps` | Generated app management |
| `/admin/system` | System health and cleanup |
| `/admin/models` | Model settings |
| `/admin/logs` | Platform logs |

`/system` redirects to `/admin/system`.

## Layout System

### `AppLayout`

File: `src/components/layout/AppLayout.tsx`

This is the main authenticated shell. It changes navigation depending on role.

Normal users see:

- Dashboard
- Projects
- Builder
- Generated Apps
- Templates
- Docs
- Profile
- Settings

Admins see:

- Console
- Users
- All Projects
- Generated Apps
- Models
- System Health
- Logs

Important constraint: keep admin and normal user workspace visually and
functionally separate. Admin mode should feel like a restricted operations
console, not a normal workspace with one extra admin link.

### Public Layout

The landing page has its own public presentation in `LandingPage.tsx`.
Auth pages use `AuthLayout`.

### Admin Layout

Admin pages use `AdminLayout` and admin-specific services.

## Authentication

Core file: `src/contexts/AuthContext.tsx`

AuthContext owns:

- `user`
- `loading`
- `error`
- `isAuthenticated`
- `isAdmin`
- `login`
- `logout`
- `register`
- `verifyOtp`
- `resendOtp`
- `forgotPassword`
- `resetPassword`
- `refreshUser`

Token storage:

- Current token key: `access_token`
- Older key migrated/removed: `ai_builder_token`

Axios behavior:

- `src/services/api.ts` injects the bearer token.
- On `401`, it removes tokens and dispatches `auth:session-expired`.

Default local platform admin:

```text
Email: admin@example.com
Password: change_me_admin_password
```

Generated apps have a separate demo admin after generation/build:

```text
Email: admin@example.com
Password: Admin1234!
```

Do not confuse platform auth with generated-app auth.

## Backend API Contract Used By Frontend

Base behavior:

- In dev, `VITE_API_URL` is normally empty.
- Vite proxies `/api` and `/auth` to `http://127.0.0.1:8000`.
- `api.ts` has a long timeout because local LLM generation can take a long time.
- Stage generation calls use `{ timeout: 0 }` to avoid browser-side timeout.

Service files:

| File | Responsibility |
| --- | --- |
| `api.ts` | Axios instance, token injection, errors, health |
| `authService.ts` | Login/register/OTP/reset/logout/me |
| `projectsService.ts` | Project list/create/read/delete/stage/plain text/artifact URL |
| `workflowService.ts` | Cleaned spec, requirements, stories, architecture, data model, SRS, UI selection |
| `generationService.ts` | Code generation and logs |
| `buildService.ts` | Build, start server, stop server, server status |
| `settingsService.ts` | Model settings, Ollama status, size report, cleanup |
| `adminService.ts` | Admin stats, users, projects, generated apps, system health, logs |

Important backend endpoints:

```text
GET    /api/health
POST   /auth/login
POST   /auth/register
POST   /auth/verify-otp
POST   /auth/resend-otp
POST   /auth/forgot-password
POST   /auth/reset-password
GET    /auth/me

GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
DELETE /api/projects/{project_id}
POST   /api/projects/{project_id}/stage
POST   /api/projects/{project_id}/plain-text

POST   /api/projects/{project_id}/generate/cleaned-spec
POST   /api/projects/{project_id}/generate/requirements
POST   /api/projects/{project_id}/generate/user-stories
POST   /api/projects/{project_id}/generate/architecture
POST   /api/projects/{project_id}/generate/data-model
POST   /api/projects/{project_id}/generate/srs
POST   /api/projects/{project_id}/ui-selection
POST   /api/projects/{project_id}/generate/code
GET    /api/projects/{project_id}/logs

POST   /api/projects/{project_id}/build
POST   /api/projects/{project_id}/start-server
POST   /api/projects/{project_id}/stop-server
GET    /api/projects/{project_id}/server-status

GET    /api/settings/models
PUT    /api/settings/models
GET    /api/ollama/status
GET    /api/system/size-report
POST   /api/system/cleanup

GET    /api/admin/stats
GET    /api/admin/users
PATCH  /api/admin/users/{user_id}
GET    /api/admin/projects
GET    /api/admin/generated-apps
GET    /api/admin/system/health
GET    /api/admin/logs
```

## Builder Workflow Details

Main page: `src/pages/BuilderPage.tsx`

This page currently contains the important animated circular workflow at the top.
Preserve this concept unless explicitly asked to replace it. The user strongly
prefers the animated, colorful, visual flow over a flat grid of stage cards.

Current builder page structure:

- Top project header
- Animated circular 11-stage timeline
- Left workflow stage navigation
- Center stage-specific content
- Right project overview and progress summary

Workflow metadata file:

- `src/types/workflow.ts`

Stage order and `doneKey` mapping:

| Stage | Key | Done field |
| --- | --- | --- |
| Description | `PLAIN_TEXT` | `plain_text` |
| Cleaned Spec | `CLEANED_SPEC` | `cleaned_spec` |
| Requirements | `REQUIREMENTS` | `requirements` |
| User Stories | `USER_STORIES` | `user_stories` |
| Architecture | `ARCHITECTURE` | `architecture` |
| Data Model | `DATA_MODEL` | `data_model` |
| SRS Documentation | `SRS_DOCUMENTATION` | `srs_document` |
| UI Selection | `UI_SELECTION` | `ui_selection` |
| Code Generation | `CODE_GENERATION` | `tdd_passed` |
| Build and Run | `BUILD_AND_RUN` | `build_done` |
| Preview | `PREVIEW` | `server_pid` |

Stage components:

```text
src/components/stages/PlainTextStage.tsx
src/components/stages/CleanedSpecStage.tsx
src/components/stages/RequirementsStage.tsx
src/components/stages/UserStoriesStage.tsx
src/components/stages/ArchitectureStage.tsx
src/components/stages/DataModelStage.tsx
src/components/stages/SrsDocumentationStage.tsx
src/components/stages/UiSelectionStage.tsx
src/components/stages/CodeGenerationStage.tsx
```

Build and Preview are currently implemented inside `BuilderPage.tsx`.

All stage components receive `StageProps`:

```ts
interface StageProps {
  project?: ProjectState;
  onProjectChange: (project: ProjectState) => void;
  onStageChange: (stage: StageKey) => void;
}
```

## Generated App Frontend vs Platform Frontend

This React frontend is the platform UI.

Generated applications are created by the backend generator, especially:

```text
generated_apps/generator/repo_generator.py
```

Recent engine work added a three-tier generated-app frontend router:

- `shell`: current safe generated-app frontend
- `app`: future bespoke dashboard generated frontend
- `site`: future public-site generated frontend

That generated-app router is not the same as this React frontend. If the task is
"make generated apps have different UI", modify the generator. If the task is
"make the AI Builder platform prettier", modify this React frontend.

## State Management

Use the right state owner:

- Auth/session: `AuthContext`
- Remote server data: TanStack Query
- Builder UI state: `builderStore`
- Theme preference: `themeStore`
- Toast notifications: `toastStore`
- Local forms/dialogs: component state

Avoid copying server data into Zustand unless it is cross-screen UI state.

## Theme And Design System

Global design tokens:

- `src/index.css`
- `tailwind.config.ts`

Fonts:

- Inter
- JetBrains Mono

Core colors:

- `primary`: `#3b82f6`
- `secondary`: `#8b5cf6`
- `accent`: `#06b6d4`
- `success`: `#10b981`
- `warning`: `#f59e0b`
- `danger`: `#ef4444`

CSS variables drive dark/light modes:

```css
--color-ink
--color-surface
--color-surface-2
--color-line
--color-line-bright
--color-text-primary
--color-text-secondary
--color-text-muted
```

Theme preference:

- Stored as `ai_builder_theme`
- Values: `light`, `dark`, `system`
- Implemented in `src/stores/themeStore.ts`
- Synced by `src/components/theme/ThemeController.tsx`

Reusable UI components:

```text
Badge
Brand
CodeBlock
ConfirmDialog
ConfirmModal
EmptyState
ErrorState
GlassCard
GradientButton
JsonViewer
LoadingSpinner
LoadingState
LogPanel
MarkdownPreview
PageHeader
ProgressBar
ProgressRing
StatusBadge
SuccessState
ToastContainer
```

Current visual language:

- Premium dark SaaS look
- Glass cards
- Blue/violet/cyan gradients
- Subtle grid backgrounds
- Floating orbs
- Animated workflow lines
- Rounded panels
- Strong spacing
- Domain/productivity studio tone

Light mode exists and should keep working. Do not hardcode text colors in a way
that breaks `html[data-theme="light"]`.

## Current Important Pages

### `LandingPage.tsx`

Public product page with:

- Hero section
- Animated product pipeline demo
- Floating visual elements
- Feature cards
- Workflow/stage explanation
- Sign in/register calls to action

Improve this if making the product more premium. Keep it conversion-focused.

### `DashboardPage.tsx`

Normal user workspace overview. Should emphasize:

- Current projects
- Recent progress
- Quick start/create project
- Builder health/status

### `BuilderPage.tsx`

Most important user page. Preserve the circular animated 11-stage workflow. It is
part of the desired UX. Improve polish, responsiveness, and stage clarity, but do
not regress it back to flat generic cards.

### `ProjectsPage.tsx` and `ProjectDetailsPage.tsx`

Manage checkpoints and generated artifacts. Project details include overview,
stages, output, and settings tabs.

### `GeneratedAppsPage.tsx`

Manage generated apps and runtime controls. Should clearly show build status,
server status, ports, app links, and docs links.

### `TemplatesPage.tsx`

Starter prompt ideas. It should help users create strong prompts and test the
engine with different app domains.

### `DocsPage.tsx`

In-app documentation. Good place for workflow explanation, API reference, and
FAQ.

### Admin Pages

Admin pages live in `src/pages/admin/`:

```text
AdminDashboardPage.tsx
AdminUsersPage.tsx
AdminProjectsPage.tsx
AdminGeneratedAppsPage.tsx
AdminSystemPage.tsx
AdminModelsPage.tsx
AdminLogsPage.tsx
```

Admin must see only admin navigation in `AppLayout`. Keep normal user links
hidden while in admin mode.

## Modification Goals For Claude

If Claude is asked to improve the frontend, the preferred direction is:

1. Keep the backend API contract unchanged.
2. Keep route guards and admin/user separation unchanged.
3. Preserve the animated circular builder workflow.
4. Make the whole platform feel like a premium AI SaaS product, not a class
   project or generic admin panel.
5. Improve normal user pages, not only admin pages.
6. Improve admin pages so they feel like a restricted operations console.
7. Ensure light/dark/system theme switching works everywhere.
8. Keep responsive behavior strong on laptop and desktop widths.
9. Reuse existing UI components where possible.
10. Avoid rewriting services unless a backend contract actually changed.

Suggested frontend upgrade priorities:

- Redesign `DashboardPage` with stronger product metrics, project progress,
  recent activity, and quick-start cards.
- Polish `BuilderPage` without removing the circular workflow.
- Improve `ProjectsPage` and `ProjectDetailsPage` with clearer cards, artifacts,
  timeline, status, and action hierarchy.
- Improve `GeneratedAppsPage` with better runtime cards and launch controls.
- Improve admin pages with richer operational cards, model/health/status sections,
  and better empty/loading/error states.
- Make the auth pages visually consistent with the premium landing page.
- Audit all pages in light mode.
- Audit mobile and small laptop widths.

## Things Claude Must Not Break

- Do not remove the current route guards.
- Do not show normal user workspace links to admins.
- Do not show admin pages to normal users.
- Do not change backend endpoint paths unless the backend is changed too.
- Do not shorten or remove long generation timeouts.
- Do not remove OTP/password-reset flows.
- Do not remove `access_token` handling.
- Do not flatten the builder workflow into generic cards.
- Do not confuse the React platform frontend with generated-app frontend code.
- Do not put generated-app code inside the React frontend.

## Known Backend/Local Setup Notes

Backend command from project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

Frontend command from project root:

```powershell
cd .\frontend
npm run dev
```

If activation is blocked by PowerShell policy, run the Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

Current local Ollama note from recent checks:

- Installed local model visible: `llama3.1:latest`
- Some saved settings may reference `llama3.1:8b` or `qwen2.5-coder:14b`.
- If live generation fails with "model not found", update model settings or pull
  the missing model.

## Validation Checklist After Frontend Changes

Run from `frontend/`:

```powershell
npm run build
```

Manual checks:

1. `/` landing page renders.
2. `/login`, `/register`, `/verify-otp`, `/forgot-password`, `/reset-password`
   still work visually.
3. Normal user can open `/dashboard`, `/builder`, `/projects`,
   `/generated-apps`, `/templates`, `/docs`, `/profile`, `/settings`.
4. Admin opens `/admin` and sees only admin navigation.
5. Normal user cannot open `/admin`.
6. Admin gets redirected away from normal workspace routes.
7. Builder page keeps the animated circular 11-stage workflow.
8. Light/dark/system theme switching works.
9. Backend offline error is understandable.
10. Long generation requests do not time out in the browser.

## Suggested Prompt To Give Claude

Use this if you want Claude to modify the frontend:

```text
You are modifying the React/Vite/Tailwind frontend of an AI Website Builder
platform. Read frontend/CLAUDE_FRONTEND_HANDOFF.md first and follow its
constraints.

Goal: redesign and improve the frontend across normal user pages, admin pages,
auth pages, landing page, and builder workflow so it feels like a premium AI SaaS
product. Keep backend API contracts, route guards, auth flow, theme system, and
the animated circular 11-stage builder workflow intact.

Do not modify generated_apps/projects. Do not confuse the platform React
frontend with the generated-app frontend engine. After changes, run
cd frontend && npm run build and report the result.
```

