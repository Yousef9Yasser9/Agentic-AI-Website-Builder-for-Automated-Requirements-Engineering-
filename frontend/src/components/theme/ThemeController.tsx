import { useEffect } from "react";
import { applyTheme, useThemeStore } from "../../stores/themeStore";

export function ThemeController() {
  const theme = useThemeStore((state) => state.theme);

  useEffect(() => {
    applyTheme(theme);
    if (theme !== "system") return;

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const syncWithSystem = () => applyTheme("system");
    media.addEventListener("change", syncWithSystem);
    return () => media.removeEventListener("change", syncWithSystem);
  }, [theme]);

  return null;
}
