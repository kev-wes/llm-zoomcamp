# Monitoring, explained (module 5 companion)

This project implements the full module 5 monitoring pattern. If you haven't
worked through that module yet, this page explains *what* is monitored,
*why*, and *where* each concept lives in this repo.

## Why monitoring at all?

The evaluation notebooks measure quality **offline**: fixed questions, known
correct answers. Real users are different — they ask messy questions, about
topics you didn't sample, at unpredictable volume. Monitoring is the
**online** counterpart: observe the live system, so you notice quality
regressions, cost spikes, and unhappy users.

The standard recipe (and what this project does):

| Step | Course lesson | Where in this project |
|---|---|---|
| 1. Log every LLM interaction | 5.4 "Capturing metrics", 5.5 "Database" | `Build Record` + `Log Conversation` nodes in [rag-agent.json](../n8n/workflows/rag-agent.json) → `conversations` table ([init.sql](../postgres/init.sql)) |
| 2. Track cost & latency | 5.4 | `latency_ms`, `prompt_tokens`, `completion_tokens`, `cost_usd` columns (estimates — see below) |
| 3. Collect explicit user feedback | 5.8 "User feedback" | 👍/👎 buttons in [streamlit/app.py](../streamlit/app.py) → feedback webhook → `feedback` table |
| 4. Add an automatic quality signal | 5.9 "Built-in judge" | `Judge Answer` → `Parse Verdict` → `Save Verdict` nodes: an LLM classifies every live answer as RELEVANT / PARTLY_RELEVANT / NON_RELEVANT, *after* the user already got their response |
| 5. Visualize on a dashboard | 5.7 / 5.10 / 5.12 "Grafana" | auto-provisioned [Grafana dashboard](../grafana/dashboards/docs-assistant.json), 7 panels |
| 6. Run it all together | 5.13 "Docker Compose" | [docker-compose.yaml](../docker-compose.yaml) |

## What each dashboard panel tells you

Open http://localhost:3000 (login from `.env`, default `admin`/`admin`):

1. **Conversations per hour** — usage. Sudden drops often mean the app is
   down; spikes may mean cost.
2. **User feedback** — the ratio of 👍 to 👎. The most honest quality signal
   you have, but sparse (few users click).
3. **Answer relevance (LLM judge)** — automatic quality on *every* answer.
   Dense but less reliable than humans; watch the trend, not single values.
4. **Answer latency (avg / p95)** — p95 matters more than avg: it's what
   slow-side users experience. Agent loops with many tool calls push it up.
5. **Token usage per day** — input vs output volume; the driver of cost.
6. **Estimated cost** — sum over the selected time range.
7. **Recent conversations** — raw data for spot-checking: read what users
   actually asked and what the bot said. The fastest way to find failure
   modes.

## Design decisions worth knowing

- **The judge runs *after* the webhook response.** In the n8n workflow the
  `Respond` node comes before the judge nodes, so users never wait for the
  evaluation. The verdict is written to the same row later (`relevance` is
  `PENDING`/`NULL` until then).
- **Token numbers are estimates.** n8n's Agent node doesn't expose the exact
  API usage, so the workflow estimates tokens (~4 chars/token, plus a fixed
  allowance for the system prompt and retrieved context) in the
  `Build Record` code node. Good enough for trends and rough cost; the
  notebooks use exact API usage where precision matters.
- **One Postgres for everything.** Vectors (`n8n_vectors`), monitoring
  tables, and n8n's own state (separate `n8n` database) share one container.
  Simple for a project; in production you'd likely split them.

## Generating some traffic

Dashboards are boring when empty. Ask a handful of questions in the
Streamlit UI (http://localhost:8501), click a few 👍/👎, then refresh
Grafana. For bulk synthetic traffic, loop over ground-truth questions:

```bash
uv run python - <<'EOF'
import pandas as pd, requests, random
qs = pd.read_csv("data/ground-truth.csv").question.sample(10, random_state=7)
for q in qs:
    r = requests.post("http://localhost:5678/webhook/chat", json={"question": q}, timeout=180).json()
    requests.post("http://localhost:5678/webhook/feedback",
                  json={"conversation_id": r["conversation_id"], "feedback": random.choice([1, 1, -1])})
    print("ok:", q[:60])
EOF
```
