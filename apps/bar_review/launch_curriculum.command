#!/bin/zsh
# Finder / Terminal launcher using this checkout's Python environment.
set -eu
curriculum_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$curriculum_root"
if [[ ! -x .venv/bin/python ]]; then
    print -u2 'Create the project environment first: uv sync --extra desktop'
    exit 1
fi
if [[ -f /opt/homebrew/lib/libcairo.2.dylib ]]; then
    export DYLD_FALLBACK_LIBRARY_PATH="${DYLD_FALLBACK_LIBRARY_PATH:-/opt/homebrew/lib}"
fi
export MPLCONFIGDIR="${MPLCONFIGDIR:-${TMPDIR:-/tmp}/musvit-matplotlib}"
exec .venv/bin/python apps/bar_review/desktop.py "$@"
