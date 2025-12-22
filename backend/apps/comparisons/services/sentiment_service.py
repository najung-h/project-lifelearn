# apps/comparisons/services/sentiment_service.py

"""
[설계 의도]
- 강좌 리뷰의 감성분석을 담당하는 서비스(Service) 계층
- 실제 감성분석 모델 추론은 processor.py의 SentimentProcessor에 위임
- 이 서비스는 "모델 추론 결과를 어떻게 활용할지"에만 집중

────────────────────────────────────────
[전체 흐름 요약]

[학습 단계]
- train_model.py
  └─ sklearn Pipeline 학습
  └─ joblib : 감성분석 Pipeline 저장
  └─ json   : 모델 메타데이터(버전, 정확도 등) 저장

[추론 단계 - 런타임]
- SentimentService
  └─ get_sentiment_processor()
      └─ SentimentProcessor (Singleton)
          ├─ joblib.load(...)        ← 애플리케이션 전체에서 딱 1번
          └─ pipeline.predict / predict_proba
              (이후에는 추론만 반복 수행)

→ 핵심 포인트:
  "무거운 모델 로드는 processor에서 한 번만,
   Service는 가볍게 재사용하면서 비즈니스 로직만 처리"
────────────────────────────────────────

[이 Service의 책임]
- 특정 강좌의 리뷰를 DB에서 조회
- 리뷰 텍스트를 processor에 전달하여 감성분석 수행
- 긍정 비율, 리뷰 수, 신뢰도 같은 '서비스 지표'로 가공
- UI / 추천 로직에서 바로 쓸 수 있는 결과 구조 반환

[상세 고려 사항]
- 리뷰가 없는 경우에도 응답 구조는 항상 동일
- 캐싱, 모델 로딩, 배치 최적화는 processor 내부 책임
- #NOTE 신뢰도 기준: 
  - 리뷰 수 ≥ 10  → "high"
  - 리뷰 수 < 10  → "low"
"""

from typing import Dict
from django.db.models import QuerySet
from apps.courses.models import CourseReview
from apps.comparisons.ai_models.processor import get_sentiment_processor

class SentimentService:
    """
    [설계 의도]
    - 강좌 리뷰 감성분석에 대한 비즈니스 로직을 담당하는 Service 계층
    - 실제 모델 추론은 SentimentProcessor에 위임하고,
      이 클래스는 DB 조회 + 정책 판단 + 통계 가공만 수행
    - Controller/View 단에서는 감성분석의 내부 구현(joblib, sklearn 등)을
      전혀 알 필요 없도록 추상화

    [상세 고려 사항]
    - 모델 로딩은 processor에서 Singleton으로 한 번만 수행됨
    - Service는 processor 인스턴스를 재사용하며 추론만 요청
    - 리뷰 수가 0인 경우에도 항상 동일한 응답 스키마를 유지
    """

    # =========================
    # 정책 상수
    # =========================
    RELIABILITY_THRESHOLD = 10   # 신뢰도 판단 기준 리뷰 수
    LABEL_POSITIVE = 'positive'  # 감성분석 결과 중 긍정 라벨
    STATUS_HIGH = 'high'
    STATUS_LOW = 'low'

    def __init__(self):
        """
        [설계 의도]
        - SentimentProcessor는 Singleton이므로
          Service 인스턴스가 여러 번 생성되어도
          내부적으로 동일한 processor를 참조

        [상세 고려 사항]
        - 이 시점에서는 모델을 새로 로드하지 않음
        - processor 내부에서 이미 로드 여부를 판단
        """
        self.processor = get_sentiment_processor()

    def analyze_course_reviews(self, course_id: int) -> Dict:
        """
        [설계 의도]
        - 특정 강좌의 리뷰들을 감성분석하여
          서비스/UX 관점에서 의미 있는 통계 지표로 변환

        [상세 고려 사항]
        - DB 조회 → AI 추론 → 통계 가공의 책임을 이 메서드에서 일관되게 처리
        - 리뷰가 없는 경우 Early Return으로 불필요한 추론 방지
        """

        # 1. 강좌 리뷰 조회
        # - course_id 기준 필터링
        # - review_text가 NULL인 데이터 제외
        # - values_list(flat=True)로 텍스트만 추출
        #
        # 주의: 이 시점에서는 실제 DB 쿼리가 실행되지 않음 (Lazy Evaluation) -> 실제 쿼리는 count() 또는 list() 호출 시 실행됨 -> why? 성능 최적화를 위해
        review_qs: QuerySet = CourseReview.objects.filter(
            course_id=course_id
        ).exclude(
            review_text__isnull=True
        ).values_list(
            'review_text',
            flat=True
        )

        # 리뷰 개수 계산
        # - COUNT 쿼리 실행 (실제 DB 쿼리 발생)
        review_count = review_qs.count()

        # 2. 리뷰가 없는 경우 Early Return
        # - 모델 호출 방지
        # - 클라이언트 단 분기 처리 단순화
        if review_count == 0:
            return self._get_default_result()

        # 3. 리뷰 데이터 로드 및 배치 감성분석
        # - list() 호출 시 실제 SELECT 쿼리 실행 (실제 DB 쿼리 발생)
        review_texts = list(review_qs)

        # - processor는 이미 메모리에 모델을 로드한 상태
        # - 여기서는 순수 추론만 수행
        results = self.processor.analyze_batch(review_texts)

        # 4. 긍정 리뷰 개수 계산
        # - analyze_batch 결과 중 label이 'positive'인 경우만 카운트
        positive_count = sum(
            1
            for result in results
            if result.get('label') == self.LABEL_POSITIVE
        )

        # 5. 통계 및 신뢰도 계산
        # - 긍정 비율은 퍼센트 단위로 반환, 소수점 첫째 자리까지 반올림해서,.
        positive_ratio = round(
            (positive_count / review_count) * 100,
            1
        )

        # - 리뷰 수 기준으로 신뢰도 판정
        reliability = (
            self.STATUS_HIGH
            if review_count >= self.RELIABILITY_THRESHOLD
            else self.STATUS_LOW
        )

        return {
            'positive_ratio': positive_ratio,
            'review_count': review_count,
            'reliability': reliability
        }

    def _get_default_result(self) -> Dict:
        """
        [설계 의도]
        - 리뷰가 없는 경우에도 응답 스키마를 통일하기 위한 기본값 반환

        [상세 고려 사항]
        # NOTE
        - UI / 추천 로직에서 null 체크 불필요
        - 감성분석 결과가 없음을 간접적으로 표현
        """
        return {
            'positive_ratio': 0.0,
            'review_count': 0,
            'reliability': self.STATUS_LOW
        }


# =========================
# SentimentService 싱글톤 관리
# =========================

_sentiment_service_instance = None

def get_sentiment_service() -> SentimentService:
    """
    [설계 의도]
    - SentimentService를 애플리케이션 전역에서 재사용

    [상세 고려 사항]
    - Service 자체는 가볍지만
      내부에서 processor(Singleton)를 참조하므로
      불필요한 인스턴스 생성을 방지
    """
    global _sentiment_service_instance

    if _sentiment_service_instance is None:
        _sentiment_service_instance = SentimentService()

    return _sentiment_service_instance
