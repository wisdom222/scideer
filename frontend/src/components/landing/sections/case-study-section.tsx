import Link from "next/link";

import { Card } from "@/components/ui/card";
import { pathOfThread } from "@/core/threads/utils";
import { cn } from "@/lib/utils";

import { Section } from "../section";

type ArtProps = { className?: string };

/* ------------------------------------------------------------------ *
 * Full-colour case-study illustrations.
 * Each fills the card (viewBox 0 0 400 400) and carries its own
 * gradient background — no external assets, no network, no AI raster.
 * Gradient / filter ids are namespaced per illustration to avoid
 * collisions when all six render on the same page.
 * ------------------------------------------------------------------ */

function GcnArt({ className }: ArtProps) {
  // Layered graph-convolution network: a small input graph feeding two
  // GCN layers into an output layer.
  const inputGraph = [
    { x: 70, y: 150 },
    { x: 50, y: 230 },
    { x: 110, y: 290 },
    { x: 120, y: 110 },
  ];
  const inputEdges = [
    { x1: 70, y1: 150, x2: 50, y2: 230 },
    { x1: 70, y1: 150, x2: 120, y2: 110 },
    { x1: 50, y1: 230, x2: 110, y2: 290 },
    { x1: 70, y1: 150, x2: 110, y2: 290 },
  ];
  const hidden = [110, 165, 220, 275, 330];
  const output = [150, 220, 290];
  return (
    <svg viewBox="0 0 400 400" className={className} fill="none">
      <defs>
        <linearGradient id="gcn-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#1e1b4b" />
          <stop offset="1" stopColor="#312e81" />
        </linearGradient>
        <radialGradient id="gcn-node" cx="0.35" cy="0.35" r="0.8">
          <stop offset="0" stopColor="#e0e7ff" />
          <stop offset="1" stopColor="#818cf8" />
        </radialGradient>
      </defs>
      <rect width="400" height="400" fill="url(#gcn-bg)" />
      {/* edges: input graph */}
      <g stroke="#6366f1" strokeWidth="2" opacity="0.7">
        {inputEdges.map((e, i) => (
          <line key={i} x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2} />
        ))}
      </g>
      {/* edges: input graph -> hidden layer */}
      <g stroke="#4f46e5" strokeWidth="1.5" opacity="0.45">
        {inputGraph.map((n, i) =>
          hidden.map((hy, j) => (
            <line key={`${i}-${j}`} x1={n.x} y1={n.y} x2={210} y2={hy} />
          )),
        )}
      </g>
      {/* edges: hidden -> output */}
      <g stroke="#6366f1" strokeWidth="1.5" opacity="0.55">
        {hidden.map((hy, i) =>
          output.map((oy, j) => (
            <line key={`${i}-${j}`} x1={210} y1={hy} x2={330} y2={oy} />
          )),
        )}
      </g>
      {/* input graph nodes */}
      <g>
        {inputGraph.map((n, i) => (
          <circle key={i} cx={n.x} cy={n.y} r="13" fill="url(#gcn-node)" />
        ))}
      </g>
      {/* hidden layer */}
      <g>
        {hidden.map((hy, i) => (
          <circle key={i} cx={210} cy={hy} r="15" fill="#a5b4fc" />
        ))}
      </g>
      {/* output layer */}
      <g>
        {output.map((oy, i) => (
          <circle key={i} cx={330} cy={oy} r="17" fill="#c4b5fd" />
        ))}
      </g>
    </svg>
  );
}

function MoeArt({ className }: ArtProps) {
  // Fanned stack of papers feeding a router hub that dispatches to experts.
  const experts = [90, 170, 250, 330];
  return (
    <svg viewBox="0 0 400 400" className={className} fill="none">
      <defs>
        <linearGradient id="moe-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#451a03" />
          <stop offset="1" stopColor="#78350f" />
        </linearGradient>
      </defs>
      <rect width="400" height="400" fill="url(#moe-bg)" />
      {/* fanned papers */}
      <g>
        <rect
          x="40"
          y="120"
          width="110"
          height="150"
          rx="8"
          fill="#fde68a"
          transform="rotate(-14 95 195)"
        />
        <rect
          x="50"
          y="115"
          width="110"
          height="150"
          rx="8"
          fill="#fcd34d"
          transform="rotate(-4 105 190)"
        />
        <rect x="60" y="110" width="110" height="150" rx="8" fill="#fbbf24" />
        <g stroke="#92400e" strokeWidth="3" strokeLinecap="round" opacity="0.6">
          <line x1="78" y1="135" x2="152" y2="135" />
          <line x1="78" y1="152" x2="152" y2="152" />
          <line x1="78" y1="169" x2="138" y2="169" />
        </g>
      </g>
      {/* router hub */}
      <line
        x1="170"
        y1="185"
        x2="235"
        y2="200"
        stroke="#f59e0b"
        strokeWidth="3"
      />
      <circle cx="255" cy="200" r="26" fill="#f59e0b" />
      <circle cx="255" cy="200" r="26" fill="none" stroke="#fef3c7" strokeWidth="2" />
      {/* router -> experts */}
      <g stroke="#fbbf24" strokeWidth="2.5" opacity="0.8">
        {experts.map((ey, i) => (
          <line key={i} x1="281" y1="200" x2="330" y2={ey} />
        ))}
      </g>
      {/* expert boxes */}
      <g>
        {experts.map((ey, i) => (
          <rect
            key={i}
            x="330"
            y={ey - 22}
            width="44"
            height="44"
            rx="8"
            fill={i === 1 ? "#fde68a" : "#d97706"}
            stroke="#fef3c7"
            strokeWidth="2"
          />
        ))}
      </g>
    </svg>
  );
}

