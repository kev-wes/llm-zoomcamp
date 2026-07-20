#!/bin/sh
# One-shot init container: seeds n8n with credentials and workflows.
#
# Credentials are generated from environment variables (see .env) so no
# secrets ever land in the repository. Workflows are imported from the
# JSON files in n8n/workflows/ and activated.
set -e

CRED_FILE="/tmp/credentials.json"

cat > "$CRED_FILE" <<EOF
[
  {
    "id": "openaidocsassist",
    "name": "OpenAI Docs Assistant",
    "type": "openAiApi",
    "data": {
      "apiKey": "${OPENAI_API_KEY}"
    }
  },
  {
    "id": "pgdocsassistant1",
    "name": "Docs Assistant Postgres",
    "type": "postgres",
    "data": {
      "host": "postgres",
      "port": 5432,
      "database": "${POSTGRES_DB}",
      "user": "${POSTGRES_USER}",
      "password": "${POSTGRES_PASSWORD}",
      "ssl": "disable",
      "sshTunnel": false
    }
  }
]
EOF

echo "Importing credentials..."
n8n import:credentials --input="$CRED_FILE"
rm -f "$CRED_FILE"

echo "Importing workflows..."
n8n import:workflow --separate --input=/import/workflows

# Publish (= activate) each workflow. The ids are pinned in the JSON files.
echo "Publishing workflows..."
n8n publish:workflow --id=IngestDocs000001
n8n publish:workflow --id=RagAgentApi00001
n8n publish:workflow --id=Feedback00000001

echo "n8n import complete."
