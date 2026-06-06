#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# Build and push a multi-arch Docker image (amd64 + arm64) with tags.
# By default, it tags as both :<version> and :latest.
# - VERSION is required (e.g., v0.1.2 or sha-abc123)
# - USERNAME is optional; defaults to $DOCKERHUB_USERNAME or $(whoami)
# - IMAGE defaults to "mousesearch" but can be overridden with -i/--image
#
# Two modes:
#   * Default (multi-arch): uses `docker buildx --push` to build linux/amd64 and
#     linux/arm64 and push them as a single manifest. A multi-arch build cannot
#     be loaded into the local Docker image store, so this mode always pushes.
#   * Local fast path (--load): builds a SINGLE arch (the host's by default) and
#     loads it into the local Docker store for testing. Does not push.
#
# One-time setup required for multi-arch builds (run once per machine):
#   docker run --privileged --rm tonistiigi/binfmt --install all   # skip on Apple Silicon
#   docker buildx create --name multiarch --use --bootstrap
#
# Usage:
#   ./buildImage.sh -v <version> [-u <user>] [-i <image>] [--platform <list>]
#                   [--load] [--no-cache] [--no-latest]
#
# Examples:
#   ./buildImage.sh -v v0.1.2                       # multi-arch build + push
#   ./buildImage.sh -v dev --load                   # single-arch, local only (no push)
#   ./buildImage.sh -v v0.1.3 --platform linux/arm64 --load
#   ./buildImage.sh -v v0.1.3 --no-latest
# ------------------------------------------------------------------------------

USERNAME_DEFAULT="${DOCKERHUB_USERNAME:-$(whoami)}"
IMAGE_DEFAULT="mousesearch"
PLATFORM_DEFAULT="linux/amd64,linux/arm64"
NO_CACHE=""
PUSH_LATEST="true"
LOAD_LOCAL="false"

usage() {
  cat <<EOF
Usage: $0 -v <version> [-u <user>] [-i <image>] [--platform <list>] [--load] [--no-cache] [--no-latest]

Required:
  -v, --version   Image version tag to publish (e.g., v0.1.2)

Optional:
  -u, --username  Docker Hub username (default: \$DOCKERHUB_USERNAME or $(whoami))
  -i, --image     Image name/repository (default: ${IMAGE_DEFAULT})
      --platform  Comma-separated platforms (default: ${PLATFORM_DEFAULT})
      --load      Single-arch fast path: build for the host arch and load into
                  the local Docker store instead of pushing. For local testing.
      --no-cache  Build without using cache
      --no-latest Do not tag or push the 'latest' tag

Environment:
  DOCKERHUB_USERNAME  Used as default for --username if set

One-time setup (multi-arch only):
  docker run --privileged --rm tonistiigi/binfmt --install all   # skip on Apple Silicon
  docker buildx create --name multiarch --use --bootstrap

Examples:
  $0 -v v0.1.2                       # multi-arch build + push
  $0 -v dev --load                   # single-arch, local only (no push)
  $0 -v v0.1.3 --platform linux/arm64 --load
EOF
}

# --- Parse args ---
USERNAME="${USERNAME_DEFAULT}"
IMAGE="${IMAGE_DEFAULT}"
PLATFORM="${PLATFORM_DEFAULT}"
VERSION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -u|--username) USERNAME="$2"; shift 2 ;;
    -i|--image)    IMAGE="$2"; shift 2 ;;
    -v|--version)  VERSION="$2"; shift 2 ;;
    --platform)    PLATFORM="$2"; shift 2 ;;
    --load)        LOAD_LOCAL="true"; shift ;;
    --no-cache)    NO_CACHE="--no-cache"; shift ;;
    --no-latest)   PUSH_LATEST="false"; shift ;;
    -h|--help)     usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "${VERSION}" ]]; then
  echo "ERROR: --version is required."
  usage
  exit 1
fi

