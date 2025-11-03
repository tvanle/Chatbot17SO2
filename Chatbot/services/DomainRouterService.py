"""
DomainRouterService - Route câu hỏi của user đến domain service phù hợp
Dùng keyword matching để detect domain của câu hỏi
"""
from typing import List, Type, Dict, Optional
from sqlalchemy.orm import Session

from .rag.BaseRAGService import BaseRAGService
from .rag.AdmissionRAGService import AdmissionRAGService
from .rag.TuitionRAGService import TuitionRAGService
from .rag.RegulationRAGService import RegulationRAGService
from .rag.GeneralRAGService import GeneralRAGService


class DomainRouterService:
    """
    Domain router cho multi-domain RAG system

    Kiến trúc:
    1. Phân tích câu hỏi của user
    2. Match với keywords của các domain
    3. Route đến domain service phù hợp nhất
    4. Fallback về GeneralRAGService nếu không match

    Cách dùng:
        router = DomainRouterService()
        service = router.route(question, db, vectorizer, generator)
        result = service.answer(question)
    """

    def __init__(self):
        """
        Khởi tạo router với domain service registry
        Thứ tự quan trọng: Domain cụ thể hơn nên đứng trước
        """
        # Đăng ký các domain services theo thứ tự ưu tiên
        self.domain_services: List[Type[BaseRAGService]] = [
            AdmissionRAGService,   # Tuyển sinh (ưu tiên cao)
            TuitionRAGService,     # Học phí (ưu tiên cao)
            RegulationRAGService,  # Quy chế (ưu tiên trung bình)
            # GeneralRAGService là fallback, không để trong registry
        ]

        # Fallback service
        self.fallback_service = GeneralRAGService

        # Build keyword index để match nhanh hơn
        self._keyword_index = self._build_keyword_index()

    def _build_keyword_index(self) -> Dict[str, Type[BaseRAGService]]:
        """
        Build index mapping keywords to service classes
        Allows O(1) keyword lookup

        Returns:
            Dict mapping lowercase keyword to service class
        """
        index = {}
        for service_class in self.domain_services:
            keywords = service_class.DOMAIN_KEYWORDS
            for keyword in keywords:
                # Map each keyword to its service (lowercase for case-insensitive matching)
                index[keyword.lower()] = service_class
        return index

    def detect_domain(self, question: str) -> Type[BaseRAGService]:
        """
        Detect which domain service best matches the question
        Uses keyword matching with scoring

        Algorithm:
        1. Tokenize question to words
        2. Check each word against keyword index
        3. Count matches per domain
        4. Return domain with highest match count
        5. Fallback to GeneralRAGService if no matches

        Args:
            question: User's question (raw text)

        Returns:
            Service class that best matches the question
        """
        question_lower = question.lower()

        # Count keyword matches per service
        service_scores: Dict[Type[BaseRAGService], int] = {}

        # Check each registered service's keywords
        for service_class in self.domain_services:
            score = 0
            keywords = service_class.DOMAIN_KEYWORDS

            # Count how many keywords appear in question
            for keyword in keywords:
                if keyword.lower() in question_lower:
                    score += 1

                    # Bonus: If keyword appears multiple times
                    count = question_lower.count(keyword.lower())
                    if count > 1:
                        score += (count - 1) * 0.5  # Partial bonus for repeats

            if score > 0:
                service_scores[service_class] = score

        # Return service with highest score
        if service_scores:
            best_service = max(service_scores.items(), key=lambda x: x[1])[0]
            return best_service

        # No matches: fallback to general service
        return self.fallback_service

    def detect_multi_domain(self, question: str) -> List[Type[BaseRAGService]]:
        """
        Detect if question spans multiple domains
        Returns all domains that match (sorted by score)

        Example:
            "Học phí tuyển sinh năm nay là bao nhiêu?"
            → [TuitionRAGService, AdmissionRAGService]

        Args:
            question: User's question

        Returns:
            List of matching service classes (empty if no matches)
        """
        question_lower = question.lower()
        service_scores: Dict[Type[BaseRAGService], int] = {}

        # Score all services
        for service_class in self.domain_services:
            score = 0
            keywords = service_class.DOMAIN_KEYWORDS

            for keyword in keywords:
                if keyword.lower() in question_lower:
                    score += 1

            if score > 0:
                service_scores[service_class] = score

        # Return all services with matches, sorted by score
        sorted_services = sorted(
            service_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [service_class for service_class, _ in sorted_services]

    def route(
        self,
        question: str,
        db: Session,
        vectorizer,
        generator
    ) -> BaseRAGService:
        """
        Route question to appropriate domain service
        Main entry point for routing

        Args:
            question: User's question
            db: Database session
            vectorizer: VectorizerService instance
            generator: GeneratorService instance

        Returns:
            Instantiated domain service ready to use
        """
        service_class = self.detect_domain(question)
        return service_class(db, vectorizer, generator)

    def route_multi(
        self,
        question: str,
        db: Session,
        vectorizer,
        generator,
        max_domains: int = 2
    ) -> List[BaseRAGService]:
        """
        Route to multiple domains for multi-domain questions
        Returns list of services to query in parallel

        Args:
            question: User's question
            db: Database session
            vectorizer: VectorizerService instance
            generator: GeneratorService instance
            max_domains: Max number of domains to query

        Returns:
            List of instantiated services
        """
        service_classes = self.detect_multi_domain(question)[:max_domains]

        # If no matches, use fallback
        if not service_classes:
            service_classes = [self.fallback_service]

        return [service_class(db, vectorizer, generator) for service_class in service_classes]

    def get_domain_info(self) -> List[Dict[str, any]]:
        """
        Get information about all registered domains
        Useful for debugging and documentation

        Returns:
            List of dicts with domain metadata
        """
        domains = []

        for service_class in self.domain_services + [self.fallback_service]:
            # Create temporary instance to get metadata
            # Note: This is a workaround since we need db/vectorizer/generator
            # In production, consider making these class methods instead
            domains.append({
                "class_name": service_class.__name__,
                "namespace": service_class.DOMAIN_KEYWORDS if hasattr(service_class, 'DOMAIN_KEYWORDS') else [],
                "keywords_count": len(service_class.DOMAIN_KEYWORDS) if hasattr(service_class, 'DOMAIN_KEYWORDS') else 0,
                "keywords_sample": service_class.DOMAIN_KEYWORDS[:5] if hasattr(service_class, 'DOMAIN_KEYWORDS') else []
            })

        return domains

    def analyze_question(self, question: str) -> Dict[str, any]:
        """
        Analyze question and return detailed routing information
        Useful for debugging and understanding routing decisions

        Args:
            question: User's question

        Returns:
            Dict with analysis results
        """
        # Detect primary domain
        primary_service = self.detect_domain(question)

        # Detect all matching domains
        all_matches = self.detect_multi_domain(question)

        # Find matched keywords per domain
        question_lower = question.lower()
        matched_keywords = {}

        for service_class in self.domain_services:
            keywords = service_class.DOMAIN_KEYWORDS
            matches = [kw for kw in keywords if kw.lower() in question_lower]
            if matches:
                matched_keywords[service_class.__name__] = matches

        return {
            "question": question,
            "primary_domain": primary_service.__name__,
            "all_matching_domains": [s.__name__ for s in all_matches],
            "matched_keywords": matched_keywords,
            "is_multi_domain": len(all_matches) > 1,
            "fallback_used": primary_service == self.fallback_service
        }
