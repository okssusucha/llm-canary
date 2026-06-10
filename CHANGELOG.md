# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/).

## [0.4.0] - 2026-06-10

### Added
- `matrix:` on cases — expand one case into the cartesian product of variable
  axes (`greet[hello,ja]`, `greet[hello,ko]`, …).
- `--max-workers` on `run` / `record` / `check` for concurrent case execution.
- `system_prompt` / `system_prompt_file` options on the `openai` and
  `anthropic` providers — point `system_prompt_file` at the same file your
  app uses so the prompt under change is actually on the tested path.
- `llm-canary validate` — lint a suite (unknown providers/assertions, missing
  judge) without calling any provider.
- `--json` on `run` for machine-readable results.
- Server token auth: `llm-canary serve --token <t>` (or `CANARY_TOKEN`)
  requires `Authorization: Bearer <t>` on everything except `/healthz`.
- Colored PASS/FAIL console output on TTYs.

### Fixed
- Prompts containing literal braces (JSON examples, code) no longer crash
  variable rendering.
- `json_valid` / `json_schema` now tolerate trailing prose after the JSON
  payload ("… } Hope that helps!").

## [0.3.0] - 2026-06-10

### Added
- `command` provider — test any executable bot: `{prompt}` substitution in
  args, or stdin when no placeholder; stdout is the reply.
- `http` provider — test any REST bot: recursive `{prompt}` substitution,
  dot-path response extraction, `${ENV_VAR}` expansion in headers.
- Server guard: suites using `command` are rejected unless the server is
  started with `--allow-command` / `CANARY_ALLOW_COMMAND=1`.

## [0.2.0] - 2026-06-10

### Added
- Self-hosted server mode: `llm-canary serve` (FastAPI + SQLite), REST API
  for runs / trace checks / team-shared baselines, run-history dashboard,
  Dockerfile and docker-compose.

## [0.1.0] - 2026-06-10

### Added
- Initial release: YAML suites, 11 assertion types, offline `echo`/`fixture`
  providers, `openai`/`anthropic` providers, baseline record/check with
  offline hash-embedder similarity, agent-trace policy gates, console /
  JUnit / Markdown reporters, GitHub Actions integration.
