"""
Phase 0 spike: prove Mesh API connectivity before anything else is built on it.

One embeddings.create call + one chat.completions.create call, both routed
through Mesh via the OpenAI SDK. Throwaway — superseded by app/services/
llm_client.py in Phase 2.
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MESH_BASE_URL = "https://api.meshapi.ai/v1"
EMBED_MODEL = "sentence-transformers/all-minilm-l6-v2"
CHAT_MODEL = "openai/chat-latest"


def main() -> None:
    api_key = os.environ.get("MESH_API_KEY")
    if not api_key:
        print("MESH_API_KEY is not set — add it to .env", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(base_url=MESH_BASE_URL, api_key=api_key)

    print(f"--- Embedding call ({EMBED_MODEL}) ---")
    embedding_response = client.embeddings.create(
        model=EMBED_MODEL,
        input=["SmartReco recommends courses based on real user behavior."],
    )
    vector = embedding_response.data[0].embedding
    print(f"OK - received a {len(vector)}-dim vector. First 5 values: {vector[:5]}")

    print(f"\n--- Chat completion call ({CHAT_MODEL}) ---")
    chat_response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "user",
                "content": "In one sentence, what is retrieval-augmented generation?",
            }
        ],
    )
    print(f"OK - {chat_response.choices[0].message.content}")

    print("\nMesh spike succeeded: both embeddings and chat completions work.")


if __name__ == "__main__":
    main()
