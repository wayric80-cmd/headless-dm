#!/bin/sh
# Installs the Classic-trimmed module RAG plus Way of Vanilla own facts. Restart wow-world afterwards.
set -e
cd "$(dirname "$0")/.."
D=/opt/wow/server/data/ollama-rag
python3 wov/rag_classic.py src/modules/mod-ollama-chat/data/rag $D
python3 wov/rag_classic.py wov/rag $D
