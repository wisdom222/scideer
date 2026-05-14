"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useMemo } from "react";

import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

import { AuroraText } from "../ui/aurora-text";

let waved = false;

/** Inline Libra constellation mark — inline so it inherits `currentColor`. */
function LibraMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 200"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <g
        stroke="currentColor"
        strokeWidth="2"
        opacity="0.5"
        strokeLinecap="round"
      >
        <line x1="118" y1="40" x2="166" y2="86" />
        <line x1="118" y1="40" x2="56" y2="96" />
        <line x1="56" y1="96" x2="166" y2="86" />
        <line x1="56" y1="96" x2="80" y2="166" />
      </g>
      <g fill="currentColor">
        <circle cx="118" cy="40" r="9" />
        <circle cx="166" cy="86" r="5.5" />
        <circle cx="56" cy="96" r="7" />
        <circle cx="80" cy="166" r="6" />
      </g>
    </svg>
  );
}

export function Welcome({
  className,
  mode,
}: {
  className?: string;
  mode?: "ultra" | "pro" | "thinking" | "flash";
}) {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const isSkillMode = searchParams.get("mode") === "skill";
  const isUltra = useMemo(() => mode === "ultra", [mode]);
  const colors = useMemo(() => {
    if (isUltra) {
      return ["#d19e1d", "#e9c665", "#e3a812"];
    }
    return ["var(--color-foreground)"];
  }, [isUltra]);
  useEffect(() => {
    waved = true;
  }, []);
  return (
    <div
      className={cn(
        "mx-auto flex w-full flex-col items-center justify-center gap-3 px-8 py-4 text-center",
        className,
      )}
    >
      {!isSkillMode && (
        <LibraMark
          className={cn(
            "text-foreground/80 size-11",
            !waved ? "animate-wave" : "",
          )}
        />
      )}
      <div className="text-2xl font-bold">
        {isSkillMode ? (
          `✨ ${t.welcome.createYourOwnSkill} ✨`
        ) : (
          <AuroraText colors={colors}>{t.welcome.greeting}</AuroraText>
        )}
      </div>
      {isSkillMode ? (
        <div className="text-muted-foreground text-sm">
          {t.welcome.createYourOwnSkillDescription.includes("\n") ? (
            <pre className="font-sans whitespace-pre">
              {t.welcome.createYourOwnSkillDescription}
            </pre>
          ) : (
            <p>{t.welcome.createYourOwnSkillDescription}</p>
          )}
        </div>
      ) : (
        <p className="text-muted-foreground text-sm">{t.welcome.description}</p>
      )}
    </div>
  );
}
