import { useState } from "react";
import { BookOpen, Braces, CircleHelp, Lightbulb, Workflow } from "lucide-react";
import { WorkflowPreview } from "../components/builder/WorkflowPreview";
import { Reveal } from "../components/common/Reveal";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Badge } from "../components/ui/Badge";
import { GlassCard } from "../components/ui/GlassCard";
import { PageHeader } from "../components/ui/PageHeader";
import { WORKFLOW_STAGES } from "../types/workflow";

type Section = "getting-started" | "workflow" | "api" | "faq";

const endpoints = [
  ["POST", "/auth/register", "Create a user and send an email verification code."],
  ["POST", "/auth/login", "Return a JWT access token for a verified user."],
  ["GET", "/auth/me", "Load the current authenticated user."],
  ["GET", "/api/projects", "List checkpoints visible to the current user."],
  ["POST", "/api/projects", "Create a checkpoint from a plain-text description."],
  ["POST", "/api/projects/:id/generate/cleaned-spec", "Clean and structure the initial product idea."],
  ["POST", "/api/projects/:id/generate/requirements", "Generate functional and non-functional requirements."],
  ["POST", "/api/projects/:id/generate/code", "Generate the application repository."],
  ["POST", "/api/projects/:id/build", "Build, install, seed, and validate the generated app."],
  ["POST", "/api/projects/:id/start-server", "Start the generated application server."],
];

const quickStart = [
  ["1", "Create a project", "Give the project a clear name and describe users, features, workflows, and rules."],
  ["2", "Review AI stages", "Run each planning stage and inspect its structured output before continuing."],
  ["3", "Choose the UI", "Pick a visual direction and navigation layout for the generated application."],
  ["4", "Generate and build", "Create the repository, build its environment, and start the live server."],
];

const faqs = [
  ["Does the workflow save automatically?", "Yes. Each successful stage writes a checkpoint, so closing the browser does not discard completed work."],
  ["Why is a stage locked?", "Future stages stay locked until their required upstream output exists. This keeps the generated architecture and code internally consistent."],
  ["What happens when Ollama is offline?", "AI stages return a friendly backend error. Existing projects, documentation, and non-AI account features remain available."],
  ["Can I regenerate a stage?", "Yes. Open any completed stage and run it again. Downstream content should be reviewed after changing an upstream decision."],
  ["Where is generated code stored?", "The Output tab and Generated Apps page show the repository path returned by the backend."],
];

