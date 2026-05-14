import Link from "next/link";

import { Card } from "@/components/ui/card";
import { pathOfThread } from "@/core/threads/utils";

import { Section } from "../section";

type ArtProps = { className?: string };

/* ------------------------------------------------------------------ *
 * Case-study illustrations — cohesive tech aesthetic.
 * Each is a self-contained 400×240 SVG with a dark tech-gradient
 * background and glowing accents. Gradient / filter ids are
 * namespaced per illustration to avoid collisions on the page.
 * ------------------------------------------------------------------ */

function GcnArt({ className }: ArtProps) {
  // Layered graph-convolution network: input graph → 2 hidden layers → output.
  const inputNodes = [
    { x: 54, y: 90 },
    { x: 38, y: 150 },
    { x: 92, y: 70 },
    { x: 88, y: 168 },
  ];
  const inputEdges: [number, number][] = [
    [0, 1],
    [0, 2],
    [0, 3],
    [1, 3],
    [2, 3],
  ];
  const layer1 = [54, 100, 146, 192];
  const layer2 = [62, 108, 154, 200];
  const output = [86, 130, 174];
  return (
    <svg
      viewBox="0 0 400 240"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      role="img"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="gcn-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#161335" />
          <stop offset="1" stopColor="#2a2160" />
        </linearGradient>
        <filter id="gcn-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="3" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="400" height="240" fill="url(#gcn-bg)" />
      {/* layer planes */}
      <g opacity="0.18">
        <rect x="150" y="28" width="56" height="184" rx="10" fill="#7c6cf0" />
        <rect x="244" y="28" width="56" height="184" rx="10" fill="#7c6cf0" />
      </g>
      {/* input graph edges */}
      <g stroke="#8a7df0" strokeWidth="1.6" opacity="0.6">
        {inputEdges.map(([a, b], i) => (
          <line
            key={i}
            x1={inputNodes[a]!.x}
            y1={inputNodes[a]!.y}
            x2={inputNodes[b]!.x}
            y2={inputNodes[b]!.y}
          />
        ))}
      </g>
      {/* input → layer1 */}
      <g stroke="#6f5fd6" strokeWidth="1" opacity="0.3">
        {inputNodes.map((n, i) =>
          layer1.map((y, j) => (
            <line key={`${i}-${j}`} x1={n.x} y1={n.y} x2={178} y2={y} />
          )),
        )}
      </g>
      {/* layer1 → layer2 */}
      <g stroke="#7c6cf0" strokeWidth="1" opacity="0.35">
        {layer1.map((y1, i) =>
          layer2.map((y2, j) => (
            <line key={`${i}-${j}`} x1={178} y1={y1} x2={272} y2={y2} />
          )),
        )}
      </g>
      {/* layer2 → output */}
      <g stroke="#8a7df0" strokeWidth="1.2" opacity="0.45">
        {layer2.map((y2, i) =>
          output.map((yo, j) => (
            <line key={`${i}-${j}`} x1={272} y1={y2} x2={350} y2={yo} />
          )),
        )}
      </g>
      <g filter="url(#gcn-glow)">
        {inputNodes.map((n, i) => (
          <circle key={i} cx={n.x} cy={n.y} r="7" fill="#c4bbff" />
        ))}
        {layer1.map((y, i) => (
          <circle key={i} cx={178} cy={y} r="8" fill="#8b7bff" />
        ))}
        {layer2.map((y, i) => (
          <circle key={i} cx={272} cy={y} r="8" fill="#a99bff" />
        ))}
        {output.map((y, i) => (
          <circle key={i} cx={350} cy={y} r="9" fill="#5eead4" />
        ))}
      </g>
    </svg>
  );
}

function MoeArt({ className }: ArtProps) {
  // Mixture-of-Experts: a paper stack feeds a gate/router that fans to experts.
  const experts = [44, 96, 148, 200];
  return (
    <svg
      viewBox="0 0 400 240"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      role="img"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="moe-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#2a1605" />
          <stop offset="1" stopColor="#5a2f0a" />
        </linearGradient>
        <filter id="moe-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="3" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="400" height="240" fill="url(#moe-bg)" />
      {/* paper stack */}
      <g>
        <rect
          x="34"
          y="92"
          width="62"
          height="80"
          rx="6"
          fill="#fbbf60"
          opacity="0.45"
          transform="rotate(-9 65 132)"
        />
        <rect
          x="40"
          y="84"
          width="62"
          height="80"
          rx="6"
          fill="#fcd089"
          opacity="0.7"
          transform="rotate(-4 71 124)"
        />
        <rect x="46" y="78" width="62" height="80" rx="6" fill="#fde3b3" />
        <g stroke="#a45a12" strokeWidth="2.4" strokeLinecap="round">
          <line x1="56" y1="92" x2="98" y2="92" />
          <line x1="56" y1="104" x2="98" y2="104" />
          <line x1="56" y1="116" x2="84" y2="116" />
        </g>
      </g>
      {/* gate/router */}
      <line
        x1="108"
        y1="118"
        x2="176"
        y2="118"
        stroke="#f0a23c"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
      <g filter="url(#moe-glow)">
        <circle cx="196" cy="118" r="20" fill="#f59e2c" />
      </g>
      <path
        d="M188 118 l6 6 l11 -13"
        fill="none"
        stroke="#fff7e6"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* router → experts */}
      <g stroke="#f0a23c" strokeWidth="1.8" opacity="0.7" strokeLinecap="round">
        {experts.map((y, i) => (
          <line key={i} x1="216" y1="118" x2="300" y2={y + 22} />
        ))}
      </g>
      {/* expert blocks */}
      <g>
        {experts.map((y, i) => (
          <g key={i}>
            <rect
              x="300"
              y={y}
              width="62"
              height="44"
              rx="8"
              fill={i === 1 ? "#fde3b3" : "#7a3f0d"}
              stroke="#f0a23c"
              strokeWidth="1.5"
            />
            <circle
              cx="320"
              cy={y + 22}
              r="6"
              fill={i === 1 ? "#a45a12" : "#fbbf60"}
            />
            <line
              x1="332"
              y1={y + 17}
              x2="352"
              y2={y + 17}
              stroke={i === 1 ? "#a45a12" : "#fbbf60"}
              strokeWidth="2.4"
              strokeLinecap="round"
            />
            <line
              x1="332"
              y1={y + 27}
              x2="346"
              y2={y + 27}
              stroke={i === 1 ? "#a45a12" : "#fbbf60"}
              strokeWidth="2.4"
              strokeLinecap="round"
            />
          </g>
        ))}
      </g>
    </svg>
  );
}

function PaperArt({ className }: ArtProps) {
  // A conference-style LaTeX page: title, two text columns, a formula
  // block and an embedded result figure.
  const colA = [86, 98, 110, 122, 134];
  const colB = [156, 168, 180, 192];
  return (
    <svg
      viewBox="0 0 400 240"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      role="img"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="paper-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#04211f" />
          <stop offset="1" stopColor="#0c423d" />
        </linearGradient>
        <filter id="paper-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="3.5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="400" height="240" fill="url(#paper-bg)" />
      <g filter="url(#paper-glow)">
        <rect
          x="132"
          y="26"
          width="136"
          height="188"
          rx="8"
          fill="#ecfdf9"
        />
      </g>
      {/* title */}
      <rect x="158" y="40" width="84" height="8" rx="4" fill="#0f766e" />
      <rect x="174" y="54" width="52" height="5" rx="2.5" fill="#5eccba" />
      {/* two columns */}
      <g fill="#9fe3d5">
        {colA.map((y, i) => (
          <rect
            key={i}
            x="142"
            y={y}
            width={i === colA.length - 1 ? 32 : 52}
            height="4"
            rx="2"
          />
        ))}
        {colB.map((y, i) => (
          <rect
            key={i}
            x="142"
            y={y}
            width={i === colB.length - 1 ? 30 : 52}
            height="4"
            rx="2"
          />
        ))}
        {colA.map((y, i) => (
          <rect
            key={`r${i}`}
            x="206"
            y={y}
            width={i === colA.length - 1 ? 28 : 52}
            height="4"
            rx="2"
          />
        ))}
      </g>
      {/* formula block */}
      <rect
        x="206"
        y="150"
        width="52"
        height="26"
        rx="4"
        fill="#d3f5ed"
        stroke="#14b8a6"
        strokeWidth="1.2"
      />
      <rect x="212" y="158" width="40" height="4" rx="2" fill="#0d9488" />
      <rect x="212" y="166" width="28" height="4" rx="2" fill="#0d9488" />
      {/* embedded figure */}
      <rect
        x="206"
        y="182"
        width="52"
        height="24"
        rx="3"
        fill="#04211f"
        opacity="0.08"
      />
      <line
        x1="210"
        y1="202"
        x2="254"
        y2="202"
        stroke="#0d9488"
        strokeWidth="1.4"
      />
      <rect x="214" y="192" width="7" height="10" fill="#14b8a6" />
      <rect x="225" y="186" width="7" height="16" fill="#0d9488" />
      <rect x="236" y="190" width="7" height="12" fill="#2dd4bf" />
      <rect x="247" y="183" width="7" height="19" fill="#5eead4" />
    </svg>
  );
}

function CitationGraphArt({ className }: ArtProps) {
  // Radial multi-hop citation network: a seed paper, a ring of direct
  // citations, an outer ring of second-hop descendants.
  const cx = 200;
  const cy = 120;
  const ring1 = Array.from({ length: 6 }, (_, i) => {
    const a = (i / 6) * Math.PI * 2 - Math.PI / 2;
    return { x: cx + Math.cos(a) * 54, y: cy + Math.sin(a) * 54 };
  });
  const ring2 = Array.from({ length: 12 }, (_, i) => {
    const a = (i / 12) * Math.PI * 2;
    return { x: cx + Math.cos(a) * 100, y: cy + Math.sin(a) * 100 };
  });
  return (
    <svg
      viewBox="0 0 400 240"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      role="img"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="cite-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#0b1b3f" />
          <stop offset="1" stopColor="#13367a" />
        </linearGradient>
        <radialGradient id="cite-seed" cx="0.35" cy="0.35" r="0.8">
          <stop offset="0" stopColor="#dbeafe" />
          <stop offset="1" stopColor="#3b82f6" />
        </radialGradient>
        <filter id="cite-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="3" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="400" height="240" fill="url(#cite-bg)" />
      {/* ring1 → ring2 */}
      <g stroke="#5b8be8" strokeWidth="1" opacity="0.35">
        {ring2.map((n, i) => {
          const p = ring1[Math.floor(i / 2)]!;
          return <line key={i} x1={p.x} y1={p.y} x2={n.x} y2={n.y} />;
        })}
      </g>
      {/* seed → ring1 */}
      <g stroke="#7aa7f5" strokeWidth="1.8" opacity="0.8">
        {ring1.map((n, i) => (
          <line key={i} x1={cx} y1={cy} x2={n.x} y2={n.y} />
        ))}
      </g>
      <g>
        {ring2.map((n, i) => (
          <circle key={i} cx={n.x} cy={n.y} r="5.5" fill="#7aa7f5" />
        ))}
      </g>
      <g filter="url(#cite-glow)">
        {ring1.map((n, i) => (
          <circle key={i} cx={n.x} cy={n.y} r="9" fill="#a9c8fb" />
        ))}
        <circle cx={cx} cy={cy} r="17" fill="url(#cite-seed)" />
      </g>
    </svg>
  );
}

function CoraAnalysisArt({ className }: ArtProps) {
  // Exploratory analysis: a degree-distribution histogram with a power-law
  // decay curve, plus a community-cluster scatter.
  const bars = [
    { x: 44, h: 120 },
    { x: 74, h: 86 },
    { x: 104, h: 58 },
    { x: 134, h: 38 },
    { x: 164, h: 24 },
    { x: 194, h: 14 },
  ];
  const baseY = 196;
  const scatter = [
    [284, 70],
    [312, 84],
    [300, 104],
    [330, 96],
    [288, 120],
    [322, 124],
    [346, 78],
    [272, 96],
  ];
  return (
    <svg
      viewBox="0 0 400 240"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      role="img"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="cora-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#241043" />
          <stop offset="1" stopColor="#4a1d7a" />
        </linearGradient>
        <filter id="cora-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="2.5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="400" height="240" fill="url(#cora-bg)" />
      {/* axes */}
      <line
        x1="36"
        y1={baseY}
        x2="232"
        y2={baseY}
        stroke="#c9a9f0"
        strokeWidth="1.8"
      />
      <line x1="36" y1="48" x2="36" y2={baseY} stroke="#c9a9f0" strokeWidth="1.8" />
      {/* bars */}
      <g>
        {bars.map((b, i) => (
          <rect
            key={i}
            x={b.x}
            y={baseY - b.h}
            width="22"
            height={b.h}
            rx="3"
            fill="#b07ce8"
            opacity={0.55 + i * 0.06}
          />
        ))}
      </g>
      {/* power-law curve */}
      <g filter="url(#cora-glow)">
        <path
          d="M55 70 C 95 150, 130 182, 216 192"
          fill="none"
          stroke="#f0a8e8"
          strokeWidth="2.6"
          strokeLinecap="round"
        />
      </g>
      {/* community scatter */}
      <circle
        cx="312"
        cy="100"
        r="58"
        fill="none"
        stroke="#c9a9f0"
        strokeWidth="1.4"
        strokeDasharray="4 6"
        opacity="0.6"
      />
      <g filter="url(#cora-glow)">
        {scatter.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="6" fill="#ecd9ff" />
        ))}
      </g>
    </svg>
  );
}

