#!/usr/bin/env bash
# Thin wrapper: removes the Sieve shim (same as `sieve off`).
set -euo pipefail
exec sieve off
