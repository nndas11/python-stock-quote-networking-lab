#!/usr/bin/env bash
set -eu
cd -- "$(dirname -- "$0")"
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
exec .venv/bin/python stock_quotes.py "$@"
