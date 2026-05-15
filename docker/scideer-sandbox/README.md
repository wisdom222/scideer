# scideer-sandbox / libra-sandbox

DeerFlow AIO sandbox extended with both skill toolchains:

- **ML layer** (for the `paper-reproduction` skill) — PyTorch (CPU wheel),
  `torchvision`, `torch_geometric`, `pdfplumber`.
- **LaTeX layer** (for the `scientific-writing` skill) — `texlive-latex-extra`
  + fonts + `texlive-bibtex-extra` + `latexmk`.

**Image size:** base ~3 GB + ML layer ~1.0 GB + LaTeX layer ~1.4 GB ≈ **~5.4 GB**.
(vs ~7 GB with texlive-full.)

## Prerequisites

- Docker 20+ (or Apple Container on macOS)
- Network access to `enterprise-public-cn-beijing.cr.volces.com` for the base pull
- Network access to `download.pytorch.org` for the CPU torch wheel (or use a
  mirror; see Build > China-region builds below)
- ~8 GB free disk (image + build cache)

## Build

From the repo root:

```bash
docker build -t libra-sandbox:latest -f docker/scideer-sandbox/Dockerfile docker/scideer-sandbox/
```

First-time build downloads ~200 MB of torch + ~1 GB of texlive packages.
**Expect 15–25 min** (was 10–15 min before the ML layer was added).

### China-region builds (slow pip)

If `pip install torch_geometric pdfplumber` is slow from the Tencent Cloud
Singapore region, switch to the Tsinghua mirror by editing the second
`pip install` invocation in the Dockerfile:

```dockerfile
pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    torch_geometric pdfplumber
```

Leave the first `pip install` (torch) with `--index-url https://download.pytorch.org/whl/cpu`
because the Tsinghua mirror does not re-host the PyTorch CPU index.

## Smoke Test

After the build (each command should exit 0 and print a version string):

```bash
# LaTeX toolchain
docker run --rm libra-sandbox:latest pdflatex --version | head -1
docker run --rm libra-sandbox:latest latexmk --version

# ML toolchain
docker run --rm libra-sandbox:latest python -c "import torch; print(torch.__version__)"
docker run --rm libra-sandbox:latest python -c "import torchvision; print(torchvision.__version__)"
docker run --rm libra-sandbox:latest python -c "from torch_geometric.nn import GCNConv; print('PyG ok')"
docker run --rm libra-sandbox:latest python -c "import pdfplumber; print(pdfplumber.__version__)"
```

Six commands; all must print without error. (The Dockerfile already runs an
equivalent smoke test in a `RUN` step, so a successful `docker build` proves
these too — these commands are a post-build sanity check.)

User-context check (first build only):

```bash
docker run --rm libra-sandbox:latest whoami
```

If it prints `root`, no action needed. If it prints another user and you later
hit permission errors at skill-execution time, see Troubleshooting below.

## Wire Up to DeerFlow

Edit `config.yaml` on the server. Locate the existing `sandbox:` block (usually
`LocalSandboxProvider` from `config.example.yaml`, or a commented-out AIO
section). **Replace** it with:

```yaml
sandbox:
  use: deerflow.community.aio_sandbox:AioSandboxProvider
  image: libra-sandbox:latest
  port: 8080
  replicas: 3
  # Recommended: mount the SciDeer cache for the paper-reproduction skill.
  # Tier 1 of the 3-tier code-acquisition chain looks here first.
  mounts:
    - host_path: /home/<user>/.scideer/cache
      container_path: /mnt/scideer-cache
      read_only: true
```

Do **not** delete other sections of `config.yaml` (models, subagents,
extensions, etc.) — only the `sandbox:` block is replaced.

Restart DeerFlow:

```bash
make dev-daemon-stop && make dev-daemon
```

(Or your local equivalent — `pkill -f 'deerflow' && make dev` on a hand-rolled
setup.)

