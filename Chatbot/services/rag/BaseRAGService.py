"""
BaseRAGService - Class cơ sở cho các domain service RAG
Định nghĩa interface chung mà tất cả domain service phải implement
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
import numpy as np
from sqlalchemy.orm import Session

from Chatbot.services.RetrieverService import RetrieverService
from Chatbot.utils.token_counter import fit_within_budget


class BaseRAGService(ABC):
    """
    Class cơ sở cho các domain-specific RAG services

    Kiến trúc:
    - Mỗi domain (tuyển sinh, học phí, quy chế) extend class này
    - Cung cấp các điểm tùy chỉnh: preprocessing, filtering, chọn namespace
    - Duy trì pipeline RAG nhất quán: vectorize → retrieve → generate

    Cách dùng:
        class AdmissionRAGService(BaseRAGService):
            def get_namespace(self) -> str:
                return "ptit_admission"

            def get_domain_keywords(self) -> List[str]:
                return ["tuyển sinh", "điểm chuẩn"]
    """

    def __init__(self, db: Session, vectorizer, generator):
        """
        Khởi tạo domain-specific RAG service

        Args:
            db: SQLAlchemy database session
            vectorizer: VectorizerService singleton (đã load model)
            generator: GeneratorService singleton (đã load LLM)
        """
        self.db = db
        self.vectorizer = vectorizer
        self.generator = generator
        self.retriever = RetrieverService(db)

    # ===== Các method bắt buộc phải implement =====

    @abstractmethod
    def get_namespace(self) -> str:
        """
        Trả về namespace identifier cho domain này
        Dùng trong vector store để phân tách documents theo domain

        Returns:
            Namespace string (ví dụ: "ptit_admission", "ptit_tuition")
        """
        pass

    @abstractmethod
    def get_domain_keywords(self) -> List[str]:
        """
        Danh sách keywords để nhận diện câu hỏi thuộc domain này
        DomainRouterService dùng để routing câu hỏi

        Returns:
            List các keywords tiếng Việt (lowercase)
        """
        pass

    @abstractmethod
    def get_domain_name(self) -> str:
        """
        Tên domain dễ đọc (dùng cho logging/debugging)

        Returns:
            Tên domain bằng tiếng Việt (ví dụ: "Tuyển sinh", "Học phí")
        """
        pass

    # ===== Các method tùy chọn có thể override =====

    def preprocess_question(self, question: str) -> str:
        """
        Tiền xử lý câu hỏi theo nhu cầu riêng của domain
        Override để thêm các transformations đặc thù

        Args:
            question: Câu hỏi gốc từ user

        Returns:
            Câu hỏi đã được xử lý

        Ví dụ:
            - Expand từ viết tắt: "TS" → "tuyển sinh"
            - Thêm context thời gian: "năm nay" → "năm 2024"
            - Chuẩn hóa thuật ngữ: "HP" → "học phí"
        """
        return question.strip()

    def get_search_filters(self) -> Optional[Dict]:
        """
        Metadata filters cho vector search
        Override để thêm filtering đặc thù theo domain

        Returns:
            Filter dict hoặc None

        Ví dụ:
            {"category": "admission", "year": "2024"}
            {"department": "finance"}
        """
        return None

    def get_custom_prompt_context(self) -> Optional[str]:
        """
        Context bổ sung để inject vào LLM prompt
        Override để thêm instructions đặc thù theo domain

        Returns:
            Text prompt bổ sung hoặc None

        Ví dụ:
            "Bạn là chuyên viên tư vấn tuyển sinh của PTIT..."
        """
        return None

    def postprocess_answer(self, answer: str) -> str:
        """
        Hậu xử lý câu trả lời đã generate
        Override để thêm formatting đặc thù theo domain

        Args:
            answer: Câu trả lời thô từ LLM

        Returns:
            Câu trả lời đã xử lý

        Ví dụ:
            - Thêm disclaimers
            - Format dates/numbers
            - Thêm thông tin liên hệ
        """
        return answer

    # ===== Main RAG Pipeline (thường không cần override) =====

    def answer(
        self,
        question: str,
        top_k: int = 5,
        token_budget: int = 2000,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict:
        """
        Thực thi main RAG pipeline
        Có thể override nếu cần logic hoàn toàn custom, nhưng thường không cần

        Pipeline:
        1. Preprocess câu hỏi (domain-specific)
        2. Vectorize câu hỏi
        3. Retrieve các chunks liên quan (với domain filters)
        4. Generate câu trả lời bằng LLM
        5. Postprocess câu trả lời (domain-specific)

        Args:
            question: Câu hỏi của user
            top_k: Số lượng chunks cần retrieve
            token_budget: Giới hạn tokens cho context
            conversation_history: Lịch sử hội thoại trước đó

        Returns:
            Dict với keys: answer, citations, domain, namespace
        """
        # Bước 1: Tiền xử lý câu hỏi
        processed_question = self.preprocess_question(question)

        # Bước 2: Chuyển câu hỏi thành vector
        query_vector = self.vectorizer.embed(processed_question)

        # Bước 3: Tìm kiếm TOÀN BỘ namespaces (vì data hiện tại phần lớn là general)
        # Mặc dù tìm toàn bộ, mỗi domain vẫn có:
        # - Preprocessing riêng (expand abbreviations, add context)
        # - Custom prompt/system context riêng
        # - Postprocessing riêng
        hits = self.retriever.search(
            namespace=None,  # None = tìm tất cả namespaces
            query_vector=query_vector,
            top_k=top_k,
            filters=None  # Không filter để có nhiều kết quả hơn
        )

        # Xử lý trường hợp không tìm thấy kết quả
        if not hits:
            return {
                "answer": self._get_no_results_message(),
                "citations": [],
                "domain": self.get_domain_name(),
                "namespace": self.get_namespace()
            }

        # Bước 4: Cắt xén contexts cho vừa token budget
        context_texts = [hit.chunk["text"] for hit in hits if hit.chunk]
        contexts = fit_within_budget(context_texts, token_budget=token_budget)

        # Bước 5: Generate câu trả lời với domain context tùy chọn
        custom_context = self.get_custom_prompt_context()
        answer_text = self.generator.generate(
            question=processed_question,
            contexts=contexts,
            language="vi",
            conversation_history=conversation_history,
            system_context=custom_context
        )

        # Bước 6: Hậu xử lý câu trả lời
        final_answer = self.postprocess_answer(answer_text)

        return {
            "answer": final_answer,
            "citations": hits,
            "domain": self.get_domain_name(),
            "namespace": self.get_namespace()
        }

    def _get_no_results_message(self) -> str:
        """
        Message mặc định khi không tìm thấy documents liên quan
        Override để custom message theo từng domain
        """
        return (
            f"Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi "
            f"của bạn trong lĩnh vực {self.get_domain_name()}. "
            f"Bạn có thể thử hỏi theo cách khác hoặc liên hệ văn phòng để được tư vấn chi tiết hơn."
        )

    # ===== Class method để detect domain =====

    @classmethod
    def matches_domain(cls, question: str) -> bool:
        """
        Kiểm tra xem câu hỏi có khớp với domain này không (dùng cho routing)
        Sử dụng keywords từ get_domain_keywords()

        Args:
            question: Câu hỏi của user (lowercase)

        Returns:
            True nếu câu hỏi chứa keywords của domain
        """
        # Tạo instance tạm để lấy keywords (static method sẽ tốt hơn)
        # Đây là thiết kế thỏa hiệp - lý tưởng là keywords nên là class attribute
        question_lower = question.lower()

        # Vì không thể instantiate mà không có db/vectorizer, cần workaround
        # Domain routers sẽ handle việc này khác đi
        return False
