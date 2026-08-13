#!/usr/bin/env bash
# Build cv.pdf inside the pinned Linux container.
#
# This is the ONE build path: the Pages workflow calls this script, and so do
# you locally. cv.pdf is not reproducible across platforms — headless Chromium
# hints glyphs on Linux and not on macOS, which silently changed text layout in
# the deployed PDF once already — so building on a Mac tells you nothing about
# what CI will ship. Running the same image both places removes the difference
# instead of hoping it doesn't matter.
#
# Usage:  scripts/ci_docker.sh              # writes cv.pdf into the repo root
#         OUT=/tmp scripts/ci_docker.sh     # write it somewhere else
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${OUT:-$ROOT}"

# Ships Chromium preinstalled and matched to its Playwright version, so the
# browser build is pinned by the image tag. Keep the version in step with
# playwright== in scripts/requirements.txt — they must agree or Playwright
# will refuse the preinstalled browser and download its own.
IMAGE="${IMAGE:-mcr.microsoft.com/playwright/python:v1.59.0-noble}"

if ! docker info >/dev/null 2>&1; then
  echo "docker isn't running" >&2
  exit 1
fi

echo "==> building cv.pdf in $IMAGE"

docker run --rm \
  -v "$ROOT":/src:ro \
  -v "$OUT":/out \
  -e PIP_DISABLE_PIP_VERSION_CHECK=1 \
  "$IMAGE" bash -euo pipefail -c '
    # The source mount is read-only (generate_pdf.py writes into the tree) and
    # .venv holds macOS binaries, so work from a copy without it.
    cp -r /src /work && rm -rf /work/.venv /work/.git
    cd /work

    # The image carries the browsers but not the Python package.
    pip install --quiet --break-system-packages -r scripts/requirements.txt

    python scripts/generate_pdf.py
    python scripts/verify_pdf.py

    cp cv.pdf /out/cv.pdf
  '

echo "==> wrote $OUT/cv.pdf"
