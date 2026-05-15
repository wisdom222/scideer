# Libra Sandbox — DeerFlow AIO sandbox + ML toolchain + LaTeX toolchain
#
# Built on top of Volcengine's all-in-one-sandbox image. Adds two skill
# toolchains in separate layers (ordered larger-first for better cache reuse):
#
#   Layer 1 (ML, ~1.0 GB) — for the `paper-reproduction` skill
#     - torch (CPU wheel)
#     - torchvision      (MNIST CNN backup demo path in pytorch_skeleton.py)
#     - torch_geometric  (basic ops; torch_scatter/torch_sparse are optional
#                         in PyG 2.5+ and not needed for GCN on Cora)
#     - pdfplumber       (PDF -> text extraction in download_paper.py)
#
#   Layer 2 (LaTeX, ~1.4 GB) — for the `scientific-writing` skill
#     - texlive-latex-extra      compile core + most academic packages
#     - texlive-fonts-recommended Latin Modern et al.
#     - texlive-bibtex-extra      bibtex tools beyond the base set
#     - latexmk                   multi-pass orchestration
#
# Resulting image: base ~3 GB + ML ~1.0 GB + LaTeX ~1.4 GB ≈ ~5.4 GB.
# (vs ~7 GB with texlive-full; vs ~3 GB base alone.)

FROM enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest

USER root

# Layer 1: ML toolchain (paper-reproduction skill).
#
# Install order:
#   1. Upgrade pip first so PEP 517 wheels resolve correctly.
#   2. torch from the CPU-only wheel index to avoid pulling CUDA (~2 GB extra).
#   3. torch_geometric + pdfplumber from regular pypi.
#
# We do NOT pin exact versions: pip's resolver chooses a torch/PyG combo with
# prebuilt wheels at build time. If you need reproducible builds, pin both:
#   torch==2.3.1 (CPU index has wheels for py3.10-3.12)
#   torch_geometric==2.5.3 (compatible with torch 2.3.x)
#
# Note for China-region builds: if pip is slow, swap to a mirror, e.g.
#   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ...
# Verify torch from CPU index still resolves (the Tsinghua mirror doesn't
# re-host the pytorch.org CPU index; keep --index-url for torch explicitly).
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
        torch_geometric \
        pdfplumber

# Layer 2: LaTeX toolchain (scientific-writing skill).
#   --no-install-recommends keeps the layer lean; we add fonts explicitly.
#   DEBIAN_FRONTEND=noninteractive avoids tzdata interactive prompts.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        texlive-latex-extra \
        texlive-fonts-recommended \
        texlive-bibtex-extra \
        latexmk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Smoke test: fail the build if any required dependency is missing.
# Each line in its own `&&` chain so the build error message points at the
# specific missing piece.
RUN python -c "import torch; print(f'torch {torch.__version__}')" && \
    python -c "import torchvision; print(f'torchvision {torchvision.__version__}')" && \
    python -c "from torch_geometric.nn import GCNConv; from torch_geometric.datasets import Planetoid; print('torch_geometric OK')" && \
    python -c "import pdfplumber; print(f'pdfplumber {pdfplumber.__version__}')" && \
    pdflatex --version > /dev/null && \
    bibtex --version > /dev/null && \
    latexmk --version > /dev/null && \
    echo "All sandbox dependencies present."

LABEL org.opencontainers.image.description="DeerFlow AIO sandbox + PyTorch (CPU) + torch_geometric + LaTeX (texlive-latex-extra) for SciDeer/Libra skills (paper-reproduction, scientific-writing)"
LABEL org.opencontainers.image.source="https://github.com/wisdom222/scideer"
