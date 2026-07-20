# Convenience commands - see README.md for the full walkthrough.

.PHONY: prepare-data up down logs ingest ask psql

# Download the pinned n8n docs subset and chunk it into data/chunks.json
prepare-data:
	uv run python ingestion/download_docs.py
	uv run python ingestion/prepare_chunks.py

# Build and start the whole stack (n8n, Postgres, Grafana, Streamlit)
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f n8n

# Trigger the n8n ingestion workflow (embeds chunks into pgvector)
ingest:
	curl -s -X POST http://localhost:5678/webhook/ingest && echo " ingestion started - watch: make logs"

# Ask a test question via the API
ask:
	curl -s -X POST http://localhost:5678/webhook/chat \
		-H 'Content-Type: application/json' \
		-d '{"question": "How do I loop over items in n8n?"}' | python3 -m json.tool

# Open a psql shell on the project database
psql:
	docker compose exec postgres psql -U docs_assistant -d docs_assistant