export function DocsPage() {
  const [section, setSection] = useState<Section>("getting-started");
  const navigation = [
    { id: "getting-started" as const, label: "Getting Started", icon: BookOpen },
    { id: "workflow" as const, label: "Workflow Guide", icon: Workflow },
    { id: "api" as const, label: "API Reference", icon: Braces },
    { id: "faq" as const, label: "FAQ", icon: CircleHelp },
  ];

  return (
    <PageWrapper>
      <PageHeader title="Documentation" subtitle="Learn the application workflow, understand the backend contract, and get unstuck quickly." />
      <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <GlassCard padding="sm" className="h-fit lg:sticky lg:top-24">
          <nav className="space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSection(item.id)}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition ${section === item.id ? "bg-primary/12 text-blue-200" : "text-text-secondary hover:bg-white/[0.035] hover:text-white"}`}
                >
                  <Icon className="h-4 w-4" /> {item.label}
                </button>
              );
            })}
          </nav>
        </GlassCard>

        <article className="min-w-0">
          {section === "getting-started" ? (
            <div className="space-y-5">
              <Reveal>
                <GlassCard padding="lg">
                  <Badge variant="info">Quick start</Badge>
                  <h2 className="mt-4 text-2xl font-bold text-white">Your first generated application</h2>
                  <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">
                    AI Builder turns a product idea into a sequence of reviewable artifacts. You stay in control of the requirements, architecture, data model, UI direction, code generation, and runtime.
                  </p>
                </GlassCard>
              </Reveal>
              <Reveal delay={80}>
                <WorkflowPreview variant="compact" />
              </Reveal>
              <div className="grid gap-4 sm:grid-cols-2">
                {quickStart.map(([number, title, copy], index) => (
                  <Reveal key={number} delay={index * 60}>
                    <GlassCard hover padding="md" className="h-full">
                      <span className="grid h-9 w-9 place-items-center rounded-xl border border-primary/25 bg-primary/10 font-bold text-blue-200 shadow-depth-1">{number}</span>
                      <h3 className="mt-4 font-bold text-white">{title}</h3>
                      <p className="mt-2 text-sm leading-6 text-text-secondary">{copy}</p>
                    </GlassCard>
                  </Reveal>
                ))}
              </div>
              <div className="rounded-2xl border border-warning/20 bg-warning/10 p-5">
                <p className="flex items-center gap-2 font-semibold text-amber-200"><Lightbulb className="h-5 w-5" /> Better prompts produce better systems</p>
                <p className="mt-2 text-sm leading-6 text-amber-100/70">Include user roles, core entities, important validations, and the main journey a user should complete.</p>
              </div>
            </div>
          ) : null}

          {section === "workflow" ? (
            <div className="space-y-5">
              <Reveal>
                <WorkflowPreview variant="full" />
              </Reveal>
              <div className="grid gap-3">
                {WORKFLOW_STAGES.map((stage, index) => {
                  const Icon = stage.icon;
                  return (
                    <Reveal key={stage.key} delay={index * 45}>
                      <GlassCard hover padding="md">
                        <div className="flex items-start gap-4">
                          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-primary/25 bg-primary/10 text-blue-300 shadow-depth-1"><Icon className="h-5 w-5" /></span>
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-blue-200">Stage {index + 1}</span>
                              <h2 className="font-bold text-white">{stage.label}</h2>
                            </div>
                            <p className="mt-2 text-sm leading-6 text-text-secondary">{stage.description}</p>
                            <p className="mt-3 text-xs font-medium text-text-muted">Completion key: <code className="font-mono text-blue-300">{stage.doneKey}</code></p>
                          </div>
                        </div>
                      </GlassCard>
                    </Reveal>
                  );
                })}
              </div>
            </div>
          ) : null}

          {section === "api" ? (
            <Reveal>
              <GlassCard className="overflow-hidden">
                <div className="border-b border-line p-6">
                  <Badge variant="purple">Backend contract</Badge>
                  <h2 className="mt-4 text-2xl font-bold text-white">Key endpoints</h2>
                  <p className="mt-2 text-sm text-text-secondary">Authenticated requests send the JWT as a Bearer token.</p>
                </div>
                <div className="divide-y divide-line">
                  {endpoints.map(([method, path, description]) => (
                    <div key={`${method}-${path}`} className="grid gap-3 p-5 md:grid-cols-[5rem_minmax(0,1fr)_minmax(15rem,1fr)] md:items-center">
                      <Badge variant={method === "GET" ? "success" : "info"} className="justify-center">{method}</Badge>
                      <code className="overflow-x-auto font-mono text-sm text-white">{path}</code>
                      <p className="text-sm leading-6 text-text-secondary">{description}</p>
                    </div>
                  ))}
                </div>
                <div className="border-t border-line bg-black/20 p-6">
                  <p className="mb-3 text-sm font-semibold text-white">Example authenticated request</p>
                  <pre className="overflow-x-auto rounded-xl bg-black/40 p-4 font-mono text-xs leading-6 text-emerald-300">{`curl http://localhost:8000/api/projects \\\n  -H "Authorization: Bearer <access_token>"`}</pre>
                </div>
              </GlassCard>
            </Reveal>
          ) : null}

          {section === "faq" ? (
            <div className="space-y-3">
              {faqs.map(([question, answer], index) => (
                <Reveal key={question} delay={index * 50}>
                  <details open={index === 0} className="glass-card group p-5">
                    <summary className="cursor-pointer list-none font-bold text-white">{question}</summary>
                    <p className="mt-3 text-sm leading-6 text-text-secondary">{answer}</p>
                  </details>
                </Reveal>
              ))}
            </div>
          ) : null}
        </article>
      </div>
    </PageWrapper>
  );
}