function PaperArt({ className }: ArtProps) {
  // A conference-style document page: title, two text columns, a formula
  // block and an embedded result figure.
  const colA = [148, 162, 176, 190, 204, 218, 232];
  const colB = [288, 302, 316, 330, 344];
  return (
    <svg viewBox="0 0 400 400" className={className} fill="none">
      <defs>
        <linearGradient id="paper-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#042f2e" />
          <stop offset="1" stopColor="#134e4a" />
        </linearGradient>
      </defs>
      <rect width="400" height="400" fill="url(#paper-bg)" />
      {/* page */}
      <rect
        x="90"
        y="50"
        width="220"
        height="300"
        rx="6"
        fill="#f0fdfa"
        stroke="#5eead4"
        strokeWidth="2"
      />
      {/* title */}
      <rect x="120" y="74" width="160" height="10" rx="5" fill="#0f766e" />
      <rect x="150" y="92" width="100" height="6" rx="3" fill="#14b8a6" />
      {/* left column text */}
      <g>
        {colA.map((y, i) => (
          <rect
            key={i}
            x="110"
            y={y}
            width={i === colA.length - 1 ? 50 : 80}
            height="5"
            rx="2.5"
            fill="#99f6e4"
          />
        ))}
      </g>
      {/* formula block */}
      <rect
        x="110"
        y="250"
        width="80"
        height="40"
        rx="4"
        fill="#ccfbf1"
        stroke="#2dd4bf"
        strokeWidth="1.5"
      />
      <rect x="120" y="262" width="60" height="6" rx="3" fill="#0d9488" />
      <rect x="120" y="274" width="42" height="6" rx="3" fill="#0d9488" />
      {/* right column text */}
      <g>
        {colB.map((y, i) => (
          <rect
            key={i}
            x="210"
            y={y}
            width={i === colB.length - 1 ? 48 : 80}
            height="5"
            rx="2.5"
            fill="#99f6e4"
          />
        ))}
      </g>
      {/* embedded figure: mini bar chart */}
      <rect
        x="210"
        y="148"
        width="80"
        height="64"
        rx="4"
        fill="#042f2e"
        opacity="0.06"
      />
      <line x1="218" y1="204" x2="282" y2="204" stroke="#0d9488" strokeWidth="2" />
      <line x1="218" y1="156" x2="218" y2="204" stroke="#0d9488" strokeWidth="2" />
      <rect x="226" y="184" width="11" height="20" fill="#14b8a6" />
      <rect x="242" y="170" width="11" height="34" fill="#0d9488" />
      <rect x="258" y="160" width="11" height="44" fill="#2dd4bf" />
    </svg>
  );
}

