import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Blocks,
  Check,
  CheckCircle2,
  Code2,
  Database,
  FileCheck2,
  GitBranch,
  Layers3,
  Menu,
  Play,
  Rocket,
  Sparkles,
  WandSparkles,
  Workflow,
  X,
} from "lucide-react";
import { useState } from "react";
import { FloatingOrbs } from "../components/common/FloatingOrbs";
import { Reveal } from "../components/common/Reveal";
import { WorkflowPreview } from "../components/builder/WorkflowPreview";
import { Badge } from "../components/ui/Badge";
import { Brand } from "../components/ui/Brand";
import { GlassCard } from "../components/ui/GlassCard";
import { GradientButton } from "../components/ui/GradientButton";
import { WORKFLOW_STAGES } from "../types/workflow";

const howItWorks = [
  { title: "Describe", copy: "Explain the product in plain English, from a quick concept to a detailed brief.", icon: FileCheck2 },
  { title: "Configure", copy: "Review requirements, architecture, data models, and the visual direction.", icon: Blocks },
  { title: "Generate", copy: "Create a complete FastAPI application with auth, data, UI, and tests.", icon: Code2 },
  { title: "Deploy", copy: "Build the environment, start the server, and open the working application.", icon: Rocket },
];

const features = [
  { title: "AI Spec Cleaning", copy: "Turn rough notes into a structured product identity and implementation-ready brief.", icon: WandSparkles },
  { title: "Auto Requirements", copy: "Generate functional and non-functional requirements with priorities and traceability.", icon: FileCheck2 },
  { title: "User Story Generation", copy: "Create role-aware stories and acceptance criteria that stay linked to requirements.", icon: GitBranch },
  { title: "Architecture Design", copy: "Plan pages, modules, roles, API endpoints, and the technical stack before coding.", icon: Blocks },
  { title: "Full Code Generation", copy: "Generate the backend, database, authentication, responsive UI, seed data, and tests.", icon: Code2 },
  { title: "One-Click Runtime", copy: "Build dependencies, initialize data, and launch the generated application locally.", icon: Rocket },
];

const testimonials = [
  { quote: "The staged workflow made the AI feel predictable. I could correct the product thinking before it touched the code.", name: "Maya Chen", role: "Product engineer" },
  { quote: "It gave our team a usable backend, role model, and data structure from one detailed brief. That is a serious head start.", name: "Omar Hassan", role: "Technical founder" },
  { quote: "The checkpoint model is the best part. We can revisit architecture decisions instead of starting the generation over.", name: "Elena Rossi", role: "Software lead" },
];

