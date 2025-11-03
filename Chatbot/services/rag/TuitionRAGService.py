"""
TuitionRAGService - RAG service specialized for tuition and financial queries
Handles: học phí, chi phí, lệ phí, học bổng, miễn giảm
"""
from typing import List, Optional, Dict
from datetime import datetime

from .BaseRAGService import BaseRAGService


class TuitionRAGService(BaseRAGService):
    """
    Domain service for PTIT tuition and financial queries

    Specializations:
    - Namespace: ptit_tuition
    - Keywords: học phí, chi phí, học bổng, miễn giảm
    - Preprocessing: Normalize currency, expand abbreviations
    - Filtering: By academic year and semester
    """

    # Class-level keywords (for domain routing)
    DOMAIN_KEYWORDS = [
        "học phí",
        "chi phí",
        "lệ phí",
        "phí",
        "học bổng",
        "miễn giảm",
        "miễn học phí",
        "giảm học phí",
        "thu phí",
        "đóng học phí",
        "nộp học phí",
        "mức học phí",
        "bảng giá",
        "tín chí",
        "học phí tín chỉ",
        "chi phí học tập",
        "khoản phải nộp",
        "tiền học"
    ]

    def get_namespace(self) -> str:
        """Namespace for tuition documents"""
        return "ptit_tuition"

    def get_domain_keywords(self) -> List[str]:
        """Keywords identifying tuition domain"""
        return self.DOMAIN_KEYWORDS

    def get_domain_name(self) -> str:
        """Human-readable domain name"""
        return "Học phí và Chi phí"

    def preprocess_question(self, question: str) -> str:
        """
        Preprocess tuition-specific questions

        Transformations:
        - Expand abbreviations: HP → học phí
        - Add academic year context
        - Normalize currency terms
        """
        processed = question.strip()

        # Expand abbreviations
        abbreviations = {
            " HP ": " học phí ",
            "HP.": "học phí",
            " TC ": " tín chỉ ",
            "TC.": "tín chỉ",
            "HB": "học bổng"
        }

        for abbrev, full in abbreviations.items():
            processed = processed.replace(abbrev, full)

        # Normalize currency terms
        processed = processed.replace("đ", "đồng")
        processed = processed.replace("k", "000")  # 500k → 500000

        # Add academic year context
        current_year = datetime.now().year
        current_month = datetime.now().month

        # Determine current academic year (starts in August/September)
        if current_month >= 8:
            academic_year = f"{current_year}-{current_year + 1}"
        else:
            academic_year = f"{current_year - 1}-{current_year}"

        temporal_replacements = {
            "năm nay": f"năm học {academic_year}",
            "năm học này": f"năm học {academic_year}",
            "học kỳ này": f"học kỳ năm {academic_year}"
        }

        for temporal, expanded in temporal_replacements.items():
            if temporal in processed.lower():
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
        Filter by tuition category and recent academic years
        """
        current_year = datetime.now().year
        current_month = datetime.now().month

        # Determine academic year
        if current_month >= 8:
            academic_year = f"{current_year}-{current_year + 1}"
        else:
            academic_year = f"{current_year - 1}-{current_year}"

        return {
            "category": "tuition",
            "academic_year": academic_year
        }

    def get_custom_prompt_context(self) -> Optional[str]:
        """
        Additional context for LLM about tuition domain
        """
        return (
            "Bạn là chuyên viên tài chính của Học viện Công nghệ Bưu chính Viễn thông (PTIT). "
            "Nhiệm vụ của bạn là cung cấp thông tin chính xác về học phí, chi phí học tập, "
            "chính sách miễn giảm, và học bổng. "
            "Khi nói về số tiền, hãy định dạng rõ ràng (ví dụ: 500.000 đồng/tín chỉ). "
            "Nếu thông tin không có trong tài liệu, khuyến nghị sinh viên liên hệ phòng Tài chính "
            "qua email: taichinh@ptit.edu.vn hoặc trực tiếp tại văn phòng phòng Tài chính."
        )

    def postprocess_answer(self, answer: str) -> str:
        """
        Postprocess tuition answers
        Format currency values and add disclaimer
        """
        # Format currency (add thousands separator)
        import re

        # Find currency patterns (numbers followed by đồng/VNĐ)
        def format_currency(match):
            number = match.group(1).replace(",", "").replace(".", "")
            try:
                formatted = "{:,.0f}".format(float(number)).replace(",", ".")
                return f"{formatted} đồng"
            except ValueError:
                return match.group(0)

        answer = re.sub(r'(\d+(?:[.,]\d+)*)\s*(?:đồng|VNĐ)', format_currency, answer)

        # Add disclaimer about policy changes
        if "học phí" in answer.lower() or "chi phí" in answer.lower():
            answer += (
                "\n\n⚠️ Lưu ý: Học phí có thể thay đổi theo quy định của nhà trường và cơ quan quản lý. "
                "Vui lòng kiểm tra thông tin mới nhất tại phòng Tài chính."
            )

        return answer

    def _get_no_results_message(self) -> str:
        """Custom no-results message for tuition domain"""
        return (
            "Xin lỗi, tôi không tìm thấy thông tin về học phí/chi phí trong cơ sở dữ liệu. "
            "Bạn có thể:\n"
            "1. Liên hệ phòng Tài chính: taichinh@ptit.edu.vn\n"
            "2. Truy cập cổng thông tin sinh viên để xem học phí chi tiết\n"
            "3. Gọi tổng đài: 024.3577.1148 (máy lẻ Tài chính)"
        )