function CitationGraphArt({ className }: ArtProps) {
  // Radial multi-hop citation network: a seed paper, a ring of direct
  // citations, and an outer ring of second-hop descendants.
  const cx = 200;
  const cy = 200;
  const ring1 = Array.from({ length: 6 }, (_, i) => {
    const a = (i / 6) * Math.PI * 2 - Math.PI / 2;
    return { x: cx + Math.cos(a) * 78, y: cy + Math.sin(a) * 78, a };
  });
  const ring2 = Array.from({ length: 12 }, (_, i) => {
    const a = (i / 12) * Math.PI * 2;
    return { x: cx + Math.cos(a) * 150, y: cy + Math.sin(a) * 150, a };
  });
  return (
    <svg viewBox="0 0 400 400" className={className} fill="none">
      <defs>
        <linearGradient id="cite-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#172554" />
          <stop offset="1" stopColor="#1e3a8a" />
        </linearGradient>
        <radialGradient id="cite-seed" cx="0.35" cy="0.35" r="0.8">
          <stop offset="0" stopColor="#dbeafe" />
          <stop offset="1" stopColor="#3b82f6" />
        </radialGradient>
      </defs>
      <rect width="400" height="400" fill="url(#cite-bg)" />
      {/* seed -> ring1 */}
      <g stroke="#2563eb" strokeWidth="2" opacity="0.8">
        {ring1.map((n, i) => (
          <line key={i} x1={cx} y1={cy} x2={n.x} y2={n.y} />
        ))}
      </g>
      {/* ring1 -> ring2 */}
      <g stroke="#3b82f6" strokeWidth="1.5" opacity="0.4">
        {ring2.map((n, i) => {
          const p = ring1[Math.floor(i / 2)];
          if (!p) return null;
          return <line key={i} x1={p.x} y1={p.y} x2={n.x} y2={n.y} />;
        })}
      </g>
      {/* ring2 nodes */}
      <g>
        {ring2.map((n, i) => (
          <circle key={i} cx={n.x} cy={n.y} r="9" fill="#60a5fa" />
        ))}
      </g>
      {/* ring1 nodes */}
      <g>
        {ring1.map((n, i) => (
          <circle key={i} cx={n.x} cy={n.y} r="14" fill="#93c5fd" />
        ))}
      </g>
      {/* seed node */}
      <circle cx={cx} cy={cy} r="24" fill="url(#cite-seed)" />
    </svg>
  );
}

function CoraAnalysisArt({ className }: ArtProps) {
  // Exploratory analysis: a degree-distribution histogram with an overlaid
  // power-law decay curve, plus a scattered community cluster.
  const bars = [
    { x: 70, h: 150 },
    { x: 104, h: 110 },
    { x: 138, h: 78 },
    { x: 172, h: 54 },
    { x: 206, h: 36 },
    { x: 240, h: 22 },
  ];
  const baseY = 300;
  const scatter = [
    [300, 90],
    [330, 110],
    [318, 140],
    [350, 130],
    [305, 160],
    [340, 170],
    [365, 95],
    [288, 120],
  ];
  return (
    <svg viewBox="0 0 400 400" className={className} fill="none">
      <defs>
        <linearGradient id="cora-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#3b0764" />
          <stop offset="1" stopColor="#581c87" />
        </linearGradient>
      </defs>
      <rect width="400" height="400" fill="url(#cora-bg)" />
      {/* axes */}
      <line
        x1="58"
        y1={baseY}
        x2="270"
        y2={baseY}
        stroke="#e9d5ff"
        strokeWidth="2.5"
      />
      <line x1="58" y1="120" x2="58" y2={baseY} stroke="#e9d5ff" strokeWidth="2.5" />
      {/* bars */}
      <g>
        {bars.map((b, i) => (
          <rect
            key={i}
            x={b.x}
            y={baseY - b.h}
            width="26"
            height={b.h}
            rx="3"
            fill={i % 2 === 0 ? "#c084fc" : "#d8b4fe"}
          />
        ))}
      </g>
      {/* power-law decay curve */}
      <path
        d="M83 138 C 120 200, 150 250, 200 275 S 260 296, 266 298"
        stroke="#f0abfc"
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
      />
      {/* community scatter cluster */}
      <g>
        {scatter.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="9" fill="#e9d5ff" opacity="0.9" />
        ))}
        <circle cx="325" cy="130" r="52" fill="none" stroke="#f0abfc" strokeWidth="2" strokeDasharray="5 6" opacity="0.7" />
      </g>
    </svg>
  );
}

function VitAblationArt({ className }: ArtProps) {
  // Ablation study: an attention-style heatmap grid with varying cell
  // intensities, framed by axis ticks.
  const n = 5;
  const cell = 48;
  const ox = 110;
  const oy = 90;
  const intensity = [
    [0.25, 0.45, 0.8, 0.5, 0.3],
    [0.4, 0.7, 0.95, 0.65, 0.35],
    [0.55, 0.85, 1, 0.75, 0.45],
    [0.35, 0.6, 0.8, 0.9, 0.5],
    [0.2, 0.4, 0.55, 0.6, 0.85],
  ];
  return (
    <svg viewBox="0 0 400 400" className={className} fill="none">
      <defs>
        <linearGradient id="vit-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#083344" />
          <stop offset="1" stopColor="#155e75" />
        </linearGradient>
      </defs>
      <rect width="400" height="400" fill="url(#vit-bg)" />
      {/* heatmap cells */}
      <g>
        {intensity.flatMap((row, r) =>
          row.map((v, c) => (
            <rect
              key={`${r}-${c}`}
              x={ox + c * cell}
              y={oy + r * cell}
              width={cell - 5}
              height={cell - 5}
              rx="4"
              fill="#22d3ee"
              fillOpacity={v}
            />
          )),
        )}
      </g>
      {/* grid frame */}
      <rect
        x={ox - 4}
        y={oy - 4}
        width={n * cell}
        height={n * cell}
        rx="6"
        fill="none"
        stroke="#a5f3fc"
        strokeWidth="2"
      />
      {/* axis ticks */}
      <g stroke="#67e8f9" strokeWidth="3" strokeLinecap="round">
        {Array.from({ length: n }, (_, i) => (
          <line
            key={`x${i}`}
            x1={ox + i * cell + (cell - 5) / 2}
            y1={oy + n * cell + 6}
            x2={ox + i * cell + (cell - 5) / 2}
            y2={oy + n * cell + 18}
          />
        ))}
        {Array.from({ length: n }, (_, i) => (
          <line
            key={`y${i}`}
            x1={ox - 18}
            y1={oy + i * cell + (cell - 5) / 2}
            x2={ox - 6}
            y2={oy + i * cell + (cell - 5) / 2}
          />
        ))}
      </g>
    </svg>
  );
}

