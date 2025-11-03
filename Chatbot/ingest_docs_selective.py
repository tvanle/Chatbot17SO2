#!/usr/bin/env python3
"""
Script để ingest documents từ Chatbot/assets/raw vào Qdrant
Hỗ trợ:
1. Ingest TẤT CẢ documents: python3 Chatbot/ingest_docs_selective.py
2. Ingest TỰ CHỌN: python3 Chatbot/ingest_docs_selective.py -f file1.md file2.md
3. Liệt kê files: python3 Chatbot/ingest_docs_selective.py -l
4. Ingest cụ thể: python3 Chatbot/ingest_docs_selective.py SuKien_PTIT_2025.md NhanSu_PTIT_2024-2025.md
"""
import os
import sys
import requests
import time
import argparse
from pathlib import Path
from typing import List, Dict

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
API_URL = "http://127.0.0.1:8000/api/rag/ingest"
NAMESPACE = "ptit_docs"
RAW_DIR = Path("Chatbot/assets/raw")


def list_available_files():
    """Liệt kê tất cả markdown files có sẵn"""
    if not RAW_DIR.exists():
        print(f"❌ Thư mục không tồn tại: {RAW_DIR.absolute()}")
        return []
    
    md_files = sorted(list(RAW_DIR.glob("*.md")))
    
    if not md_files:
        print(f"⚠️  Không tìm thấy file .md nào trong {RAW_DIR}")
        return []
    
    print(f"\n📚 Có {len(md_files)} documents sẵn sàng:\n")
    for i, file in enumerate(md_files, 1):
        size_kb = file.stat().st_size / 1024
        print(f"  {i}. {file.name:<50} ({size_kb:.1f} KB)")
    
    return md_files


def read_document(file_path: Path) -> str:
    """Đọc nội dung document từ file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        print(f"❌ File không tìm thấy: {file_path}")
        return None
    except Exception as e:
        print(f"❌ Lỗi đọc file: {str(e)}")
        return None


def ingest_document(file_name: str) -> Dict:
    """
    Ingest một document duy nhất qua API
    
    Args:
        file_name: Tên file cần ingest
        
    Returns:
        Dict với kết quả ingest
    """
    file_path = RAW_DIR / file_name
    
    # Kiểm tra file tồn tại
    if not file_path.exists():
        print(f"❌ File không tồn tại: {file_name}")
        return {
            "success": False,
            "file": file_name,
            "error": "File not found"
        }
    
    # Đọc nội dung
    content = read_document(file_path)
    if not content:
        return {
            "success": False,
            "file": file_name,
            "error": "Failed to read file"
        }
    
    # Tạo title từ filename
    title = file_name.replace('_', ' ').replace('.md', '')
    
    # Chuẩn bị payload request
    payload = {
        "namespace_id": NAMESPACE,
        "document_title": title,
        "content": content
    }
    
    try:
        print(f"📄 Ingesting: {title}...", end=" ", flush=True)
        
        response = requests.post(
            API_URL,
            json=payload,
            timeout=120  # 2 minutes timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success!")
            print(f"   📊 Doc ID: {result.get('doc_id')}")
            print(f"   📝 Chunks: {result.get('chunk_count')}")
            return {
                "success": True,
                "file": file_name,
                "doc_id": result.get('doc_id'),
                "chunk_count": result.get('chunk_count')
            }
        else:
            error_msg = response.text
            print(f"❌ Failed ({response.status_code})")
            print(f"   Error: {error_msg[:100]}...")
            return {
                "success": False,
                "file": file_name,
                "status_code": response.status_code,
                "error": error_msg
            }
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error")
        print(f"   Chắc chắn API server chạy trên {API_URL}")
        return {
            "success": False,
            "file": file_name,
            "error": f"Cannot connect to {API_URL}"
        }
    except requests.exceptions.Timeout:
        print(f"❌ Timeout")
        return {
            "success": False,
            "file": file_name,
            "error": "Request timeout"
        }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "success": False,
            "file": file_name,
            "error": str(e)
        }


def main():
    """Main ingestion flow"""
    parser = argparse.ArgumentParser(
        description="Ingest documents vào Qdrant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python3 Chatbot/ingest_docs_selective.py
    → Ingest TẤT CẢ documents

  python3 Chatbot/ingest_docs_selective.py -l
    → Liệt kê tất cả documents

  python3 Chatbot/ingest_docs_selective.py SuKien_PTIT_2025.md NhanSu_PTIT_2024-2025.md
    → Ingest 2 documents cụ thể

  python3 Chatbot/ingest_docs_selective.py -f file1.md file2.md
    → Ingest documents từ danh sách
        """
    )
    
    parser.add_argument(
        'files',
        nargs='*',
        help='Tên files cần ingest (nếu không chỉ định sẽ ingest tất cả)'
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='Liệt kê tất cả documents có sẵn'
    )
    parser.add_argument(
        '-f', '--files',
        nargs='+',
        help='Danh sách files cần ingest'
    )
    
    args = parser.parse_args()
    
    # Nếu chọn -l, chỉ liệt kê
    if args.list:
        list_available_files()
        return 0
    
    print("=" * 70)
    print("🚀 INGESTING DOCUMENTS INTO QDRANT")
    print("=" * 70)
    print(f"API URL: {API_URL}")
    print(f"Namespace: {NAMESPACE}")
    print(f"Raw Dir: {RAW_DIR.absolute()}")
    print("=" * 70 + "\n")
    
    # Kiểm tra thư mục tồn tại
    if not RAW_DIR.exists():
        print(f"❌ Error: Thư mục không tồn tại: {RAW_DIR.absolute()}")
        sys.exit(1)
    
    # Xác định files cần ingest
    if args.files:
        # Nếu dùng -f option
        files_to_ingest = args.files
    elif args.files is None and len(args.files) > 0:
        # Nếu truyền positional arguments
        files_to_ingest = args.files
    else:
        # Ingest TẤT CẢ nếu không chỉ định
        all_md_files = list(RAW_DIR.glob("*.md"))
        if not all_md_files:
            print("⚠️  Không tìm thấy markdown files nào để ingest")
            return 1
        files_to_ingest = [f.name for f in sorted(all_md_files)]
    
    if not files_to_ingest:
        print("❌ Không có files để ingest!")
        return 1
    
    # Ingest documents
    results = []
    for i, file_name in enumerate(files_to_ingest, 1):
        print(f"[{i}/{len(files_to_ingest)}] ", end="")
        result = ingest_document(file_name)
        results.append(result)
        print()  # New line
    
    # Summary
    print("=" * 70)
    print("📊 INGESTION SUMMARY")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count
    total_chunks = sum(r.get("chunk_count", 0) for r in results if r["success"])
    
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['file']}")
        if result["success"]:
            print(f"   └─ Doc ID: {result.get('doc_id')}, Chunks: {result.get('chunk_count')}")
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"   └─ Error: {error_msg[:60]}...")
    
    print("-" * 70)
    print(f"✅ Successfully ingested: {success_count}/{len(results)}")
    print(f"❌ Failed: {fail_count}/{len(results)}")
    print(f"📝 Total chunks created: {total_chunks}")
    print("=" * 70)
    
    # Return exit code
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
