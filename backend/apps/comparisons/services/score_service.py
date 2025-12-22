# apps/comparisons/services/score_service.py
"""
[설계 의도]
- 사용자의 선호도 벡터와 강좌의 AI 평가 벡터 간의 유사도를
  하나의 직관적인 점수(0~100)로 환산하는 서비스
- 이 점수를 기준으로 강좌 정렬 / 추천 순위 결정

[핵심 아이디어]
- "사용자가 원하는 강좌"와 "강좌의 실제 성향"을
  4차원 공간의 점으로 보고,
  두 점 사이의 거리를 유사도로 해석

[상세 고려 사항]
- 매칭 점수 계산 방식: 유클리드 거리(Euclidean Distance)
- 차이가 0이면 100점 (완전 일치)
- 모든 항목에서 최대 차이(5)가 나면 0점
- 비교 항목:
  theory / practical / difficulty / duration (총 4개)
"""

import math
from typing import Dict
from apps.comparisons.models import CourseAIReview


class ScoreService:
    """
    사용자 선호도와 강좌 AI 평가를 비교하여
    '얼마나 잘 맞는 강좌인지'를 점수로 계산하는 도메인 서비스

    [설계 의도]
    - 추천/비교 로직에서 재사용 가능
    - 점수 산출 책임을 View/Serializer에서 분리
    """

    # 비교 항목 설정 (모델 필드명: 사용자 선호도 키)
    MATCHING_FIELDS = {
        'theory_rating': 'theory',
        'practical_rating': 'practical',
        'difficulty_rating': 'difficulty',
        'duration_rating': 'duration'
    }

    MAX_RATING = 5.0  # 각 항목의 최대 평점

    def calculate_match_score(
        self,
        ai_review: CourseAIReview,
        user_preferences: Dict[str, float]
    ) -> float:
        """
        매칭 점수 계산

        Args:
            ai_review: CourseAIReview 인스턴스
            user_preferences: {
                'theory': 0.0-5.0,
                'practical': 0.0-5.0,
                'difficulty': 0.0-5.0,
                'duration': 0.0-5.0
            }

        Returns:
            float: 매칭 점수 (0-100)

        [설계 의도]
        - 사용자가 원하는 수준과 강좌의 실제 수준이 얼마나 일치하는지 수치화
        - 완벽히 일치하면 100점, 완전히 다르면 0점

        [계산 로직]
        1. 각 항목별 차이 계산 (제곱합)
           - sum_of_squares = Σ(ai_val - user_val)²
        2. 유클리드 거리 계산
           - distance = sqrt(sum_of_squares)
        3. 점수 변환 (최대 가능 거리로 정규화)
           - max_distance = sqrt(항목수 * MAX_RATING²)
           - score = 100 * (1 - distance / max_distance)

        [상세 고려 사항]
        - 점수 범위: 0-100 보장 (max, min 사용)
        - 소수점 첫째 자리까지 반환
        """
        # 1. 차이 제곱합 계산
        sum_of_squares = 0.0
        field_count = len(self.MATCHING_FIELDS)

        # 1. 각 항목별 차이의 제곱합 계산
        for model_field, pref_key in self.MATCHING_FIELDS.items():
            # ai_review 필드 값과 사용자 선호도 값 가져오기, 기본값 0.0 처리
            ai_val = getattr(ai_review, model_field, 0) or 0.0
            # 사용자의 선호도 값 가져오기, 기본값 0.0 처리
            user_val = user_preferences.get(pref_key, 0.0)
            # (ai_val - user_val)^2 누적
            sum_of_squares += (ai_val - user_val) ** 2

        # 2. 유클리드 거리 계산 in 4차원.
        distance = math.sqrt(sum_of_squares)

        # 3. 최대 가능 거리 계산 (모든 항목이 0 vs 5일 때)
        # 4개 항목 기준: sqrt(4 * 5^2) = sqrt(100) = 10.0
        max_possible_distance = math.sqrt(field_count * (self.MAX_RATING ** 2))

        # 4. 점수 변환
        # 방어적 설계
        if max_possible_distance == 0:
            return 0.0
        
        # 거리에 기반한 점수 계산
        score = 100 * (1 - (distance / max_possible_distance))

        # 5. 범위 보정 (0-100)
        score = max(0.0, min(100.0, score))

        # 반올림, 소숫점 첫째 자리까지
        return round(score, 1)


# 싱글톤 인스턴스 관리
_score_service_instance = None

def get_score_service() -> ScoreService:
    """
    ScoreService 싱글톤 인스턴스 반환

    - 서비스는 상태를 가지지 않으므로
      단일 인스턴스 재사용이 적합
    """
    global _score_service_instance
    if _score_service_instance is None:
        _score_service_instance = ScoreService()
    return _score_service_instance