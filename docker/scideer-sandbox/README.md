# scideer-sandbox / libra-sandbox

DeerFlow AIO sandbox extended with the LaTeX toolchain required by the
`scientific-writing` skill. Adds `texlive-latex-extra` + fonts +
`texlive-bibtex-extra` + `latexmk` on top of the base image.

**Image size:** base ~3 GB + LaTeX layer ~1.4 GB ≈ ~4.4 GB (vs 7 GB for texlive-full).

## Prerequisites

- Docker 20+ (or Apple Container on macOS)
- Network access to `enterprise-public-cn-beijing.cr.volces.com` for the base pull
- ~6 GB free disk

## Build

From the repo root:

```bash
docker build -t libra-sandbox:latest -f docker/scideer-sandbox/Dockerfile docker/scideer-sandbox/
```

First-time build downloads ~1 GB of texlive packages. Expect 10–15 min.

## Smoke Test

After the build:

```bash
docker run --rm libra-sandbox:latest pdflatex --version
docker run --rm libra-sandbox:latest latexmk --version
```

Both should print version strings without error.

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
  # Optional: mount the SciDeer cache used by paper-reproduction.
  # mounts:
  #   - host_path: /home/<user>/.scideer/cache
  #     container_path: /mnt/scideer-cache
  #     read_only: true
```

Do **not** delete other sections of `config.yaml` (models, subagents,
extensions, etc.) — only the `sandbox:` block is replaced.

Restart DeerFlow:

```bash
make dev-daemon-stop && make dev-daemon
```

(Or your local equivalent — `pkill -f 'deerflow' && make dev` on a hand-rolled
setup.)

Verify in the Web UI: ask any agent to run `which pdflatex` in a sandboxed
bash. Expected output: `/usr/bin/pdflatex`.

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

Note: rolling back disables the `scientific-writing` skill's PDF compile
(no LaTeX on the host PATH unless you've installed it separately). The skill's
non-LaTeX phases (collect, skeleton, naked-tex generation) still work.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `pdflatex: command not found` inside skill | Wrong image active | Confirm `docker images \| grep libra-sandbox`; check `config.yaml` `image:` field; restart DeerFlow |
| Compile hangs > 5 min | latexmk in interactive mode (rare) | Verify `compile_pdf.sh` uses `-interaction=nonstopmode` (it does by default; do not modify) |
| Permission denied writing `outputs/paper/figures/` | USER mismatch from base image | Rebuild with `RUN chown -R <user>:<user> /home/<user>` appended to the Dockerfile after the texlive layer |
| Image larger than 5 GB | `texlive-full` was substituted | Confirm Dockerfile uses `texlive-latex-extra`, not `texlive-full`; rebuild |
| `apt-get update` fails during build | Network policy or registry mirror | Configure Docker `--build-arg http_proxy` or replace registry mirror |

## Related Files

- `docker/scideer-sandbox/Dockerfile` — image definition
- `skills/custom/scientific-writing/scripts/compile_pdf.sh` — uses `latexmk` provided by this image
- `docs/plans/2026-05-06-scientific-writing-design.md` §4 — design rationale
