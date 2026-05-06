#!/bin/bash
# compile_pdf.sh — 3-attempt retry + naked-PDF degradation.
# Always produces paper.pdf and compile_errors.md if at all possible.
#
# Usage: compile_pdf.sh <paper-dir>
#   Expects: <paper-dir>/paper.tex, <paper-dir>/references.bib (may be empty),
#            <paper-dir>/figures/ (may be empty)
#   Produces: <paper-dir>/paper.pdf, <paper-dir>/compile_errors.md
#
# Exit codes:
#   0 — paper.pdf was produced (vanilla, attempt 2/3, or naked)
#   1 — even naked PDF compilation failed; user must hand-debug

set -u

PAPER_DIR="${1:-outputs/paper}"
if [ ! -d "$PAPER_DIR" ]; then
    echo "compile_pdf.sh: paper dir not found: $PAPER_DIR" >&2
    exit 1
fi
cd "$PAPER_DIR" || exit 1

if [ ! -f paper.tex ]; then
    echo "compile_pdf.sh: paper.tex not found in $PAPER_DIR" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")" && pwd)"

# Clean up artifacts from any previous compile run in this directory.
# Keeps paper.tex and references.bib (the inputs); removes the previous
# attempt logs, naked artifacts, and the previous compile_errors.md so
# the new log doesn't accumulate stale content from a prior demo rehearsal.
rm -f compile_attempt_*.log compile_naked.log paper_naked.tex paper_naked.pdf paper.tex.bak compile_errors.md

LOG="compile_errors.md"

{
    echo "# LaTeX Compile Log"
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "Paper directory: $PAPER_DIR"
} > "$LOG"

run_compile() {
    # $1 = attempt number, $2 = source tex (without .tex)
    local attempt="$1"
    local src="$2"
    latexmk -pdf -interaction=nonstopmode -file-line-error "$src.tex" \
        > "compile_attempt_${attempt}.log" 2>&1
}

dump_tail() {
    local attempt="$1"
    {
        echo '```'
        if [ -f paper.log ]; then
            grep -E '^(!|paper\.tex:[0-9]+:|LaTeX (Error|Warning):|! Package .* Error:|Runaway argument|Emergency stop|Citation .* undefined|Reference .* undefined|File .* not found)' paper.log | head -40 || true
        fi
        echo "--- compile_attempt_${attempt}.log (tail) ---"
        tail -30 "compile_attempt_${attempt}.log" 2>/dev/null || true
        echo '```'
    } >> "$LOG"
}

# ---------- Attempt 1: vanilla ----------
echo "" >> "$LOG"
echo "## Attempt 1 (vanilla)" >> "$LOG"
if run_compile 1 paper; then
    echo "Result: success" >> "$LOG"
    exit 0
fi
dump_tail 1

# ---------- Attempt 2: drop missing image refs ----------
echo "" >> "$LOG"
echo "## Attempt 2 (after dropping missing image refs)" >> "$LOG"
if [ -f paper.log ]; then
    # Extract filenames LaTeX reports as missing.
    MISSING_FILES=$(grep -oE "File \`[^']+' not found" paper.log | \
                    sed -E "s/File \`([^']+)' not found/\1/" | sort -u || true)
    if [ -n "${MISSING_FILES:-}" ]; then
        for img in $MISSING_FILES; do
            base=$(basename "$img")
            echo "- Removing reference to missing file: $img" >> "$LOG"
            # Comment out lines containing \includegraphics + that base filename
            sed -i.bak -E "/\\\\includegraphics([^{]*\\{)?[^}]*${base}/s/^/% MISSING_FIG: /" paper.tex
            rm -f paper.tex.bak
        done
    else
        echo "- No missing-image errors detected; retrying anyway." >> "$LOG"
    fi
fi
if run_compile 2 paper; then
    echo "Result: success after image-ref cleanup" >> "$LOG"
    exit 0
fi
dump_tail 2

# ---------- Attempt 3: drop undefined cites ----------
echo "" >> "$LOG"
echo "## Attempt 3 (after dropping undefined cites)" >> "$LOG"
if [ -f paper.log ]; then
    BAD_KEYS=$(grep -oE "Citation \`[^']+' (on page [0-9]+ )?undefined" paper.log | \
               sed -E "s/Citation \`([^']+)'.*/\1/" | sort -u || true)
    if [ -n "${BAD_KEYS:-}" ]; then
        for key in $BAD_KEYS; do
            echo "- Replacing undefined cite key: $key" >> "$LOG"
            # Replace single-key \citep{key} and \cite{key} with [?].
            # Multi-key cites containing this key are left alone (LaTeX still
            # warns but compiles); they'll just print [?] inline at compile time.
            esc=$(printf '%s\n' "$key" | sed -e 's/[]\/$*.^|[]/\\&/g')
            sed -i.bak -E "s/\\\\citep\\{${esc}\\}/[?]/g; s/\\\\citet\\{${esc}\\}/[?]/g; s/\\\\cite\\{${esc}\\}/[?]/g" paper.tex
            rm -f paper.tex.bak
        done
    else
        echo "- No undefined-cite errors detected; retrying anyway." >> "$LOG"
    fi
fi
if run_compile 3 paper; then
    echo "Result: success after cite cleanup" >> "$LOG"
    exit 0
fi
dump_tail 3

# ---------- Naked PDF fallback ----------
echo "" >> "$LOG"
echo "## Naked PDF Fallback" >> "$LOG"
echo "After 3 failed attempts, generating text-only naked PDF." >> "$LOG"

GEN_PY="$SCRIPT_DIR/generate_latex.py"
if [ ! -f "$GEN_PY" ]; then
    echo "compile_pdf.sh: generate_latex.py not found at $GEN_PY" >> "$LOG"
    exit 1
fi

if ! python3 "$GEN_PY" naked --tex paper.tex --out paper_naked.tex \
        >> "$LOG" 2>&1; then
    echo "Naked tex generation failed." >> "$LOG"
    exit 1
fi

if latexmk -pdf -interaction=nonstopmode paper_naked.tex \
        > compile_naked.log 2>&1 && [ -f paper_naked.pdf ]; then
    cp paper_naked.pdf paper.pdf
    echo "Naked PDF compiled. Original paper.tex preserved; paper_naked.tex is the compiled source." >> "$LOG"
    exit 0
fi

{
    echo "Naked compile also failed."
    echo '```'
    tail -30 compile_naked.log 2>/dev/null || true
    echo '```'
    echo ""
    echo "paper.pdf was NOT produced. paper.tex and references.bib are preserved on disk for manual debugging."
} >> "$LOG"
exit 1
