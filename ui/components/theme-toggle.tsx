"use client";

import { useSyncExternalStore } from "react";
import { MoonIcon, SunIcon } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

const noop = () => () => {};

// One button flips light and dark; the first visit follows the system setting.
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  // The server can't know the theme, so the label waits for the client to avoid a hydration mismatch.
  const mounted = useSyncExternalStore(noop, () => true, () => false);
  const dark = mounted && resolvedTheme === "dark";
  return (
    <Button variant="outline" size="icon" aria-label={dark ? "Switch to light theme" : "Switch to dark theme"} onClick={() => setTheme(dark ? "light" : "dark")}>
      <SunIcon className="dark:hidden" />
      <MoonIcon className="hidden dark:block" />
    </Button>
  );
}
