"""
AdmissionRAGService - RAG service specialized for admission-related queries
Handles: tuyển sinh, điểm chuẩn, xét tuyển, ngành học, chỉ tiêu
"""
from typing import List, Optional, Dict
from datetime import datetime

from .BaseRAGService import BaseRAGService


class AdmissionRAGService(BaseRAGService):
    """
    Domain service for PTIT admission queries

    Specializations:
    - Namespace: ptit_admission
    - Keywords: tuyển sinh, điểm chuẩn, xét tuyển, etc.
    - Preprocessing: Expand abbreviations, add current year context
    - Filtering: By admission year
    """

    # Class-level keywords (for domain routing without instantiation)
    DOMAIN_KEYWORDS = [
        "tuyển sinh",
        "điểm chuẩn",
        "xét tuyển",
        "đăng ký",
        "hồ sơ tuyển sinh",
        "ngành học",
        "chỉ tiêu",
        "phương thức xét tuyển",
        "thi tuyển",
        "thí sinh",
        "tuyển thẳng",
        "xét học bạ",
        "đăng ký xét tuyển",
        "nguyện vọng",
        "khối thi",
        "môn thi",
        "điểm xét tuyển"
    ]

    def get_namespace(self) -> str:
        """Namespace for admission documents"""
        return "ptit_admission"

    def get_domain_keywords(self) -> List[str]:
        """Keywords identifying admission domain"""
        return self.DOMAIN_KEYWORDS

    def get_domain_name(self) -> str:
        """Human-readable domain name"""
        return "Tuyển sinh"

    def preprocess_question(self, question: str) -> str:
        """
        Preprocess admission-specific questions

        Transformations:
        - Expand abbreviations: TS → tuyển sinh, ĐC → điểm chuẩn
        - Add current year context for temporal references
        - Normalize year formats
        """
        processed = question.strip()

        # Expand common abbreviations
        abbreviations = {
            " TS ": " tuyển sinh ",
            "TS.": "tuyển sinh",
            " ĐC ": " điểm chuẩn ",
            "ĐC.": "điểm chuẩn",
            " XT ": " xét tuyển ",
            "XT.": "xét tuyển",
            "ĐKXT": "đăng ký xét tuyển",
            "NV": "nguyện vọng"
        }

        for abbrev, full in abbreviations.items():
            processed = processed.replace(abbrev, full)

        # Add current year context
        current_year = datetime.now().year
        temporal_replacements = {
            "năm nay": f"năm {current_year}",
            "năm hiện tại": f"năm {current_year}",
            "năm tới": f"năm {current_year + 1}",
            "kỳ tuyển sinh này": f"kỳ tuyển sinh năm {current_year}"
        }

        for temporal, expanded in temporal_replacements.items():
            if temporal in processed.lower():
                # Case-insensitive replacement
                import re
                processed = re.sub(
                    re.escape(temporal),
                    expanded,
                    processed,
                    flags=re.IGNORECASE
                )

        return processed

    def get_search_filters(self) -> Optional[Dict]:
        """
        Filter by admission category and recent years
        Prioritize latest admission data
        """
        current_year = datetime.now().year

        # For admission queries, we want recent years (current + last 2 years)
        return {
            "category": "admission",
            # Note: Actual filtering depends on VectorIndexDAO implementation
            # This is metadata that can be used if documents have year field
            "year_range": [current_year - 2, current_year, current_year + 1]
        }

    def get_custom_prompt_context(self) -> Optional[str]:
        """
        Additional context for LLM about admission domain
        Helps LLM understand role and constraints
        """
        return (
            "Bạn là chuyên viên tư vấn tuyển sinh của Học viện Công nghệ Bưu chính Viễn thông (PTIT). "
            "Nhiệm vụ của bạn là cung cấp thông tin chính xác, rõ ràng về quy trình tuyển sinh, "
            "điểm chuẩn, phương thức xét tuyển, và các ngành đào tạo. "
            "Nếu thông tin không có trong tài liệu, hãy khuyến nghị thí sinh liên hệ phòng Đào tạo "
            "qua hotline 024.3577.1148 hoặc email tuyensinh@ptit.edu.vn"
        )

    def postprocess_answer(self, answer: str) -> str:
        """
        Postprocess admission answers
        Add disclaimer and contact info if needed
        """
        # Check if answer seems incomplete or uncertain
        uncertainty_markers = [
            "không rõ",
            "không chắc chắn",
            "cần xác nhận",
            "có thể thay đổi"
        ]

        if any(marker in answer.lower() for marker in uncertainty_markers):
            # Add contact disclaimer
            answer += (
                "\n\n📞 Để được tư vấn chính xác nhất, vui lòng liên hệ:\n"
                "- Hotline tuyển sinh: 024.3577.1148\n"
                "- Email: tuyensinh@ptit.edu.vn"
            )

        return answer

    def _get_no_results_message(self) -> str:
        """Custom no-results message for admission domain"""
        return (
            "Xin lỗi, tôi không tìm thấy thông tin tuyển sinh liên quan trong cơ sở dữ liệu. "
            "Bạn có thể:\n"
            "1. Thử hỏi lại với từ khóa khác\n"
            "2. Truy cập website: https://tuyensinh.ptit.edu.vn\n"
            "3. Gọi hotline tuyển sinh: 024.3577.1148\n"
            "4. Email: tuyensinh@ptit.edu.vn"
        )
