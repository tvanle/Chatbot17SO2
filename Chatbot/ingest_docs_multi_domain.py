#!/usr/bin/env python3
"""
ENHANCED Multi-Domain Document Ingestion Script

Tự động phân loại documents vào các domain categories:
- admission: Tuyển sinh
- tuition: Học phí
- regulations: Quy chế đào tạo
- general: Thông tin chung

Usage:
  python3 Chatbot/ingest_docs_multi_domain.py                    # Ingest all
  python3 Chatbot/ingest_docs_multi_domain.py -l                 # List files
  python3 Chatbot/ingest_docs_multi_domain.py file1.md file2.md  # Specific files
"""
import os
import sys
import requests
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
API_URL = "http://localhost:8000/api/rag/ingest"
RAW_DIR = Path("Chatbot/assets/raw")

# Domain classification rules
DOMAIN_RULES = {
    "admission": {
        "namespace": "ptit_admission",
        "keywords": [
            "tuyển sinh", "điểm chuẩn", "xét tuyển", "đăng ký xét tuyển",
            "phương thức tuyển sinh", "ngành học", "chỉ tiêu", "hồ sơ tuyển sinh",
            "admission", "điểm xét tuyển", "khối thi", "nguyện vọng"
        ],
        "filename_patterns": [
            "tuyen_sinh", "tuyensinh", "admission", "diem_chuan", "diemchuan",
            "xet_tuyen", "xettuyen"
        ]
    },
    "tuition": {
        "namespace": "ptit_tuition",
        "keywords": [
            "học phí", "chi phí", "lệ phí", "học bổng", "miễn giảm",
            "miễn học phí", "thu phí", "đóng học phí", "tín chỉ",
            "tuition", "phí đào tạo", "mức thu"
        ],
        "filename_patterns": [
            "hoc_phi", "hocphi", "tuition", "chi_phi", "chiphi",
            "hoc_bong", "hocbong", "scholarship"
        ]
    },
    "regulations": {
        "namespace": "ptit_regulations",
        "keywords": [
            "quy chế", "quy định", "điều kiện tốt nghiệp", "chương trình đào tạo",
            "học vụ", "thi cử", "điểm", "tích lũy tín chỉ", "cảnh báo học tập",
            "regulations", "quy trình", "thể lệ", "nội quy"
        ],
        "filename_patterns": [
            "quy_che", "quyche", "regulation", "quy_dinh", "quydinh",
            "dao_tao", "daotao", "hoc_vu", "hocvu"
        ]
    },
    "general": {
        "namespace": "ptit_docs",
        "keywords": [],  # Fallback category
        "filename_patterns": []
    }
}


def classify_document(file_path: Path, content: str) -> Dict:
    """
    Tự động phân loại document vào domain category

    Algorithm:
    1. Check filename patterns
    2. Count keyword matches in content
    3. Return category with highest score

    Args:
        file_path: Path to document
        content: Document content

    Returns:
        Dict with category, namespace, metadata
    """
    filename_lower = file_path.name.lower()
    content_lower = content.lower()

    # Score each domain
    scores = {}

    for domain, rules in DOMAIN_RULES.items():
        if domain == "general":
            continue  # Skip general (fallback)

        score = 0

        # Check filename patterns (weight: 5 points each)
        for pattern in rules["filename_patterns"]:
            if pattern in filename_lower:
                score += 5

        # Count keyword matches in content (weight: 1 point each)
        for keyword in rules["keywords"]:
            # Count occurrences
            count = content_lower.count(keyword)
            score += count

        scores[domain] = score

    # Find domain with highest score
    if scores:
        best_domain = max(scores.items(), key=lambda x: x[1])
        if best_domain[1] > 0:  # Must have at least 1 match
            category = best_domain[0]
            namespace = DOMAIN_RULES[category]["namespace"]

            # Extract metadata based on category
            metadata = extract_metadata(category, file_path, content)

            return {
                "category": category,
                "namespace": namespace,
                "metadata": metadata,
                "score": best_domain[1]
            }

    # Fallback to general
    return {
        "category": "general",
        "namespace": "ptit_docs",
        "metadata": {"source": file_path.name},
        "score": 0
    }


