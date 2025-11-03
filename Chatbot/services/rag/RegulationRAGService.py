"""
RegulationRAGService - RAG service specialized for academic regulations
Handles: quy chế đào tạo, điều kiện tốt nghiệp, chuyên ngành, học lại, điểm
"""
from typing import List, Optional, Dict

from .BaseRAGService import BaseRAGService


class RegulationRAGService(BaseRAGService):
    """
    Domain service for PTIT academic regulation queries

    Specializations:
    - Namespace: ptit_regulations
    - Keywords: quy chế, điều kiện, tốt nghiệp, học lại, chuyên ngành
    - Preprocessing: Normalize regulation terms
    - Filtering: By regulation version/year
    """

    # Class-level keywords (for domain routing)
    DOMAIN_KEYWORDS = [
        "quy chế",
        "quy định",
        "điều kiện",
        "tốt nghiệp",
        "chuyên ngành",
        "học lại",
        "thi lại",
        "điểm",
        "điểm trung bình",
        "học vụ",
        "chương trình đào tạo",
        "kế hoạch học tập",
        "môn học",
        "học phần",
        "tín chỉ tích lũy",
        "cảnh báo học tập",
        "buộc thôi học",
        "nghỉ học",
        "chuyển trường",
        "chuyển ngành",
        "điều kiện đăng ký",
        "đăng ký học phần",
        "thời khóa biểu"
    ]

    def get_namespace(self) -> str:
        """Namespace for regulation documents"""
        return "ptit_regulations"

    def get_domain_keywords(self) -> List[str]:
        """Keywords identifying regulation domain"""
        return self.DOMAIN_KEYWORDS

    def get_domain_name(self) -> str:
        """Human-readable domain name"""
        return "Quy chế đào tạo"

    def preprocess_question(self, question: str) -> str:
        """
        Preprocess regulation-specific questions

        Transformations:
        - Expand abbreviations: QCĐT → quy chế đào tạo
        - Normalize grade terms: GPA → điểm trung bình
        """
        processed = question.strip()

        # Expand abbreviations
        abbreviations = {
            "QCĐT": "quy chế đào tạo",
            "ĐKTN": "điều kiện tốt nghiệp",
            "ĐKTB": "điểm trung bình",
            "GPA": "điểm trung bình",
            "KHTB": "kết quả trung bình",
            "HP": "học phần",
            "ĐKHP": "đăng ký học phần",
            "TN": "tốt nghiệp"
        }

        for abbrev, full in abbreviations.items():
            processed = processed.replace(abbrev, full)

        # Normalize grade terms
        grade_normalizations = {
            "điểm TB": "điểm trung bình",
            "đ.TB": "điểm trung bình",
            "kết quả TB": "kết quả trung bình"
        }

        for term, normalized in grade_normalizations.items():
            if term in processed:
                processed = processed.replace(term, normalized)

        return processed

    def get_search_filters(self) -> Optional[Dict]:
        """
        Filter by regulation category
        Prioritize latest regulation versions
        """
        return {
            "category": "regulations",
            # Could add version filtering if documents have regulation_version field
            # "version": "latest"
        }

    def get_custom_prompt_context(self) -> Optional[str]:
        """
        Additional context for LLM about regulation domain
        """
        return (
            "Bạn là chuyên viên học vụ của Học viện Công nghệ Bưu chính Viễn thông (PTIT). "
            "Nhiệm vụ của bạn là giải thích rõ ràng các quy chế đào tạo, điều kiện tốt nghiệp, "
            "quy trình chuyên ngành, và các quy định học vụ khác. "
            "Hãy trích dẫn cụ thể điều khoản nếu có trong tài liệu. "
            "Nếu thông tin không rõ ràng, khuyến nghị sinh viên liên hệ phòng Đào tạo "
            "qua email: daotao@ptit.edu.vn hoặc đến trực tiếp văn phòng phòng Đào tạo."
        )

    def postprocess_answer(self, answer: str) -> str:
        """
        Postprocess regulation answers
        Format citations and add disclaimer
        """
        # Add regulatory disclaimer
        if "quy chế" in answer.lower() or "quy định" in answer.lower():
            answer += (
                "\n\n📋 Lưu ý: Thông tin trên dựa trên quy chế đào tạo hiện hành. "
                "Quy chế có thể được cập nhật theo quyết định của Hội đồng Trường. "
                "Vui lòng kiểm tra phiên bản mới nhất tại phòng Đào tạo hoặc website chính thức."
            )

        # Highlight important warnings
        warning_keywords = [
            "buộc thôi học",
            "cảnh báo học tập",
            "không đủ điều kiện",
            "bị hủy"
        ]

        if any(keyword in answer.lower() for keyword in warning_keywords):
            answer = "⚠️ QUAN TRỌNG: " + answer

        return answer

    def _get_no_results_message(self) -> str:
        """Custom no-results message for regulation domain"""
        return (
            "Xin lỗi, tôi không tìm thấy thông tin về quy chế/quy định này trong cơ sở dữ liệu. "
            "Bạn có thể:\n"
            "1. Tải quy chế đào tạo đầy đủ tại website: https://ptit.edu.vn\n"
            "2. Liên hệ phòng Đào tạo: daotao@ptit.edu.vn\n"
            "3. Gọi tổng đài: 024.3577.1148 (máy lẻ Đào tạo)\n"
            "4. Hỏi cố vấn học tập của lớp"
        )
