import { Link } from "react-router-dom";
import { CheckCircle2, Code2, Layers3, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { Brand } from "../ui/Brand";

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
  steps?: { label: string; active: boolean; done: boolean }[];
}

export function AuthLayout({ title, subtitle, children, footer, steps }: AuthLayoutProps) {
  return (
    <div className="grid min-h-screen bg-ink lg:grid-cols-[minmax(0,3fr)_minmax(420px,2fr)]">
      <section className="relative hidden overflow-hidden border-r border-line lg:flex lg:flex-col lg:justify-between lg:p-12 xl:p-16">
        <div className="grid-bg absolute inset-0 opacity-70" />
        <div className="absolute -left-24 top-16 h-80 w-80 rounded-full bg-primary/15 blur-[100px]" />
        <div className="absolute -bottom-24 right-0 h-96 w-96 rounded-full bg-secondary/15 blur-[110px]" />
        <div className="relative z-10">
          <Brand showTagline showStagePips />
          <div className="mt-20 max-w-xl">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-blue-200">
              <Sparkles className="h-3.5 w-3.5" /> Eleven intelligent stages
            </p>
            <h2 className="text-4xl font-extrabold leading-tight tracking-tight text-white xl:text-5xl">
              From rough idea to <span className="gradient-text">working application.</span>
            </h2>
            <p className="mt-5 max-w-lg text-base leading-7 text-text-secondary">
              Plan requirements, shape architecture, generate production code, and keep every decision in one focused workspace.
            </p>
          </div>
          <div className="relative mt-12 h-72 max-w-xl">
            <div className="glass-card absolute left-0 top-8 w-[78%] animate-float p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary/15 text-blue-300"><Code2 className="h-5 w-5" /></span>
                  <div><p className="text-sm font-semibold text-white">Architecture designed</p><p className="text-xs text-text-muted">API, pages, roles, and modules</p></div>
                </div>
                <CheckCircle2 className="h-5 w-5 text-success" />
              </div>
              <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/5"><div className="h-full w-[72%] rounded-full bg-gradient-to-r from-primary to-secondary" /></div>
            </div>
            <div className="glass-card absolute bottom-4 right-0 w-[70%] animate-float p-5 [animation-delay:700ms]">
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-secondary/15 text-violet-300"><Layers3 className="h-5 w-5" /></span>
                <div><p className="text-sm font-semibold text-white">Code generation ready</p><p className="text-xs text-text-muted">All specifications validated</p></div>
              </div>
              <div className="mt-4 grid grid-cols-5 gap-2">{[0, 1, 2, 3, 4].map((item) => <span key={item} className="h-8 rounded-lg border border-white/5 bg-white/[0.035]" />)}</div>
            </div>
          </div>
        </div>
        <div className="relative z-10 max-w-lg border-l-2 border-primary/40 pl-5">
          <p className="text-sm leading-6 text-text-secondary">"The workflow gives every idea a clear path from product thinking to code you can actually run."</p>
          <p className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">Built for focused teams</p>
        </div>
      </section>

      <main className="relative flex min-h-screen items-center justify-center px-5 py-10 sm:px-8">
        <div className="absolute left-5 top-5 lg:hidden"><Brand variant="compact" /></div>
        <div className="w-full max-w-md animate-fade-in-up">
          {steps ? (
            <div className="mb-6 flex items-center justify-center gap-2">
              {steps.map((step, index) => (
                <div key={step.label} className="flex items-center gap-2">
                  <span className={`grid h-7 w-7 place-items-center rounded-full border text-xs font-bold ${step.done ? "border-success/30 bg-success/10 text-success" : step.active ? "border-primary/40 bg-primary/15 text-blue-200" : "border-line bg-white/[0.03] text-text-muted"}`}>
                    {step.done ? <CheckCircle2 className="h-3.5 w-3.5" /> : index + 1}
                  </span>
                  {index < steps.length - 1 ? <span className="h-px w-8 bg-line" /> : null}
                </div>
              ))}
            </div>
          ) : null}
          <div className="glass-card bg-surface/85 p-6 sm:p-8">
            <div className="mb-7">
              <Link to="/" className="mb-6 inline-flex text-xs font-medium text-text-muted transition hover:text-white">Back to AI Builder</Link>
              <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">{title}</h1>
              <p className="mt-2 text-sm leading-6 text-text-secondary">{subtitle}</p>
            </div>
            {children}
          </div>
          {footer ? <div className="mt-6 text-center text-sm text-text-secondary">{footer}</div> : null}
        </div>
      </main>
    </div>
  );
}