function VitAblationArt({ className }: ArtProps) {
  // ViT ablation: image patch grid → attention heatmap, with an ablation
  // matrix beneath.
  const heat = [
    [0.25, 0.5, 0.85, 0.4],
    [0.55, 0.95, 0.7, 0.3],
    [0.35, 0.7, 0.5, 0.62],
    [0.18, 0.42, 0.66, 0.9],
  ];
  return (
    <svg
      viewBox="0 0 400 240"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      role="img"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="vit-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#04222b" />
          <stop offset="1" stopColor="#0a4655" />
        </linearGradient>
        <filter id="vit-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="2.5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="400" height="240" fill="url(#vit-bg)" />
      {/* patch grid */}
      <rect
        x="36"
        y="36"
        width="116"
        height="116"
        rx="8"
        fill="none"
        stroke="#3fb8a6"
        strokeWidth="1.6"
      />
      {[0, 1, 2, 3].map((r) =>
        [0, 1, 2, 3].map((c) => (
          <rect
            key={`${r}-${c}`}
            x={42 + c * 27}
            y={42 + r * 27}
            width="23"
            height="23"
            rx="3"
            fill="#2f9e8f"
            opacity={0.2 + ((r + c) % 3) * 0.24}
          />
        )),
      )}
      {/* arrow */}
      <path
        d="M160 94 l28 0 m-9 -8 l9 8 l-9 8"
        fill="none"
        stroke="#67e8d4"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* attention heatmap */}
      <g filter="url(#vit-glow)">
        {heat.map((row, r) =>
          row.map((v, c) => (
            <rect
              key={`${r}-${c}`}
              x={200 + c * 27}
              y={36 + r * 27}
              width="24"
              height="24"
              rx="3"
              fill="#fb923c"
              opacity={0.2 + v * 0.78}
            />
          )),
        )}
      </g>
      {/* ablation matrix */}
      <g>
        {[0, 1, 2].map((r) => (
          <g key={r}>
            <circle cx="48" cy={176 + r * 22} r="5" fill="#3fb8a6" />
            <rect
              x="60"
              y={171 + r * 22}
              width={120 + r * 36}
              height="8"
              rx="4"
              fill="#2f9e8f"
              opacity={0.8 - r * 0.18}
            />
            <rect
              x={188 + r * 36}
              y={171 + r * 22}
              width="44"
              height="8"
              rx="4"
              fill="#fb923c"
              opacity={0.5 + r * 0.2}
            />
          </g>
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
      <div className="container-md mx-auto mt-8 grid grid-cols-1 gap-6 px-4 md:grid-cols-2 md:px-8">
        {CASE_STUDIES.map(({ threadId, title, description, Art }) => (
          <Link
            key={threadId}
            href={pathOfThread(threadId) + "?mock=true"}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Card className="group/card flex h-full flex-col overflow-hidden border-white/10 bg-[#141414] transition-colors duration-300 hover:border-white/25">
              {/* Illustration band */}
              <div className="relative aspect-[16/9] overflow-hidden">
                <Art className="size-full transition-transform duration-500 group-hover/card:scale-105" />
              </div>
              {/* Content — always fully visible */}
              <div className="flex flex-col gap-2 p-5">
                <h3 className="text-xl font-bold leading-snug text-white">
                  {title}
                </h3>
                <p className="text-sm leading-relaxed text-white/70">
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
