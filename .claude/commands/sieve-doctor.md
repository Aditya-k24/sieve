---
description: Run Sieve's environment/health checks
allowed-tools: Bash(*)
---

<!-- Non-interactive shells here don't source ~/.zshrc (where 'sieve on'
persists the PATH line), so the PATH-order check would false-negative
without this prefix. -->
!`export PATH="$HOME/.sieve/bin:$PATH" && ./.venv/bin/sieve doctor`
