# Contributing to llm-canary

Thanks for considering a contribution! Issues and PRs are welcome in English
or Japanese. / コントリビュート歓迎です。Issue・PRは英語でも日本語でもどうぞ。

## Development setup

```bash
git clone https://github.com/okssusucha/llm-canary
cd llm-canary
uv sync          # installs everything, including dev tools
uv run pytest    # the whole suite runs offline in <1s
uv run ruff check .
```

## Ground rules

- **Tests must run offline.** No API keys, no network. Mock remote providers
  with `respx`; use the `echo`/`fixture` providers everywhere else. If your
  feature can't be tested offline, redesign it until it can.
- **Keep dependencies minimal.** Core stays at pydantic / pyyaml / httpx /
  jsonschema; server extras stay behind `llm-canary[server]`.
- **One behavior per PR**, with a test that fails before and passes after.
- Run `uv run ruff check .` and `uv run pytest` before pushing — CI enforces
  both on Python 3.11 and 3.12.

## Where things live

See the Architecture section of the README. Quick orientation: providers are
registered in `src/llm_canary/providers/__init__.py`, assertions in
`src/llm_canary/assertions/__init__.py` — adding either is usually a single
function plus a registry entry plus tests.

## Releases (maintainers)

1. Update `version` in `pyproject.toml` and `src/llm_canary/__init__.py`,
   add a CHANGELOG entry.
2. Tag: `git tag v0.x.0 && git push --tags`.
3. The `release.yml` workflow builds and publishes to PyPI via trusted
   publishing (requires the PyPI project to be configured for this repo).
