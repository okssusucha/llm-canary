# llm-canary

[![CI](https://github.com/okssusucha/llm-canary/actions/workflows/ci.yml/badge.svg)](https://github.com/okssusucha/llm-canary/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)

**Regression canary for LLM apps in CI**: declarative YAML test suites for
prompts, baseline drift detection without golden answers, and policy gates
for agent traces (tool order, cost budgets, runaway loops). Use it as a CLI
in CI, or **self-host it as a service** with run history, a dashboard, and
team-shared baselines. Offline-first — the whole test suite and the bundled
examples run with **zero API keys**.

**CI で動く LLM アプリの回帰カナリア**。プロンプトのテストを YAML で宣言し、
正解データなしでベースラインからのドリフトを検知、さらにエージェントの
トレース（ツール呼び出し順・コスト予算・無限ループ）をポリシーで検査します。
CI 内の CLI としても、実行履歴・ダッシュボード・チーム共有ベースラインを持つ
**セルフホスト型サービス**としても使えます。オフラインファースト設計で、
テストもサンプルも **APIキーなし** で動きます。

---

## Why / なぜ必要か

**EN**

- **Prompt changes are silent regressions.** A one-line prompt tweak can break
  JSON output, leak text it shouldn't, or double your token bill — and nothing
  in a normal CI pipeline notices. `llm-canary run` turns those into failing
  builds.
- **You rarely have golden answers.** LLM output isn't byte-stable, so snapshot
  tests don't work. `record`/`check` compares against a baseline with semantic
  similarity and cost-drift thresholds instead of exact matches.
- **Agents act; outputs aren't enough.** In 2026 the risk moved from "what did
  the model say" to "what did the agent do". `trace` gates a JSONL action log
  against a policy: forbidden tools, required ordering, step/cost budgets,
  loop detection.

**JA**

- **プロンプト変更は静かなデグレ。** 1行の修正で JSON 出力が壊れたり、出すべき
  でない文言が混ざったり、トークン費用が倍になっても、普通の CI は気づきません。
  `llm-canary run` がそれをビルド失敗に変えます。
- **正解データは普通ない。** LLM の出力はバイト単位では安定しないため、スナップ
  ショットテストは機能しません。`record`/`check` は完全一致ではなく、意味的
  類似度とコストドリフトの閾値でベースラインと比較します。
- **エージェントは「行動」する。** 2026年のリスクは「何を言ったか」から「何を
  したか」へ移りました。`trace` は JSONL の行動ログをポリシー（禁止ツール・
  実行順序・ステップ/コスト予算・ループ検知）で検査します。

---

## Quickstart / クイックスタート

```bash
# install (Python 3.11+)
uv tool install llm-canary    # or: pip install llm-canary
# from source: git clone && uv sync && uv run llm-canary ...

# scaffold and run a starter suite — works offline, no keys
llm-canary init
llm-canary run canary.yaml

# the bundled, fully offline example suite
llm-canary run canary.example.yaml

# check an agent trace against a policy
llm-canary trace examples/agent-trace/trace.jsonl \
  --policy examples/agent-trace/policy.yaml
```

Exit code is `0` when everything passes, `1` on failures — drop it straight
into CI. / 全て成功で終了コード `0`、失敗で `1`。そのまま CI に組み込めます。

---

## Suite YAML / スイート定義

```yaml
name: support-bot
providers:
  - name: openai            # echo / fixture / openai / anthropic
    model: gpt-4o-mini
judge:                      # optional: provider used by `judge` assertions
  name: anthropic
  model: claude-haiku-4-5
cases:
  - name: refund-policy
    prompt: "A customer asks: can I get a refund for {product}?"
    vars:
      product: "a keyboard bought 2 weeks ago"
    assertions:
      - type: contains
        value: "30 days"
      - type: json_schema
        value: {type: object, required: [eligible]}
      - type: judge
        value: "Politely explains the refund policy"
        threshold: 0.7
      - type: max_cost_usd
        value: 0.01
```

### Assertions / アサーション一覧

| type | checks / 内容 |
|---|---|
| `contains` / `not_contains` | substring (opt. `case_insensitive`) / 部分文字列 |
| `regex` | pattern match / 正規表現 |
| `equals` | exact match, whitespace-trimmed / 完全一致 |
| `json_valid` | parseable JSON (handles ``` fences & prose) / JSON妥当性 |
| `json_schema` | JSON Schema validation / スキーマ検証 |
| `similarity` | semantic similarity vs reference (`threshold`) / 意味的類似度 |
| `judge` | LLM-as-judge score vs criteria (`threshold`) / LLM評価 |
| `max_latency_ms` / `max_cost_usd` / `max_output_tokens` | budget gates / 予算ゲート |

### Providers / プロバイダ

- `echo` — returns the prompt; deterministic, free, offline. / プロンプトを
  そのまま返すオフライン用
- `fixture` — regex-routed canned replies; ideal for offline demos and as an
  offline judge. / 正規表現で固定応答を返す。オフラインのジャッジにも使える
- `openai` / `anthropic` — real APIs via `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
  (`base_url` option points `openai` at any OpenAI-compatible endpoint)
- `command` / `http` — **your actual bot**, whatever it is (see below) /
  **あなたの本物のボット**を対象にする(下記)
- Cost is estimated from a built-in price table — good enough for budget
  gates. / コストは内蔵価格表からの概算

---

## Test YOUR bot, not the raw model / 素のモデルではなく「あなたのボット」を検査する

A canary is only meaningful if the thing you change — your system prompt,
your RAG pipeline, your pre/post-processing — is on the execution path. The
`command` and `http` providers put your real application under test, however
it is built. / カナリアが意味を持つのは、あなたが変更するもの（システム
プロンプト・RAG・前後処理）が実行経路に乗っているときだけです。`command` /
`http` プロバイダは、どんな作りのアプリでも「本物」をテスト対象にします。

**`command` — anything executable / 実行できるものなら何でも**(Python, Node,
Go, shell, …). The prompt replaces `{prompt}` in the arguments — or is piped
to stdin when there is no placeholder — and stdout is the reply:

```yaml
providers:
  - name: command
    options:
      cmd: "python my_bot.py --ask {prompt}"   # or just "python my_bot.py" (stdin)
```

**`http` — anything with an HTTP API / HTTP APIを持つものなら何でも**.
`{prompt}` is substituted into the body/params/url; the reply is extracted
from the response JSON with a dot path:

```yaml
providers:
  - name: http
    options:
      url: http://localhost:8000/chat
      body: {message: "{prompt}", session: "ci"}
      response_path: reply.text          # or e.g. choices.0.message.content
      headers: {Authorization: "Bearer ${BOT_TOKEN}"}
```

In CI, boot your bot and point the canary at it / CIではボットを起動して
カナリアを向けるだけ:

```yaml
- run: docker compose up -d my-chatbot
- run: llm-canary run suite.yaml        # http provider hits the real stack
```

> **Security / セキュリティ**: the `command` provider executes processes, so
> the self-hosted server rejects it unless started with
> `llm-canary serve --allow-command` (or `CANARY_ALLOW_COMMAND=1`). /
> `command` はプロセスを実行するため、セルフホストサーバーでは既定で拒否され、
> `--allow-command` での明示的な許可が必要です。

---

## Baseline drift / ベースラインドリフト

```bash
llm-canary record canary.yaml          # snapshot outputs + costs
llm-canary check canary.yaml           # rerun and gate on drift
llm-canary check canary.yaml --similarity-threshold 0.85 --cost-drift 0.1
```

`check` fails when an output's semantic similarity to the baseline drops below
the threshold, or cost grows beyond the allowed ratio. The default embedder is
a deterministic offline hash embedder (pluggable). /
`check` は出力の類似度が閾値を下回るか、コストが許容比率を超えて増えたときに
失敗します。既定の埋め込みは決定的なオフラインのハッシュ埋め込み（差し替え可）。

---

## Agent trace gates / エージェントトレース検査

```jsonl
{"type": "tool_call", "tool": "query_sales_db", "cost_usd": 0.002}
{"type": "tool_call", "tool": "post_slack", "cost_usd": 0.001}
```

```yaml
# policy.yaml
max_steps: 10
max_cost_usd: 0.05
forbidden_tools: [delete_records, send_email]
required_order: [query_sales_db, post_slack]
max_tool_repeats: 3        # catch runaway loops
```

```bash
llm-canary trace trace.jsonl --policy policy.yaml
```

Emit one JSON object per agent step from your framework of choice and gate it
in CI. / 任意のフレームワークからステップごとに JSON を1行出力し、CI で
ゲートします。

---

## Self-hosting / セルフホスティング

Run llm-canary as a service inside your own infrastructure. Suites, outputs,
traces, and baselines are stored in a local SQLite file — **prompts and agent
logs never leave your network** (except calls to providers you explicitly
configure). / llm-canary を自社インフラ内のサービスとして常駐させられます。
スイート・出力・トレース・ベースラインはローカルの SQLite に保存され、
**プロンプトもエージェントログも社外に出ません**（明示的に設定したモデル
プロバイダへの呼び出しを除く）。

```bash
docker compose up -d          # serves on :8080, history persisted in a volume
# or without Docker:
pip install 'llm-canary[server]'
llm-canary serve --port 8080
```

Teams and CI jobs talk to it over HTTP / チームや CI からは HTTP で:

```bash
# run a suite (body = suite spec as JSON)
curl -X POST localhost:8080/api/runs -H 'content-type: application/json' \
  -d @suite.json

# gate an agent trace
curl -X POST localhost:8080/api/traces/check -H 'content-type: application/json' \
  -d '{"steps": [...], "policy": {"forbidden_tools": ["delete_records"]}}'

# record a team-shared baseline, then check drift against it
curl -X PUT  localhost:8080/api/baselines/main -d @suite.json \
  -H 'content-type: application/json'
curl -X POST localhost:8080/api/baselines/main/check -d '{"suite": ...}' \
  -H 'content-type: application/json'
```

- `GET /` — dashboard with run history / 実行履歴ダッシュボード
- `GET /api/runs`, `GET /api/runs/{id}` — history & full detail / 履歴と詳細
- `GET /healthz` — liveness probe

Baselines live on the server, so the whole team (and every CI job) gates
against the **same** baseline instead of per-machine files. /
ベースラインはサーバー側に保存されるため、チーム全員とすべての CI ジョブが
**同一の**ベースラインに対して検査できます（マシンごとのファイル管理が不要）。

---

## GitHub Actions

```yaml
- name: LLM regression gate
  run: |
    uv run llm-canary run canary.yaml --junit junit.xml --md summary.md
    uv run llm-canary trace trace.jsonl --policy policy.yaml
```

`--junit` integrates with test reporters; `--md` is ready to post as a PR
comment. / `--junit` はテストレポーター連携用、`--md` は PR コメント投稿用。

---

## Architecture / アーキテクチャ

```
suite YAML ─▶ runner ─▶ provider (echo | fixture | openai | anthropic)
                │              │
                ▼              ▼
           assertions ◀── completion {text, tokens, cost, latency}
                │
                ├─▶ reports: console / JUnit XML / Markdown
                └─▶ baseline: record / drift check (hash embedder)

trace JSONL ─▶ policy checks ─▶ violations (exit 1)
```

- `src/llm_canary/config.py` — pydantic specs for suites & policies
- `src/llm_canary/providers/` — provider registry (offline + remote)
- `src/llm_canary/assertions/` — assertion registry (basic + quality)
- `src/llm_canary/baseline.py` — snapshot & drift detection
- `src/llm_canary/trace.py` — agent-trace policy engine
- `src/llm_canary/report.py` — console / JUnit / Markdown reporters
- `src/llm_canary/server.py` — self-hosted FastAPI server (REST + dashboard)
- `src/llm_canary/storage.py` — SQLite history & team-shared baselines

## Development / 開発

```bash
uv sync
uv run pytest          # entire suite is offline — no keys, no network
uv run ruff check .
```

## License

MIT
