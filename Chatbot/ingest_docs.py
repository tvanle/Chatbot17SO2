"""
Script to ingest documents from Chatbot/assets/raw into RAG system
"""
import os
import sys
import requests
import time
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# API endpoint
API_URL = "http://127.0.0.1:8000/api/rag/ingest"
NAMESPACE = "ptit_docs"

def ingest_document(file_path: Path):
    """Ingest a single document"""
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract title from filename
        title = file_path.stem.replace('_', ' ')

        # Prepare request
        payload = {
            "namespace_id": NAMESPACE,
            "document_title": title,
            "content": content
        }

        # Send request
        print(f"📄 Ingesting: {title}...", end=" ")
        response = requests.post(API_URL, json=payload)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! (doc_id: {result['doc_id']}, chunks: {result['chunk_count']})")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Main ingestion flow"""
    print("🚀 Starting document ingestion from Chatbot/assets/raw\n")

    # Get all markdown files
    raw_dir = Path("Chatbot/assets/raw")
    md_files = list(raw_dir.glob("*.md"))

    print(f"📚 Found {len(md_files)} documents to ingest\n")

    # Ingest each file
    success_count = 0
    fail_count = 0

    for i, file_path in enumerate(md_files, 1):
        print(f"[{i}/{len(md_files)}] ", end="")
        if ingest_document(file_path):
            success_count += 1
        else:
            fail_count += 1
        time.sleep(0.5)  # Rate limiting

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Successfully ingested: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📊 Total: {len(md_files)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
