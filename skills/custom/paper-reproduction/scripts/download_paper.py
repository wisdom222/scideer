#!/usr/bin/env python3
"""download_paper.py -- fetch arxiv PDF and extract text.

Reuses the requests-or-urllib-fallback pattern from
skills/public/systematic-literature-review/scripts/arxiv_search.py.

Outputs:
  workspace/paper.pdf
  workspace/paper.txt   (PDF text, one block per page joined with two newlines)

PDF extraction order of preference:
  1. pdfplumber  (most accurate text extraction)
  2. pypdf       (pure-python fallback, lower fidelity)
  3. fail with clear error message
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_TIMEOUT = 60


# --- HTTP shim (same fallback pattern as arxiv_search.py) ---
try:
    import requests  # type: ignore
except ImportError:
    import urllib.error
    import urllib.request

    class _UrllibResponse:
        def __init__(self, data: bytes, status: int) -> None:
            self.content = data
            self.status_code = status

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    class _UrllibShim:
        @staticmethod
        def get(url, timeout=DEFAULT_TIMEOUT, **_):
            req = urllib.request.Request(url, headers={"User-Agent": "scideer-paper-repro/0.1"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return _UrllibResponse(resp.read(), resp.status)
            except urllib.error.HTTPError as e:
                return _UrllibResponse(e.read(), e.code)

    requests = _UrllibShim()  # type: ignore


def _arxiv_pdf_url(arxiv_id: str) -> str:
    # Strip version suffix if present (e.g. 1609.02907v4 -> 1609.02907)
    base = arxiv_id.split("v")[0] if "v" in arxiv_id and arxiv_id.split("v")[-1].isdigit() else arxiv_id
    return f"https://arxiv.org/pdf/{base}.pdf"


def _download_pdf(url: str, dst: Path) -> int:
    print(f"download_paper: GET {url}", file=sys.stderr)
    resp = requests.get(url, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    dst.write_bytes(resp.content)
    return len(resp.content)


def _extract_text_pdfplumber(pdf_path: Path) -> str | None:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return None
    blocks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if txt:
                blocks.append(txt)
    return "\n\n".join(blocks)


def _extract_text_pypdf(pdf_path: Path) -> str | None:
    try:
        import pypdf  # type: ignore
    except ImportError:
        try:
            import PyPDF2 as pypdf  # type: ignore
        except ImportError:
            return None
    blocks = []
    reader = pypdf.PdfReader(str(pdf_path))
    for page in reader.pages:
        txt = page.extract_text() or ""
        if txt:
            blocks.append(txt)
    return "\n\n".join(blocks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download arxiv PDF + extract text.")
    parser.add_argument("arxiv_id", help="e.g. 1609.02907")
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()

    args.workspace.mkdir(parents=True, exist_ok=True)
    pdf_path = args.workspace / "paper.pdf"
    txt_path = args.workspace / "paper.txt"

    # Download
    try:
        size = _download_pdf(_arxiv_pdf_url(args.arxiv_id), pdf_path)
        print(f"download_paper: wrote {size} bytes to {pdf_path}", file=sys.stderr)
    except Exception as exc:
        print(f"download_paper: FAILED to download arxiv:{args.arxiv_id}: {exc}", file=sys.stderr)
        return 1

    # Extract text
    text = _extract_text_pdfplumber(pdf_path) or _extract_text_pypdf(pdf_path)
    if text is None:
        print("download_paper: neither pdfplumber nor pypdf is installed", file=sys.stderr)
        return 1
    if len(text) < 1024:
        print(f"download_paper: extracted only {len(text)} chars; PDF may be image-based",
              file=sys.stderr)
    txt_path.write_text(text, encoding="utf-8")
    print(f"download_paper: wrote {len(text)} chars to {txt_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
