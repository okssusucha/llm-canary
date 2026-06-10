# Security Policy

## Reporting a vulnerability

Please report vulnerabilities privately via
[GitHub Security Advisories](https://github.com/okssusucha/llm-canary/security/advisories/new)
rather than opening a public issue. You should receive a response within a
week.

## Deployment notes

- **`command` provider = process execution.** Suites using it run arbitrary
  executables on the host. The self-hosted server therefore rejects such
  suites unless started with `--allow-command`. Never enable
  `--allow-command` on a server reachable by untrusted clients — that is
  remote code execution by design.
- **Protect the server.** `llm-canary serve` binds to `127.0.0.1` by default.
  If you expose it on a network, set a token (`--token` / `CANARY_TOKEN`) and
  put it behind TLS (reverse proxy).
- **Secrets stay in the environment.** API keys are read from environment
  variables; `${ENV_VAR}` expansion in `http` provider headers exists so
  tokens never need to appear in suite YAML. Don't commit keys into suites.
- **Stored data.** Outputs, traces, and baselines are stored in plain SQLite.
  Treat the database file with the same sensitivity as the prompts and
  outputs it contains.
