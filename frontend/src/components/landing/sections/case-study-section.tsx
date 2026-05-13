import Link from "next/link";

import { Card } from "@/components/ui/card";
import { pathOfThread } from "@/core/threads/utils";
import { cn } from "@/lib/utils";

import { Section } from "../section";

type ArtProps = { className?: string };

function GraphArt({ className }: ArtProps) {
  return (
    <svg viewBox="0 0 200 200" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <g opacity="0.45">
        <line x1="50" y1="60" x2="100" y2="40" />
        <line x1="50" y1="60" x2="100" y2="100" />
        <line x1="50" y1="60" x2="60" y2="140" />
        <line x1="100" y1="40" x2="150" y2="60" />
        <line x1="100" y1="40" x2="100" y2="100" />
        <line x1="100" y1="100" x2="150" y2="60" />
        <line x1="100" y1="100" x2="60" y2="140" />
        <line x1="100" y1="100" x2="140" y2="140" />
        <line x1="60" y1="140" x2="140" y2="140" />
        <line x1="150" y1="60" x2="140" y2="140" />
      </g>
      <circle cx="50" cy="60" r="5" fill="currentColor" />
      <circle cx="100" cy="40" r="5" fill="currentColor" />
      <circle cx="150" cy="60" r="5" fill="currentColor" />
      <circle cx="100" cy="100" r="6.5" fill="currentColor" />
      <circle cx="60" cy="140" r="5" fill="currentColor" />
      <circle cx="140" cy="140" r="5" fill="currentColor" />
    </svg>
  );
}

function PapersArt({ className }: ArtProps) {
  return (
    <svg viewBox="0 0 200 200" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <rect x="40" y="50" width="80" height="100" rx="3" opacity="0.5" />
      <rect x="60" y="65" width="80" height="100" rx="3" opacity="0.7" />
      <rect x="80" y="80" width="80" height="100" rx="3" fill="currentColor" fillOpacity="0.08" />
      <line x1="90" y1="100" x2="150" y2="100" opacity="0.5" />
      <line x1="90" y1="115" x2="142" y2="115" opacity="0.5" />
      <line x1="90" y1="130" x2="150" y2="130" opacity="0.5" />
      <line x1="90" y1="145" x2="132" y2="145" opacity="0.5" />
      <line x1="90" y1="160" x2="148" y2="160" opacity="0.5" />
    </svg>
  );
}

function PaperSheetArt({ className }: ArtProps) {
  return (
    <svg viewBox="0 0 200 200" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <rect x="50" y="30" width="100" height="140" rx="3" />
      <line x1="65" y1="50" x2="135" y2="50" strokeWidth="3" />
      <line x1="65" y1="70" x2="135" y2="70" opacity="0.5" />
      <line x1="65" y1="80" x2="135" y2="80" opacity="0.5" />
      <line x1="65" y1="90" x2="122" y2="90" opacity="0.5" />
      <line x1="100" y1="105" x2="100" y2="155" opacity="0.3" strokeDasharray="2 2" />
      <line x1="65" y1="115" x2="95" y2="115" opacity="0.5" />
      <line x1="65" y1="125" x2="95" y2="125" opacity="0.5" />
      <line x1="65" y1="135" x2="95" y2="135" opacity="0.5" />
      <line x1="65" y1="145" x2="93" y2="145" opacity="0.5" />
      <line x1="105" y1="115" x2="135" y2="115" opacity="0.5" />
      <line x1="105" y1="125" x2="135" y2="125" opacity="0.5" />
      <line x1="105" y1="135" x2="135" y2="135" opacity="0.5" />
      <line x1="105" y1="145" x2="130" y2="145" opacity="0.5" />
    </svg>
  );
}

function CitationTreeArt({ className }: ArtProps) {
  return (
    <svg viewBox="0 0 200 200" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <g opacity="0.45">
        <line x1="100" y1="50" x2="50" y2="100" />
        <line x1="100" y1="50" x2="100" y2="100" />
        <line x1="100" y1="50" x2="150" y2="100" />
        <line x1="50" y1="100" x2="30" y2="150" />
        <line x1="50" y1="100" x2="65" y2="150" />
        <line x1="100" y1="100" x2="85" y2="150" />
        <line x1="100" y1="100" x2="115" y2="150" />
        <line x1="150" y1="100" x2="135" y2="150" />
        <line x1="150" y1="100" x2="170" y2="150" />
      </g>
      <circle cx="100" cy="50" r="7" fill="currentColor" />
      <circle cx="50" cy="100" r="5" fill="currentColor" />
      <circle cx="100" cy="100" r="5" fill="currentColor" />
      <circle cx="150" cy="100" r="5" fill="currentColor" />
      <circle cx="30" cy="150" r="3.5" fill="currentColor" />
      <circle cx="65" cy="150" r="3.5" fill="currentColor" />
      <circle cx="85" cy="150" r="3.5" fill="currentColor" />
      <circle cx="115" cy="150" r="3.5" fill="currentColor" />
      <circle cx="135" cy="150" r="3.5" fill="currentColor" />
      <circle cx="170" cy="150" r="3.5" fill="currentColor" />
    </svg>
  );
}

function BarChartArt({ className }: ArtProps) {
  return (
    <svg viewBox="0 0 200 200" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <line x1="50" y1="160" x2="160" y2="160" strokeWidth="2" />
      <line x1="50" y1="40" x2="50" y2="160" strokeWidth="2" />
      <rect x="62" y="100" width="14" height="60" fill="currentColor" fillOpacity="0.45" />
      <rect x="82" y="80" width="14" height="80" fill="currentColor" fillOpacity="0.6" />
      <rect x="102" y="55" width="14" height="105" fill="currentColor" fillOpacity="0.8" />
      <rect x="122" y="90" width="14" height="70" fill="currentColor" fillOpacity="0.6" />
      <rect x="142" y="115" width="14" height="45" fill="currentColor" fillOpacity="0.45" />
    </svg>
  );
}