Verify in the Web UI: ask any agent to run these in a sandboxed bash:

```
which pdflatex                                  # expect /usr/bin/pdflatex
python -c "import torch; print(torch.__version__)"   # expect 2.x.y
python -c "from torch_geometric.nn import GCNConv"   # expect no error
```

## Rollback

If `libra-sandbox:latest` misbehaves and you need to revert the sandbox to the
default `LocalSandboxProvider` (e.g. minutes before a demo), restore the
`sandbox:` block in `config.yaml` to the local-execution variant from
`config.example.yaml`:

```yaml
sandbox:
  use: deerflow.sandbox.local:LocalSandboxProvider
  allow_host_bash: false
  bash_output_max_chars: 20000
  read_file_output_max_chars: 50000
  ls_output_max_chars: 20000
```

Then restart DeerFlow:

```bash
make dev-daemon-stop && make dev-daemon
```

Note: rolling back **also disables the paper-reproduction skill's ML
toolchain** (no `torch` / `torch_geometric` on the host PATH unless installed
separately). Tier 1 (cache) might still work if the cached repo doesn't itself
import torch; Tier 3 (template skeleton) will dep_missing. The skill will
report `execution_failed` via `tier_attempts`; it will NOT silently fall back
to a hand-rolled implementation (by design — see SKILL.md "What You MUST NOT Do").

Rollback also disables `scientific-writing`'s PDF compile path (collect /
skeleton / naked-tex phases still work).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `pdflatex: command not found` inside skill | Wrong image active | Confirm `docker images \| grep libra-sandbox`; check `config.yaml` `image:` field; restart DeerFlow |
| `ModuleNotFoundError: No module named 'torch'` inside paper-reproduction | Wrong image (base AIO, not libra-sandbox) | Same as above — verify `config.yaml` `image:` is `libra-sandbox:latest` and the image was rebuilt after the Dockerfile update on 2026-05-15 |
| `pip install torch` times out during build | China-region build | Use Tsinghua mirror for non-torch packages (see Build > China-region builds above) |
| `torch_geometric` install fails with "torch_scatter not found" | Older PyG pinned by accident | The Dockerfile does NOT install torch_scatter; PyG 2.5+ uses internal alternatives. If you pinned an older PyG, unpin it |
| Compile hangs > 5 min | latexmk in interactive mode (rare) | Verify `compile_pdf.sh` uses `-interaction=nonstopmode` (it does by default; do not modify) |
| Permission denied writing `outputs/paper/figures/` | USER mismatch from base image | Rebuild with `RUN chown -R <user>:<user> /home/<user>` appended to the Dockerfile after the LaTeX layer |
| Image larger than 7 GB | `texlive-full` was substituted, OR full-CUDA torch leaked in | Confirm Dockerfile uses `texlive-latex-extra` (not `texlive-full`) and torch is installed via `--index-url https://download.pytorch.org/whl/cpu`; rebuild |
| `apt-get update` fails during build | Network policy or registry mirror | Configure Docker `--build-arg http_proxy` or replace registry mirror |

## Related Files

- `docker/scideer-sandbox/Dockerfile` — image definition (ML + LaTeX layers)
- `skills/custom/paper-reproduction/SKILL.md` — uses torch + torch_geometric + pdfplumber provided by this image
- `skills/custom/paper-reproduction/templates/pytorch_skeleton.py` — Tier 3 fallback that requires `torch_geometric` (for Cora/Citeseer/Pubmed) or `torchvision` (for MNIST/FashionMNIST), both provided by this image
- `skills/custom/scientific-writing/scripts/compile_pdf.sh` — uses `latexmk` provided by this image
- `docs/plans/2026-05-06-paper-reproduction-design.md` §11 — track-boundary contract; sandbox prerequisites
- `docs/plans/2026-05-06-scientific-writing-design.md` §4 — LaTeX design rationale