function HeroPipelineDemo() {
  return (
    <div className="rounded-2xl border border-line bg-black/20 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Live pipeline</span>
        <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[10px] font-bold text-blue-200">Auto running</span>
      </div>
      <svg viewBox="0 0 440 96" className="h-24 w-full overflow-visible" role="img" aria-label="Animated AI build pipeline">
        <defs>
          <linearGradient id="landing-pipeline-gradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="62%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
        </defs>
        <path d="M62 48 H160" className="pipeline-micro-line" stroke="url(#landing-pipeline-gradient)" strokeWidth="5" strokeLinecap="round" fill="none" />
        <path d="M206 48 H304" className="pipeline-micro-line" stroke="url(#landing-pipeline-gradient)" strokeWidth="5" strokeLinecap="round" fill="none" style={{ animationDelay: "0.5s" }} />
        <path d="M350 48 H410" className="pipeline-micro-line" stroke="url(#landing-pipeline-gradient)" strokeWidth="5" strokeLinecap="round" fill="none" style={{ animationDelay: "1s" }} />
        {[
          [36, "Idea"],
          [184, "Plan"],
          [328, "Code"],
          [416, "Live"],
        ].map(([cx, label], index) => (
          <g key={label}>
            <circle cx={Number(cx)} cy="48" r="24" fill="rgba(59,130,246,0.1)" stroke="rgba(148,163,184,0.22)" strokeWidth="1" />
            <circle cx={Number(cx)} cy="48" r="13" className="pipeline-micro-node" fill="url(#landing-pipeline-gradient)" style={{ animationDelay: `${index * 0.45}s` }} />
            <text x={Number(cx)} y="88" textAnchor="middle" className="fill-slate-400 text-[10px] font-semibold">{label}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export function LandingPage() {
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const start = () => navigate("/register");

  return (
    <div className="min-h-screen overflow-hidden bg-ink text-text-primary">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-line bg-ink/80 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-6">
          <Brand />
          <nav className="hidden items-center gap-7 md:flex">
            <a href="#workflow" className="text-sm font-medium text-text-secondary hover:text-white">Workflow</a>
            <a href="#features" className="text-sm font-medium text-text-secondary hover:text-white">Features</a>
            <a href="#stages" className="text-sm font-medium text-text-secondary hover:text-white">Stages</a>
            <Link to="/login" className="text-sm font-semibold text-text-secondary hover:text-white">Sign in</Link>
            <GradientButton size="sm" onClick={start}>Start Building</GradientButton>
          </nav>
          <button type="button" onClick={() => setMobileOpen((open) => !open)} className="rounded-xl p-2 text-text-secondary hover:bg-white/5 hover:text-white md:hidden" aria-label="Toggle navigation">{mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button>
        </div>
        {mobileOpen ? (
          <div className="border-t border-line bg-surface/95 p-5 md:hidden">
            <div className="flex flex-col gap-3">
              <a href="#workflow" onClick={() => setMobileOpen(false)} className="rounded-xl px-3 py-2 text-text-secondary">Workflow</a>
              <a href="#features" onClick={() => setMobileOpen(false)} className="rounded-xl px-3 py-2 text-text-secondary">Features</a>
              <Link to="/login" className="rounded-xl px-3 py-2 text-text-secondary">Sign in</Link>
              <GradientButton onClick={start}>Start Building</GradientButton>
            </div>
          </div>
        ) : null}
      </header>

      <main>
        <section className="relative flex min-h-screen items-center overflow-hidden pb-20 pt-32">
          <div className="grid-bg absolute inset-0 opacity-60 [mask-image:linear-gradient(to_bottom,black,transparent_90%)]" />
          <FloatingOrbs density="rich" />
          <span className="floating-micro absolute left-[7%] top-[24%] hidden h-4 w-4 rounded-full border border-primary/30 bg-primary/15 lg:block" />
          <span className="floating-micro absolute right-[11%] top-[23%] hidden h-5 w-5 rounded-md border border-secondary/30 bg-secondary/15 lg:block" />
          <span className="floating-micro absolute bottom-[18%] left-[46%] hidden h-7 w-7 rounded-full border border-accent/20 lg:block" />
          <span className="floating-micro absolute right-[30%] top-[58%] hidden h-2.5 w-2.5 rounded-full bg-blue-300/50 lg:block" />
          <div className="relative mx-auto grid w-full max-w-7xl items-center gap-14 px-5 sm:px-6 lg:grid-cols-[1.05fr_.95fr]">
            <div className="animate-fade-in-up">
              <Brand showTagline showStagePips className="mb-8 hidden sm:inline-flex" />
              <Badge variant="info"><Sparkles className="h-3.5 w-3.5" /> From idea to running application</Badge>
              <h1 className="mt-6 max-w-4xl text-5xl font-extrabold leading-[1.05] tracking-[-0.04em] text-white sm:text-6xl xl:text-7xl">
                Build Production Apps with AI <span className="gradient-text">In Minutes</span>
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-text-secondary">The 11-stage AI workflow that turns your idea into a complete, deployable web application.</p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <GradientButton size="lg" onClick={start} icon={<Sparkles className="h-5 w-5" />}>Start Building Free</GradientButton>
                <GradientButton size="lg" variant="secondary" onClick={() => document.getElementById("workflow")?.scrollIntoView({ behavior: "smooth" })} icon={<Play className="h-5 w-5" />}>Watch Demo</GradientButton>
              </div>
              <div className="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-sm text-text-secondary">
                {["No credit card", "Local AI workflow", "Checkpointed stages"].map((item) => <span key={item} className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-success" /> {item}</span>)}
              </div>
              <div className="mt-6 flex max-w-md items-center gap-2 rounded-full border border-line bg-surface/70 px-4 py-3 text-xs font-semibold text-text-secondary shadow-depth-1">
                <span className="live-build-dot h-2 w-2 rounded-full bg-primary" />
                <span className="live-build-dot h-2 w-2 rounded-full bg-secondary" />
                <span className="live-build-dot h-2 w-2 rounded-full bg-accent" />
                <span className="live-build-dot h-2 w-2 rounded-full bg-primary" />
                Live build pipeline: idea, plan, design, code
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-xl">
              <div className="absolute -left-5 top-16 z-20 animate-float rounded-xl border border-line bg-surface-2/90 px-4 py-3 shadow-depth-float">
                <p className="text-xs text-text-muted">Builder stages</p>
                <p className="mt-1 text-lg font-bold text-white">11-step flow</p>
              </div>
              <div className="absolute -right-3 bottom-16 z-20 animate-float rounded-xl border border-line bg-surface-2/90 px-4 py-3 shadow-depth-float [animation-delay:800ms]">
                <p className="text-xs text-text-muted">Runtime target</p>
                <p className="mt-1 text-lg font-bold text-emerald-300">Local FastAPI</p>
              </div>
              <div className="glass-card relative overflow-hidden bg-surface/90 p-3 shadow-depth-3">
                <div className="flex items-center justify-between border-b border-line px-3 pb-3">
                  <div className="flex gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-danger/70" /><span className="h-2.5 w-2.5 rounded-full bg-warning/70" /><span className="h-2.5 w-2.5 rounded-full bg-success/70" /></div>
                  <Badge variant="purple">11 AI stages</Badge>
                </div>
                <div className="grid min-h-[430px] grid-cols-[110px_minmax(0,1fr)]">
                  <div className="border-r border-line p-3">
                    <div className="mb-4 h-8 rounded-lg bg-gradient-to-r from-primary/20 to-secondary/20" />
                    <div className="space-y-2">
                      {WORKFLOW_STAGES.slice(0, 7).map((stage, index) => {
                        const active = index === 4;
                        const complete = index < 4;
                        return (
                          <div key={stage.key} className={`flex items-center gap-2 rounded-lg border p-2 ${active ? "border-primary/30 bg-primary/10" : "border-transparent"}`}>
                            <span className={`grid h-5 w-5 place-items-center rounded-full text-[9px] ${complete ? "bg-success/10 text-success" : active ? "bg-primary/15 text-blue-200" : "bg-white/5 text-text-muted"}`}>
                              {complete ? <Check className="h-3 w-3" /> : index + 1}
                            </span>
                            <span className="truncate text-[10px] text-text-secondary">{stage.shortLabel}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  <div className="space-y-4 p-5">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-300">Stage 5</p>
                        <p className="mt-1 text-lg font-bold text-white">Architecture Design</p>
                      </div>
                      <span className="grid h-10 w-10 place-items-center rounded-xl border border-primary/30 bg-primary/10 text-blue-300 shadow-glow"><Blocks className="h-5 w-5" /></span>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      {["Pages", "Roles", "Endpoints", "Modules"].map((item, index) => (
                        <div key={item} className="rounded-xl border border-line bg-white/[0.025] p-3">
                          <p className="text-[10px] text-text-muted">{item}</p>
                          <p className="mt-2 text-xl font-bold text-white">{[8, 3, 24, 6][index]}</p>
                        </div>
                      ))}
                    </div>
                    <div className="rounded-xl border border-line bg-black/25 p-4">
                      <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-text-secondary"><Database className="h-4 w-4 text-blue-300" /> Planned data flow</div>
                      <div className="space-y-2">
                        {[92, 76, 58, 84].map((width) => (
                          <div key={width} className="flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full bg-primary" />
                            <span className="h-2 rounded-full bg-gradient-to-r from-primary/40 to-secondary/30" style={{ width: `${width}%` }} />
                          </div>
                        ))}
                      </div>
                    </div>
                    <HeroPipelineDemo />
                    <button type="button" className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-primary to-secondary py-3 text-xs font-bold text-white shadow-glow"><Sparkles className="h-4 w-4" /> Run Architecture Stage</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="workflow" className="mx-auto max-w-7xl px-5 py-24 sm:px-6">
          <Reveal>
            <div className="mx-auto max-w-2xl text-center">
              <Badge variant="purple">How it works</Badge>
              <h2 className="mt-4 text-3xl font-bold tracking-tight text-white sm:text-5xl">A clear path from concept to code</h2>
              <p className="mt-4 text-text-secondary">Keep the speed of AI without giving up control over product and technical decisions.</p>
            </div>
          </Reveal>
          <Reveal className="mt-10" delay={80}>
            <WorkflowPreview variant="compact" />
          </Reveal>
          <div className="relative mt-14 grid gap-4 lg:grid-cols-4">
            <div className="absolute left-[12%] right-[12%] top-8 hidden border-t border-dashed border-primary/30 lg:block" />
            {howItWorks.map((step, index) => {
              const Icon = step.icon;
              return (
                <Reveal key={step.title} delay={index * 70}>
                  <GlassCard hover padding="md" className="relative h-full">
                    <div className="relative z-10 grid h-16 w-16 place-items-center rounded-2xl border border-primary/20 bg-ink text-blue-300 shadow-glow"><Icon className="h-6 w-6" /></div>
                    <p className="mt-5 text-xs font-bold uppercase tracking-[0.18em] text-text-muted">Step {index + 1}</p>
                    <h3 className="mt-2 text-xl font-bold text-white">{step.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-text-secondary">{step.copy}</p>
                  </GlassCard>
                </Reveal>
              );
            })}
          </div>
        </section>

        <section id="features" className="border-y border-line bg-surface/35 py-24">
          <Reveal className="mx-auto max-w-7xl px-5 sm:px-6">
            <div className="max-w-2xl">
              <Badge variant="info">Platform capabilities</Badge>
              <h2 className="mt-4 text-3xl font-bold text-white sm:text-5xl">Everything required to move from prompt to product</h2>
            </div>
            <div className="mt-12 grid gap-4 md:grid-cols-2">
              {features.map((feature, index) => {
                const Icon = feature.icon;
                return (
                  <Reveal key={feature.title} delay={index * 60}>
                    <GlassCard hover padding="lg" className="group h-full">
                      <span className="grid h-12 w-12 place-items-center rounded-xl border border-primary/20 bg-primary/10 text-blue-300 transition group-hover:scale-105"><Icon className="h-5 w-5" /></span>
                      <h3 className="mt-5 text-xl font-bold text-white">{feature.title}</h3>
                      <p className="mt-2 max-w-xl text-sm leading-6 text-text-secondary">{feature.copy}</p>
                    </GlassCard>
                  </Reveal>
                );
              })}
            </div>
          </Reveal>
        </section>

        <section id="stages" className="mx-auto max-w-7xl px-5 py-24 sm:px-6">
          <Reveal>
            <div className="text-center">
              <Badge variant="purple"><Workflow className="h-3.5 w-3.5" /> Complete workflow</Badge>
              <h2 className="mt-4 text-3xl font-bold text-white sm:text-5xl">The 11-stage intelligent workflow</h2>
            </div>
          </Reveal>
          <Reveal className="mt-12">
            <WorkflowPreview variant="full" />
          </Reveal>
        </section>

        <section className="border-y border-line bg-surface/35 py-24">
          <Reveal className="mx-auto max-w-7xl px-5 sm:px-6">
            <div className="mx-auto max-w-2xl text-center">
              <Badge variant="success">Built for real workflows</Badge>
              <h2 className="mt-4 text-3xl font-bold text-white sm:text-5xl">Teams stay in control</h2>
            </div>
            <div className="mt-12 grid gap-4 lg:grid-cols-3">
              {testimonials.map((item, index) => (
                <Reveal key={item.name} delay={index * 80}>
                  <GlassCard hover padding="lg" className="h-full">
                    <p className="text-base leading-7 text-text-secondary">&quot;{item.quote}&quot;</p>
                    <div className="mt-6 flex items-center gap-3">
                      <span className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-primary to-secondary text-xs font-bold text-white">{item.name.split(" ").map((part) => part[0]).join("")}</span>
                      <div><p className="text-sm font-bold text-white">{item.name}</p><p className="text-xs text-text-muted">{item.role}</p></div>
                    </div>
                  </GlassCard>
                </Reveal>
              ))}
            </div>
          </Reveal>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-24 sm:px-6">
          <Reveal>
            <div className="relative overflow-hidden rounded-3xl border border-primary/25 bg-gradient-to-r from-primary/20 via-secondary/15 to-primary/10 px-6 py-16 text-center shadow-depth-3 sm:px-12">
              <div className="grid-bg absolute inset-0 opacity-40" />
              <FloatingOrbs density="subtle" />
              <div className="relative">
                <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-white/10 text-white shadow-depth-1"><Layers3 className="h-6 w-6" /></span>
                <h2 className="mt-6 text-3xl font-bold text-white sm:text-5xl">Ready to build your next product?</h2>
                <p className="mx-auto mt-4 max-w-2xl text-text-secondary">Create a free account and take your idea through a production-minded AI workflow.</p>
                <GradientButton className="mt-8" size="lg" onClick={start}>Get Started - It&apos;s Free <ArrowRight className="h-5 w-5" /></GradientButton>
              </div>
            </div>
          </Reveal>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-12 sm:px-6 md:grid-cols-[1.5fr_repeat(3,1fr)]">
          <div><Brand /><p className="mt-4 max-w-xs text-sm leading-6 text-text-secondary">A structured AI workflow for planning, generating, and running complete web applications.</p></div>
          <div><p className="text-sm font-bold text-white">Product</p><div className="mt-4 space-y-3 text-sm text-text-secondary"><a href="#features" className="block hover:text-white">Features</a><a href="#stages" className="block hover:text-white">Workflow</a><Link to="/templates" className="block hover:text-white">Templates</Link></div></div>
          <div><p className="text-sm font-bold text-white">Resources</p><div className="mt-4 space-y-3 text-sm text-text-secondary"><Link to="/docs" className="block hover:text-white">Documentation</Link><Link to="/login" className="block hover:text-white">Sign in</Link><Link to="/register" className="block hover:text-white">Create account</Link></div></div>
          <div><p className="text-sm font-bold text-white">Company</p><div className="mt-4 space-y-3 text-sm text-text-secondary"><span className="block">About</span><span className="block">Privacy</span><span className="block">Terms</span></div></div>
        </div>
        <div className="border-t border-line py-5 text-center text-xs text-text-muted">(c) 2026 AI Builder. Built for the graduation project.</div>
      </footer>
    </div>
  );
}
