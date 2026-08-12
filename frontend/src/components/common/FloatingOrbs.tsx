import { clsx } from "clsx";

type FloatingOrbsProps = {
  density?: "subtle" | "rich";
  className?: string;
};

export function FloatingOrbs({ density = "subtle", className }: FloatingOrbsProps) {
  const rich = density === "rich";

  return (
    <div className={clsx("pointer-events-none absolute inset-0 overflow-hidden", className)} aria-hidden="true">
      <span
        className={clsx(
          "absolute rounded-full bg-primary/25 blur-3xl",
          rich ? "-left-24 top-10 h-72 w-72" : "-left-16 top-12 h-48 w-48",
        )}
      />
      <span
        className={clsx(
          "absolute rounded-full bg-secondary/20 blur-3xl",
          rich ? "right-0 top-1/3 h-80 w-80" : "-right-16 bottom-8 h-52 w-52",
        )}
      />
      {rich ? (
        <span className="absolute bottom-0 left-1/3 h-64 w-64 rounded-full bg-cyan-400/10 blur-3xl" />
      ) : null}
    </div>
  );
}