def extract_metadata(category: str, file_path: Path, content: str) -> Dict:
    """
    Extract domain-specific metadata from document

    Args:
        category: Domain category
        file_path: Path to document
        content: Document content

    Returns:
        Metadata dict
    """
    metadata = {
        "source": file_path.name,
        "ingested_at": datetime.now().isoformat()
    }

    # Extract year from filename or content
    import re

    # Try filename first: "TuyenSinh_2024.md"
    year_match = re.search(r'20\d{2}', file_path.name)
    if year_match:
        metadata["year"] = year_match.group(0)
    else:
        # Try content (first occurrence)
        year_match = re.search(r'năm\s+(20\d{2})', content[:1000], re.IGNORECASE)
        if year_match:
            metadata["year"] = year_match.group(1)

    # Category-specific metadata
    if category == "admission":
        metadata["tags"] = ["tuyển sinh"]
        if "điểm chuẩn" in content.lower():
            metadata["tags"].append("điểm chuẩn")
        if "ngành học" in content.lower():
            metadata["tags"].append("ngành học")

    elif category == "tuition":
        metadata["tags"] = ["học phí"]
        if "học bổng" in content.lower():
            metadata["tags"].append("học bổng")
        if "miễn giảm" in content.lower():
            metadata["tags"].append("miễn giảm")

        # Try to extract academic year
        ay_match = re.search(r'năm học\s+(20\d{2})[-\s]*(20\d{2})?', content[:1000], re.IGNORECASE)
        if ay_match:
            if ay_match.group(2):
                metadata["academic_year"] = f"{ay_match.group(1)}-{ay_match.group(2)}"
            else:
                metadata["academic_year"] = ay_match.group(1)

    elif category == "regulations":
        metadata["tags"] = ["quy chế"]
        if "tốt nghiệp" in content.lower():
            metadata["tags"].append("tốt nghiệp")
        if "điều kiện" in content.lower():
            metadata["tags"].append("điều kiện")

    return metadata


def list_available_files():
    """Liệt kê tất cả markdown files với domain classification preview"""
    if not RAW_DIR.exists():
        print(f"❌ Thư mục không tồn tại: {RAW_DIR.absolute()}")
        return []

    md_files = sorted(list(RAW_DIR.glob("*.md")))

    if not md_files:
        print(f"⚠️  Không tìm thấy file .md nào trong {RAW_DIR}")
        return []

    print(f"\n📚 Có {len(md_files)} documents sẵn sàng:\n")
    print(f"{'No.':<4} {'Filename':<40} {'Size':<10} {'Domain (predicted)':<20}")
    print("-" * 80)

    for i, file in enumerate(md_files, 1):
        size_kb = file.stat().st_size / 1024

        # Quick classification based on filename only
        filename_lower = file.name.lower()
        predicted_domain = "general"

        for domain, rules in DOMAIN_RULES.items():
            if domain == "general":
                continue
            for pattern in rules["filename_patterns"]:
                if pattern in filename_lower:
                    predicted_domain = domain
                    break
            if predicted_domain != "general":
                break

        # Color coding
        domain_colors = {
            "admission": "🎓",
            "tuition": "💰",
            "regulations": "📋",
            "general": "📄"
        }
        icon = domain_colors.get(predicted_domain, "📄")

        print(f"{i:<4} {file.name:<40} {size_kb:>8.1f} KB  {icon} {predicted_domain:<15}")

    print("-" * 80)
    return md_files


def read_document(file_path: Path) -> Optional[str]:
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
    Ingest một document với automatic domain classification

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

    # AUTO CLASSIFY DOMAIN
    classification = classify_document(file_path, content)

    # Tạo title từ filename
    title = file_name.replace('_', ' ').replace('.md', '')

    # Domain icons
    domain_icons = {
        "admission": "🎓",
        "tuition": "💰",
        "regulations": "📋",
        "general": "📄"
    }
    icon = domain_icons.get(classification["category"], "📄")

    # Chuẩn bị payload với category và metadata
    payload = {
        "namespace_id": classification["namespace"],
        "document_title": title,
        "content": content,
        "category": classification["category"],
        "metadata": classification["metadata"]
    }

    try:
        print(f"{icon} {classification['category'].upper():<12} | {title[:40]:<40}...", end=" ", flush=True)

        response = requests.post(
            API_URL,
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result.get('chunk_count')} chunks")
            return {
                "success": True,
                "file": file_name,
                "doc_id": result.get('doc_id'),
                "chunk_count": result.get('chunk_count'),
                "category": classification["category"],
                "namespace": classification["namespace"],
                "score": classification["score"]
            }
        else:
            error_msg = response.text
            print(f"❌ Error {response.status_code}")
            return {
                "success": False,
                "file": file_name,
                "status_code": response.status_code,
                "error": error_msg[:100]
            }

    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error")
        return {
            "success": False,
            "file": file_name,
            "error": f"Cannot connect to {API_URL}"
        }
    except Exception as e:
        print(f"❌ {str(e)[:50]}")
        return {
            "success": False,
            "file": file_name,
            "error": str(e)
        }


