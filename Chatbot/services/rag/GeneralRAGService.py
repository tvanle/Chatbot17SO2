"""
GeneralRAGService - Fallback RAG service for general queries
Handles: all other queries that don't match specific domains
"""
from typing import List, Optional, Dict

from .BaseRAGService import BaseRAGService


class GeneralRAGService(BaseRAGService):
    """
    General-purpose RAG service (fallback)

    Used when:
    - Question doesn't match any specific domain keywords
    - User asks general information about PTIT
    - Multi-domain questions

    Specializations:
    - Namespace: ptit_docs (default namespace)
    - No specific keywords (catches all)
    - Minimal preprocessing
    - No filtering (searches all documents)
    """

    # Empty keywords = matches everything (fallback)
    DOMAIN_KEYWORDS = []

    def get_namespace(self) -> str:
        """Use default namespace for general queries"""
        return "ptit_docs"

    def get_domain_keywords(self) -> List[str]:
        """Empty list = accepts all queries as fallback"""
        return self.DOMAIN_KEYWORDS

    def get_domain_name(self) -> str:
        """Human-readable domain name"""
        return "Thông tin chung"

    def preprocess_question(self, question: str) -> str:
        """
        Minimal preprocessing for general queries
        Only basic cleanup
        """
        processed = question.strip()

        # Basic normalization
        common_abbreviations = {
            "PTIT": "Học viện Công nghệ Bưu chính Viễn thông",
            "HVBCVT": "Học viện Công nghệ Bưu chính Viễn thông"
        }

        # Only expand if it's standalone (not part of another word)
        import re
        for abbrev, full in common_abbreviations.items():
            # Match whole word only
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            # Keep original for first mention, can optionally add full form
            # For now, just keep as-is for general queries
            pass

        return processed

    def get_search_filters(self) -> Optional[Dict]:
        """
        No filtering for general queries
        Search across all categories
        """
        return None

    def get_custom_prompt_context(self) -> Optional[str]:
        """
        General context about PTIT
        """
        return (
            "Bạn là trợ lý AI của Học viện Công nghệ Bưu chính Viễn thông (PTIT). "
            "Nhiệm vụ của bạn là cung cấp thông tin hữu ích và chính xác về PTIT, "
            "bao gồm lịch sử, cơ sở vật chất, hoạt động sinh viên, và các thông tin khác. "
            "Hãy trả lời một cách thân thiện và chuyên nghiệp. "
            "Nếu câu hỏi thuộc lĩnh vực chuyên môn (tuyển sinh, học phí, quy chế), "
            "hãy khuyến nghị người dùng liên hệ phòng ban liên quan để được tư vấn chính xác."
        )

    def postprocess_answer(self, answer: str) -> str:
        """
        Minimal postprocessing for general answers
        """
        # Add general contact info if answer seems incomplete
        if len(answer) < 100 or "không tìm thấy" in answer.lower():
            answer += (
                "\n\n📞 Để biết thêm thông tin, bạn có thể:\n"
                "- Website: https://ptit.edu.vn\n"
                "- Hotline: 024.3577.1148\n"
                "- Email: info@ptit.edu.vn"
            )

        return answer

    def _get_no_results_message(self) -> str:
        """Custom no-results message for general domain"""
        return (
            "Xin lỗi, tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu. "
            "Bạn có thể:\n"
            "1. Thử hỏi lại với từ khóa khác\n"
            "2. Truy cập website: https://ptit.edu.vn\n"
            "3. Liên hệ tổng đài: 024.3577.1148\n"
            "4. Email: info@ptit.edu.vn\n\n"
            "Hoặc hỏi cụ thể về:\n"
            "- Tuyển sinh\n"
            "- Học phí và chi phí\n"
            "- Quy chế đào tạo\n"
            "- Cơ sở vật chất và địa chỉ"
        )
