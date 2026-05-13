import {
  BarChart3,
  BookOpen,
  FileText,
  FlaskConical,
  Microscope,
  Network,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import { Card } from "@/components/ui/card";
import { pathOfThread } from "@/core/threads/utils";
import { cn } from "@/lib/utils";

import { Section } from "../section";

type CaseStudy = {
  threadId: string;
  title: string;
  description: string;
  Icon: LucideIcon;
  /** oklch hue in degrees — keeps cards on the warm-minimal palette */
  hue: number;
};

const CASE_STUDIES: CaseStudy[] = [
  {
    threadId: "7cfa5f8f-a2f8-47ad-acbd-da7137baf990",
    title: "Reproduce GCN on the Cora Dataset",
    description:
      "Parse arXiv:1609.02907, extract the method and hyperparameters, run a 2-layer GCN in the sandbox, and compare accuracy against the paper's reported 81.5%.",
    Icon: FlaskConical,
    hue: 70,
  },
  {
    threadId: "4f3e55ee-f853-43db-bfb3-7d1a411f03cb",
    title: "Systematic Review of Mixture-of-Experts Papers",
    description:
      "Search 50+ MoE papers on arXiv since 2023, cluster by architectural approach, and generate a structured SLR report with citations.",
    Icon: BookOpen,
    hue: 20,
  },
  {
    threadId: "21cfea46-34bd-4aa6-9e1f-3009452fbeb9",
    title: "Write a NeurIPS-Style LaTeX Paper from Notes",
    description:
      "Convert raw experiment notes and result figures into a conference-ready LaTeX paper with auto-compiled bibliography and PDF output.",
    Icon: FileText,
    hue: 130,
  },
  {
    threadId: "ad76c455-5bf9-4335-8517-fc03834ab828",
    title: "Citation Graph for “Attention Is All You Need”",
    description:
      "Use Semantic Scholar MCP to expand the 2-hop influential descendants and visualize the citation tree by year and venue.",
    Icon: Network,
    hue: 240,
  },
  {
    threadId: "d3e5adaf-084c-4dd5-9d29-94f1d6bccd98",
    title: "Exploratory Analysis of the Cora Citation Network",
    description:
      "Compute graph statistics, plot the degree distribution, and identify research community clusters with publication-grade figures.",
    Icon: BarChart3,
    hue: 290,
  },
  {
    threadId: "3823e443-4e2b-4679-b496-a9506eae462b",
    title: "Design an Ablation Study for a Vision Transformer",
    description:
      "Generate a complete ablation matrix, recommend hyperparameter sweeps, execute in the sandbox, and summarise findings.",
    Icon: Microscope,
    hue: 160,
  },
];

export function CaseStudySection({ className }: { className?: string }) {
  return (
    <Section
      className={className}
      title="Case Studies"
      subtitle="See how Libra accelerates the full research lifecycle"
    >
      <div className="container-md mt-8 grid grid-cols-1 gap-4 px-4 md:grid-cols-2 md:px-20 lg:grid-cols-3">
        {CASE_STUDIES.map(({ threadId, title, description, Icon, hue }) => (
          <Link
            key={threadId}
            href={pathOfThread(threadId) + "?mock=true"}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Card className="group/card relative h-64 overflow-hidden">
              {/* Gradient wash — keeps the warm-minimal palette */}
              <div
                className="absolute inset-0 z-0 transition-transform duration-300 group-hover/card:scale-105"
                style={{
                  background: `linear-gradient(135deg, oklch(0.95 0.03 ${hue}) 0%, oklch(0.82 0.06 ${hue}) 100%)`,
                }}
              />
              {/* Centred icon */}
              <div className="pointer-events-none absolute inset-0 z-[1] flex items-center justify-center text-foreground/30 transition-colors duration-300 group-hover/card:text-foreground/60">
                <Icon className="size-16" strokeWidth={1.25} />
              </div>
              {/* Title / description tray — same slide-up reveal as before */}
              <div
                className={cn(
                  "absolute right-0 bottom-0 left-0 z-[2] flex h-full w-full translate-y-[calc(100%-60px)] flex-col items-center",
                  "transition-all duration-300",
                  "group-hover/card:translate-y-[calc(100%-128px)]",
                )}
              >
                <div
                  className="flex w-full flex-col p-4"
                  style={{
                    background:
                      "linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0.85) 100%)",
                  }}
                >
                  <div className="flex flex-col gap-2">
                    <h3 className="flex h-14 items-center text-xl font-bold text-white text-shadow-sm">
                      {title}
                    </h3>
                    <p className="overflow-hidden text-sm text-white/85 text-shadow-sm">
                      {description}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </Section>
  );
}
