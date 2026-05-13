"use client";

import {
  BarChart3,
  BookOpen,
  FileText,
  FlaskConical,
  Github,
  Network,
  type LucideIcon,
} from "lucide-react";

import MagicBento, { type BentoCardProps } from "@/components/ui/magic-bento";
import { cn } from "@/lib/utils";

import { Section } from "../section";

const CARD_BG = "#0a0a0a";

function buildLabel(label: string, Icon: LucideIcon): React.ReactNode {
  return (
    <span className="flex items-center gap-2 text-gold">
      <Icon className="size-4" strokeWidth={2} />
      {label}
    </span>
  );
}

const features: BentoCardProps[] = [
  {
    color: CARD_BG,
    label: buildLabel("Literature", BookOpen),
    title: "Systematic Search",
    description: "arXiv + Semantic Scholar with auto-clustering",
  },
  {
    color: CARD_BG,
    label: buildLabel("Reproduction", FlaskConical),
    title: "Paper-to-Code",
    description: "Extract method and hparams, run in sandbox, compare metrics",
  },
  {
    color: CARD_BG,
    label: buildLabel("Experiment", BarChart3),
    title: "Design & Analyze",
    description: "Plan ablations, run, generate publication figures",
  },
  {
    color: CARD_BG,
    label: buildLabel("Writing", FileText),
    title: "LaTeX Papers",
    description: "NeurIPS/ICML templates, auto-bibliography, PDF compile",
  },
  {
    color: CARD_BG,
    label: buildLabel("Citation", Network),
    title: "Graph Exploration",
    description: "2-hop citation graph via Semantic Scholar MCP",
  },
  {
    color: CARD_BG,
    label: buildLabel("Open Source", Github),
    title: "MIT License",
    description: "Self-hosted, swappable models, full control",
  },
];

export function WhatsNewSection({ className }: { className?: string }) {
  return (
    <Section
      className={cn("", className)}
      title="What's New in Libra"
      subtitle="Libra brings the full scientific research lifecycle to one agent — from arXiv search to LaTeX paper compilation."
    >
      <div className="flex w-full items-center justify-center">
        <MagicBento data={features} />
      </div>
    </Section>
  );
}
