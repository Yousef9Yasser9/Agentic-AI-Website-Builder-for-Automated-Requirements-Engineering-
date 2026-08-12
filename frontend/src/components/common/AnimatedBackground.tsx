export function AnimatedBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="app-grid-bg absolute inset-0 opacity-80" />
      <div className="absolute inset-x-0 top-0 h-96 bg-[linear-gradient(110deg,rgba(56,189,248,.16),transparent_32%,rgba(52,211,153,.12)_56%,transparent_78%)]" />
      <div className="absolute inset-x-0 bottom-0 h-72 bg-[linear-gradient(35deg,rgba(139,92,246,.16),transparent_42%,rgba(245,158,11,.10))]" />
    </div>
  );
}

