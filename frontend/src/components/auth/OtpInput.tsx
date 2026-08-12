import { useRef } from "react";

export function OtpInput({
  value,
  onChange,
  hasError = false,
}: {
  value: string;
  onChange: (value: string) => void;
  hasError?: boolean;
}) {
  const refs = useRef<Array<HTMLInputElement | null>>([]);
  const digits = Array.from({ length: 6 }, (_, index) => value[index] || "");

  const setDigit = (index: number, digit: string) => {
    const next = [...digits];
    next[index] = digit.replace(/\D/g, "").slice(-1);
    onChange(next.join(""));
    if (next[index] && index < 5) refs.current[index + 1]?.focus();
  };

  return (
    <div
      className={`grid grid-cols-6 gap-2 ${hasError ? "animate-[shake_.35s_ease-in-out]" : ""}`}
      onPaste={(event) => {
        const pasted = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
        if (pasted) {
          event.preventDefault();
          onChange(pasted);
          refs.current[Math.min(pasted.length, 5)]?.focus();
        }
      }}
    >
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(element) => { refs.current[index] = element; }}
          value={digit}
          onChange={(event) => setDigit(index, event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Backspace" && !digit && index > 0) refs.current[index - 1]?.focus();
            if (event.key === "ArrowLeft" && index > 0) refs.current[index - 1]?.focus();
            if (event.key === "ArrowRight" && index < 5) refs.current[index + 1]?.focus();
          }}
          inputMode="numeric"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          aria-label={`OTP digit ${index + 1}`}
          className={`h-14 min-w-0 rounded-xl border bg-white/[0.035] text-center text-xl font-bold text-white outline-none transition focus:border-primary/70 focus:ring-4 focus:ring-primary/10 ${hasError ? "border-danger/60" : "border-white/10"}`}
          maxLength={1}
        />
      ))}
    </div>
  );
}