def main():
    """Main ingestion flow"""
    parser = argparse.ArgumentParser(
        description="🚀 Multi-Domain Document Ingestion with Auto-Classification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python3 Chatbot/ingest_docs_multi_domain.py
    → Ingest TẤT CẢ documents với auto domain classification

  python3 Chatbot/ingest_docs_multi_domain.py -l
    → Liệt kê documents và preview domain classification

  python3 Chatbot/ingest_docs_multi_domain.py TuyenSinh_2024.md HocPhi_2024.md
    → Ingest specific documents
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
        help='Liệt kê tất cả documents với domain classification preview'
    )

    args = parser.parse_args()

    # Nếu chọn -l, chỉ liệt kê
    if args.list:
        list_available_files()
        return 0

    print("=" * 80)
    print("🚀 MULTI-DOMAIN DOCUMENT INGESTION")
    print("=" * 80)
    print(f"API URL:  {API_URL}")
    print(f"Raw Dir:  {RAW_DIR.absolute()}")
    print(f"\nDomains:  🎓 admission | 💰 tuition | 📋 regulations | 📄 general")
    print("=" * 80 + "\n")

    # Kiểm tra thư mục tồn tại
    if not RAW_DIR.exists():
        print(f"❌ Error: Thư mục không tồn tại: {RAW_DIR.absolute()}")
        sys.exit(1)

    # Xác định files cần ingest
    if args.files:
        files_to_ingest = args.files
    else:
        # Ingest TẤT CẢ
        all_md_files = list(RAW_DIR.glob("*.md"))
        if not all_md_files:
            print("⚠️  Không tìm thấy markdown files nào để ingest")
            return 1
        files_to_ingest = [f.name for f in sorted(all_md_files)]

    if not files_to_ingest:
        print("❌ Không có files để ingest!")
        return 1

    print(f"📚 Ingesting {len(files_to_ingest)} documents...\n")

    # Ingest documents
    results = []
    for i, file_name in enumerate(files_to_ingest, 1):
        print(f"[{i}/{len(files_to_ingest)}] ", end="")
        result = ingest_document(file_name)
        results.append(result)
        time.sleep(0.3)  # Rate limiting

    # Summary by domain
    print("\n" + "=" * 80)
    print("📊 INGESTION SUMMARY")
    print("=" * 80)

    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count
    total_chunks = sum(r.get("chunk_count", 0) for r in results if r["success"])

    # Group by domain
    by_domain = {}
    for result in results:
        if result["success"]:
            category = result.get("category", "unknown")
            if category not in by_domain:
                by_domain[category] = []
            by_domain[category].append(result)

    print(f"\n📈 By Domain:")
    for domain in ["admission", "tuition", "regulations", "general"]:
        docs = by_domain.get(domain, [])
        if docs:
            domain_icons = {"admission": "🎓", "tuition": "💰", "regulations": "📋", "general": "📄"}
            icon = domain_icons.get(domain, "📄")
            chunks = sum(d.get("chunk_count", 0) for d in docs)
            print(f"  {icon} {domain.capitalize():<15}: {len(docs)} docs, {chunks} chunks")

    print(f"\n📋 Details:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['file']}")
        if result["success"]:
            print(f"   └─ Category: {result.get('category')}, Namespace: {result.get('namespace')}, Chunks: {result.get('chunk_count')}")
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"   └─ Error: {error_msg[:60]}")

    print("\n" + "-" * 80)
    print(f"✅ Successfully ingested: {success_count}/{len(results)}")
    print(f"❌ Failed: {fail_count}/{len(results)}")
    print(f"📝 Total chunks created: {total_chunks}")
    print("=" * 80)

    # Return exit code
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
