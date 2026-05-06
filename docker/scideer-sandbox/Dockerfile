# Libra Sandbox — DeerFlow AIO sandbox + LaTeX toolchain
#
# Built on top of Volcengine's all-in-one-sandbox image. Adds:
#   - texlive-latex-extra      (compile core + most academic packages)
#   - texlive-fonts-recommended (Latin Modern et al.)
#   - texlive-bibtex-extra     (bibtex tools beyond the base set)
#   - latexmk                  (multi-pass orchestration; used by compile_pdf.sh)
#
# Resulting image is ~1.4 GB larger than base (vs ~4 GB+ for texlive-full).

FROM enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest

USER root

# Install LaTeX toolchain.
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

# Smoke test: fail the build if any binary is missing.
RUN pdflatex --version > /dev/null && \
    bibtex --version > /dev/null && \
    latexmk --version > /dev/null

LABEL org.opencontainers.image.description="DeerFlow AIO sandbox + LaTeX (texlive-latex-extra) for SciDeer/Libra scientific-writing skill"
LABEL org.opencontainers.image.source="https://github.com/wisdom222/scideer"