type CaseStudy = {
  threadId: string;
  title: string;
  description: string;
  Art: React.ComponentType<{ className?: string }>;
};

const CASE_STUDIES: CaseStudy[] = [
  {
    threadId: "7cfa5f8f-a2f8-47ad-acbd-da7137baf990",
    title: "Reproduce GCN on the Cora Dataset",
    description:
      "Parse arXiv:1609.02907, extract the method and hyperparameters, run a 2-layer GCN in the sandbox, and compare accuracy against the paper's reported 81.5%.",
    Art: GcnArt,
  },
  {
    threadId: "4f3e55ee-f853-43db-bfb3-7d1a411f03cb",
    title: "Systematic Review of Mixture-of-Experts Papers",
    description:
      "Search 50+ MoE papers on arXiv since 2023, cluster by architectural approach, and generate a structured SLR report with citations.",
    Art: MoeArt,
  },
  {
    threadId: "21cfea46-34bd-4aa6-9e1f-3009452fbeb9",
    title: "Write a NeurIPS-Style LaTeX Paper from Notes",
    description:
      "Convert raw experiment notes and result figures into a conference-ready LaTeX paper with auto-compiled bibliography and PDF output.",
    Art: PaperArt,
  },
  {
    threadId: "ad76c455-5bf9-4335-8517-fc03834ab828",
    title: "Citation Graph for “Attention Is All You Need”",
    description:
      "Use Semantic Scholar MCP to expand the 2-hop influential descendants and visualize the citation tree by year and venue.",
    Art: CitationGraphArt,
  },
  {
    threadId: "d3e5adaf-084c-4dd5-9d29-94f1d6bccd98",
    title: "Exploratory Analysis of the Cora Citation Network",
    description:
      "Compute graph statistics, plot the degree distribution, and identify research community clusters with publication-grade figures.",
    Art: CoraAnalysisArt,
  },
  {
    threadId: "3823e443-4e2b-4679-b496-a9506eae462b",
    title: "Design an Ablation Study for a Vision Transformer",
    description:
      "Generate a complete ablation matrix, recommend hyperparameter sweeps, execute in the sandbox, and summarise findings.",
    Art: VitAblationArt,
  },
];

export function CaseStudySection({ className }: { className?: string }) {
  return (
    <Section
      className={className}
      title="Case Studies"
      subtitle="See how Libra accelerates the full research lifecycle"
    >
      <div className="container-md mx-auto mt-8 grid grid-cols-1 gap-6 px-4 md:grid-cols-2 md:px-8 lg:grid-cols-3">
        {CASE_STUDIES.map(({ threadId, title, description, Art }) => (
          <Link
            key={threadId}
            href={pathOfThread(threadId) + "?mock=true"}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Card className="group/card relative aspect-square overflow-hidden">
              {/* Full-colour themed illustration fills the card */}
              <div className="pointer-events-none absolute inset-0 z-0 transition-transform duration-300 group-hover/card:scale-105">
                <Art className="size-full" />
              </div>
              {/* Bottom tray — title always visible, description reveals on hover */}
              <div
                className="absolute right-0 bottom-0 left-0 z-[2] flex flex-col gap-2 p-5"
                style={{
                  background:
                    "linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 0.9) 60%)",
                }}
              >
                <h3 className="text-lg font-bold leading-snug text-white text-shadow-sm line-clamp-2">
                  {title}
                </h3>
                <p
                  className={cn(
                    "max-h-0 overflow-hidden text-sm text-white/85 opacity-0 text-shadow-sm",
                    "transition-all duration-300",
                    "group-hover/card:max-h-32 group-hover/card:opacity-100",
                  )}
                >
                  {description}
                </p>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </Section>
  );
}