# In --load mode, default to the host's single arch unless the caller overrode
# --platform. buildx --load only supports a single platform.
if [[ "${LOAD_LOCAL}" == "true" && "${PLATFORM}" == "${PLATFORM_DEFAULT}" ]]; then
  PLATFORM=""  # empty => host native arch
fi

if [[ "${LOAD_LOCAL}" == "true" && "${PLATFORM}" == *","* ]]; then
  echo "ERROR: --load supports only a single platform, got: ${PLATFORM}"
  exit 1
fi

echo ">> Using:"
echo "   USERNAME   : ${USERNAME}"
echo "   IMAGE      : ${IMAGE}"
echo "   VERSION    : ${VERSION}"
echo "   PLATFORM   : ${PLATFORM:-<host native>}"
echo "   MODE       : $([[ "${LOAD_LOCAL}" == "true" ]] && echo 'load (local, no push)' || echo 'push (multi-arch)')"
echo "   NO_CACHE   : ${NO_CACHE:-<none>}"
echo "   PUSH_LATEST: ${PUSH_LATEST}"

# --- Sanity checks ---
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is not installed or not in PATH."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Cannot talk to the Docker daemon. Is it running? Do you need sudo?"
  exit 1
fi

if ! docker buildx version >/dev/null 2>&1; then
  echo "ERROR: 'docker buildx' is not available. Install/enable the Buildx plugin."
  exit 1
fi

# --- Assemble tags ---
FULL_VERSION_TAG="${USERNAME}/${IMAGE}:${VERSION}"
FULL_LATEST_TAG="${USERNAME}/${IMAGE}:latest"

BUILD_ARGS=()
BUILD_ARGS+=(-t "${FULL_VERSION_TAG}")
echo ">> Building:"
echo "   ${FULL_VERSION_TAG}"

if [[ "${PUSH_LATEST}" == "true" ]]; then
  BUILD_ARGS+=(-t "${FULL_LATEST_TAG}")
  echo "   ${FULL_LATEST_TAG}"
fi

if [[ -n "${PLATFORM}" ]]; then
  BUILD_ARGS+=(--platform "${PLATFORM}")
fi

if [[ -n "${NO_CACHE}" ]]; then
  BUILD_ARGS+=(${NO_CACHE})
fi

# --- Build ---
if [[ "${LOAD_LOCAL}" == "true" ]]; then
  echo ">> buildx build --load (single-arch, local only)"
  docker buildx build "${BUILD_ARGS[@]}" --load ..

  echo ">> Verifying local images..."
  if ! docker image inspect "${FULL_VERSION_TAG}" >/dev/null 2>&1; then
    echo "ERROR: Build completed but ${FULL_VERSION_TAG} not found locally."
    exit 1
  fi
  if [[ "${PUSH_LATEST}" == "true" ]] && ! docker image inspect "${FULL_LATEST_TAG}" >/dev/null 2>&1; then
    echo "ERROR: Build completed but ${FULL_LATEST_TAG} not found locally."
    exit 1
  fi

  echo ">> Local tags verified:"
  docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}' | grep -E "^${USERNAME}/${IMAGE}\s"

  echo ">> Done (local only, not pushed)!"
  echo "   Run with:"
  echo "     docker run --rm -p 5000:5000 ${FULL_VERSION_TAG}"
  exit 0
fi

# --- Multi-arch: build and push in one step ---
echo ">> buildx build --push (multi-arch manifest)"
docker buildx build "${BUILD_ARGS[@]}" --push ..

# --- Verify the pushed manifest in the registry ---
echo ">> Verifying pushed manifest..."
docker buildx imagetools inspect "${FULL_VERSION_TAG}"

echo ">> Done!"
echo "   Pull with:"
echo "     docker pull ${FULL_VERSION_TAG}"
if [[ "${PUSH_LATEST}" == "true" ]]; then
  echo "     docker pull ${FULL_LATEST_TAG}"
fi