function HeatmapArt({ className }: ArtProps) {
  return (
    <svg viewBox="0 0 200 200" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <rect x="50" y="50" width="100" height="100" />
      <line x1="50" y1="83.3" x2="150" y2="83.3" />
      <line x1="50" y1="116.6" x2="150" y2="116.6" />
      <line x1="83.3" y1="50" x2="83.3" y2="150" />
      <line x1="116.6" y1="50" x2="116.6" y2="150" />
      <rect x="51" y="51" width="31.3" height="31.3" fill="currentColor" fillOpacity="0.25" />
      <rect x="84.3" y="51" width="31.3" height="31.3" fill="currentColor" fillOpacity="0.55" />
      <rect x="117.6" y="51" width="31.3" height="31.3" fill="currentColor" fillOpacity="0.4" />
      <rect x="51" y="84.3" width="31.3" height="31.3" fill="currentColor" fillOpacity="0.55" />
      <rect x="84.3" y="84.3" width="31.3" height="31.3" fill="currentColor" fillOpacity="0.85" />
      <rect x="117.6" y="84.3" width="31.3" height="31.3" fill="currentColor" fillOpacity="0.6" />
      <rect x="51" y="117.6" width="31.3" height="31.3" fill="currentColor" fillOpacity="0.4" />
      <rect x="84.3" y="117.6" width="31.3" height="31.3" fill="currentColor" fillOpacity="0.6" />
      <rect x="117.6" y="117.6" width="31.3" height="31.3" fill="currentColor" fillOpacity="0.3" />
    </svg>
  );
}

type CaseStudy = {
  threadId: string;
  title: string;
  description: string;
  Art: React.ComponentType<{ className?: string }>;
  /** oklch hue in degrees — keeps cards on the warm-minimal palette */
  hue: number;
};

const CASE_STUDIES: CaseStudy[] = [
  {
    threadId: "7cfa5f8f-a2f8-47ad-acbd-da7137baf990",
    title: "Reproduce GCN on the Cora Dataset",
    description:
      "Parse arXiv:1609.02907, extract the method and hyperparameters, run a 2-layer GCN in the sandbox, and compare accuracy against the paper's reported 81.5%.",
    Art: GraphArt,
    hue: 70,
  },
  {
    threadId: "4f3e55ee-f853-43db-bfb3-7d1a411f03cb",
    title: "Systematic Review of Mixture-of-Experts Papers",
    description:
      "Search 50+ MoE papers on arXiv since 2023, cluster by architectural approach, and generate a structured SLR report with citations.",
    Art: PapersArt,
    hue: 20,
  },
  {
    threadId: "21cfea46-34bd-4aa6-9e1f-3009452fbeb9",
    title: "Write a NeurIPS-Style LaTeX Paper from Notes",
    description:
      "Convert raw experiment notes and result figures into a conference-ready LaTeX paper with auto-compiled bibliography and PDF output.",
    Art: PaperSheetArt,
    hue: 130,
  },
  {
    threadId: "ad76c455-5bf9-4335-8517-fc03834ab828",
    title: "Citation Graph for “Attention Is All You Need”",
    description:
      "Use Semantic Scholar MCP to expand the 2-hop influential descendants and visualize the citation tree by year and venue.",
    Art: CitationTreeArt,
    hue: 240,
  },
  {
    threadId: "d3e5adaf-084c-4dd5-9d29-94f1d6bccd98",
    title: "Exploratory Analysis of the Cora Citation Network",
    description:
      "Compute graph statistics, plot the degree distribution, and identify research community clusters with publication-grade figures.",
    Art: BarChartArt,
    hue: 290,
  },
  {
    threadId: "3823e443-4e2b-4679-b496-a9506eae462b",
    title: "Design an Ablation Study for a Vision Transformer",
    description:
      "Generate a complete ablation matrix, recommend hyperparameter sweeps, execute in the sandbox, and summarise findings.",
    Art: HeatmapArt,
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
      <div className="container-md mt-8 grid grid-cols-1 gap-4 px-4 md:grid-cols-2 md:px-8 lg:grid-cols-3">
        {CASE_STUDIES.map(({ threadId, title, description, Art, hue }) => (
          <Link
            key={threadId}
            href={pathOfThread(threadId) + "?mock=true"}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Card className="group/card relative aspect-square overflow-hidden">
              {/* Gradient wash — keeps the warm-minimal palette */}
              <div
                className="absolute inset-0 z-0 transition-transform duration-300 group-hover/card:scale-105"
                style={{
                  background: `linear-gradient(135deg, oklch(0.95 0.03 ${hue}) 0%, oklch(0.82 0.06 ${hue}) 100%)`,
                }}
              />
              {/* Centred themed art */}
              <div className="pointer-events-none absolute inset-0 z-[1] flex items-center justify-center transition-colors duration-300">
                <Art className="size-1/2 text-foreground/30 group-hover/card:text-foreground/60 transition-colors duration-300" />
              </div>
              {/* Title / description tray — same slide-up reveal as before */}
              <div
                className={cn(
                  "absolute right-0 bottom-0 left-0 z-[2] flex h-full w-full translate-y-[calc(100%-76px)] flex-col items-center",
                  "transition-all duration-300",
                  "group-hover/card:translate-y-[calc(100%-152px)]",
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
                    <h3 className="text-lg font-bold leading-snug text-white text-shadow-sm line-clamp-2">
                      {title}
                    </h3>
                    <p className="overflow-hidden text-sm text-white/85 text-shadow-sm line-clamp-3">
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
