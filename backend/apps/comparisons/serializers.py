# apps/comparisons/serializers.py

"""
# 개요

0. 사용자 입력 검증 
0.1  UserPreferencesSerializer             | 사용자 선호도 입력 검증

1. 강좌 관련
1.1  SimpleCourseSerializer                |  강좌 비교 분석 결과에서 강좌 기본 정보 제공

2. AI 평가 관련
2.1 CourseAIReviewSerializer               | LLM이 생성한 강좌 평가 정보 제공
2.2 CourseAIReviewDetailSerializer         | 특정 강좌의 AI 평가 상세 조회용

3. 강좌 비교 분석 Request/Response
3.1  ComparisonAnalyzeRequestSerializer    | 강좌 비교 분석 요청 검증
3.2  ComparisonAnalyzeResponseSerializer   | 강좌 비교 분석 최종 응답 직렬화
3.3  ComparisonResultSerializer            | 강좌별 비교 분석 결과 직렬화

4. 부가 Serializer
4.1  SentimentResultSerializer             | 감성분석 결과 직렬화
4.2  TimelineResultSerializer              | 타임라인 시뮬레이션 결과 직렬화


[참고사항]
- 서비스는 3개가 이미 존재함
  - SentimentService | CourseReview 텍스트를 긍정 비율 /리뷰 수/신뢰도로 분석
  - TimelineService | course_playtime, week, study_end + weekly_hours(input)으로 "적정 / 널널 / 빠듯 / 종료 / 판정불가" 산출
  - ScoreService | theory/pracical/difficulty/duration 점수와 user_preferences(input)로 매칭 점수 산출 (유클리드 거리 기반)
- 서비스 패키지는 get_xxx_service() 함수로 인스턴스화하여 사용(싱글톤 진입점으로 export)
- 서비스는 비즈니스 로직만 담당, 입출력 데이터 직렬화는 serializers에서 담당
- API 초안은 POST /api/v1/comparisons/analyze/에 course_ids, weekly_hours, user_preferences(theory, practical, difficulty, duration)을 받아와서
  각 강좌별로 id, name, org_name, professor, course_image, url, study_end + ai_review + match_score + sentiment +timeline을 응답하는 형태

[설계 의도]
- Comparisons API의 요청/응답 데이터 직렬화
- 입력 검증 및 안전한 데이터 변환 담당

[상세 고려 사항]
- mypage 앱의 스타일과 호환 (상세 주석, 검증 로직)
- 중첩 Serializer 활용하여 관련 데이터 함께 제공
- read_only 필드와 입력 필드 명확히 구분
"""

from rest_framework import serializers
from apps.courses.models import Course
from apps.comparisons.models import CourseAIReview

MIN_COURSE_COMPARISON_COUNT = 1  # 최소 비교 강좌 수
MAX_COURSE_COMPARISON_COUNT = 3  # 최대 비교 강좌 수

MIN_WEEKLY_HOURS = 1    # 최소 주당 학습 시간
MAX_WEEKLY_HOURS = 168  # 최대 주당 학습 시간 (24*7)

MIN_VALUE = 0 # 평가 결정 요인 -> 사용자가 평가한 중요도 최소값
MAX_VALUE = 5 # 평가 결정 요인 -> 사용자가 평가한 중요도 최대값


# 0.1 UserPreferencesSerializer | 사용자 선호도 입력 검증
class UserPreferencesSerializer(serializers.Serializer):
    """
    [설계 의도]
    - 사용자 선호도 입력 검증
    - 각 항목은 0~5 범위로 제한

    [상세 고려 사항]
    - 모든 필드 필수 입력
    - 범위 검증 (0-5)
    - #NOTE 정수로 설계 (IntegerField)
    """

    theory = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        help_text="이론적 깊이 선호도 (0: 얕음, 5: 깊음)"
    )
    practical = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        help_text="실무 활용도 선호도 (0: 낮음, 5: 높음)"
    )
    difficulty = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        help_text="학습 난이도 선호도 (0: 쉬움, 5: 어려움)"
    )
    duration = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        help_text="학습 기간 선호도 (0: 짧음, 5: 김)"
    )


# =========================
# 1. 강좌 관련 Serializer
# =========================

# 1.1 SimpleCourseSerializer | 강좌 비교 분석 결과에서 강좌 기본 정보 제공
class SimpleCourseSerializer(serializers.ModelSerializer):
    """
    [설계 의도]
    - 강좌 비교 분석 결과에서 강좌 기본 정보 제공
    - mypage.serializers.SimpleCourseSerializer와 동일한 구조
    - 강좌 카드 렌더링에 필요한 최소 정보만 포함 
    #NOTE 우선은 apps 간 의존성 최소화 차원에서 별도 정의

    [상세 고려 사항]
    - Payload 최소화 (필요한 필드만)
    - 모든 필드 read_only (조회 전용)
    """

    class Meta:
        model = Course
        fields = (
            'id',                  # 강좌 ID
            'name',                # 강좌명
            'professor',           # 교수자
            'org_name',            # 운영 기관
            'course_image',        # 썸네일 이미지
            'url',                 # 강좌 URL
            'study_end',           # 수강 종료일
            'week',                # 총 주차
            'course_playtime'      # 총 학습 시간
        )
        read_only_fields = fields


# =========================
# 2. AI 평가 관련 Serializer
# =========================

# 2.1 CourseAIReviewSerializer | LLM이 생성한 강좌 평가 정보 제공
class CourseAIReviewSerializer(serializers.ModelSerializer):
    """
    [설계 의도]
    - LLM이 생성한 강좌 평가 정보 제공
    - #NOTE 미리 산출해낸 AI 평가 데이터를 DB에서 조회하여 직렬화
      - 강의 정보는 자주 변경되지 않으므로 별도 API 호출 없이 재사용 가능하다고 생각함.
      - 다만, 일정 기간 후 재생성 필요 시점이 올 수 있음(모델 업데이트, 프롬프트 개선 등) 
      #TODO 추후 정책 수립과 파이프라인 설계 필요
    - 강좌 비교 분석 및 강좌 상세 페이지에서 재사용

    [상세 고려 사항]
    - course 필드는 제외 (중복 방지)
    - 모든 필드 read_only (LLM 생성 데이터)
    """

    class Meta:
        model = CourseAIReview
        fields = (
            'course_summary',      # LLM 생성 요약
            'average_rating',      # 종합 평점
            'theory_rating',       # 이론적 깊이
            'practical_rating',    # 실무 활용도
            'difficulty_rating',   # 학습 난이도
            'duration_rating',     # 학습 기간
            'model_version',       # 사용된 모델
            'prompt_version',      # 프롬프트 버전
            'updated_at'           # 업데이트 시각
        )
        read_only_fields = fields

# 2.2 CourseAIReviewDetailSerializer | 특정 강좌의 AI 평가 상세 조회용 -> GET /api/v1/comparisons/courses/{course_id}/ai-review/
class CourseAIReviewDetailSerializer(serializers.ModelSerializer):
    """
    [설계 의도]
    - 특정 강좌의 AI 평가 상세 조회용
    - course_id 포함하여 어떤 강좌인지 명시

    [사용처]
    - GET /api/v1/comparisons/courses/{course_id}/ai-review/
    """

    course_id = serializers.IntegerField(source='course.id', read_only=True)

    class Meta:
        model = CourseAIReview
        fields = ( # 사실 model의 모든 필드 포함
            'course_id',                  # 강좌 ID
            'course_summary',             # LLM 생성 요약
            'average_rating',             # 종합 평점 # NOTE 평균 내리고 소수점 2자리까지 반올림
            'theory_rating',              # 이론적 깊이
            'practical_rating',           # 실무 활용도
            'difficulty_rating',          # 학습 난이도
            'duration_rating',            # 학습 기간    
            'model_version',              # 사용된 모델 (예시 : gpt-4o-mini)
            'prompt_version',             # 프롬프트 버전 -> 추후 개선 이력 관리용
            'created_at',                 # 생성 시각
            'updated_at'                  #  업데이트 시각
        )
        read_only_fields = fields


# =========================
# 3. 강좌 비교 분석 Request/Response Serializer
# =========================

# 3.1 ComparisonAnalyzeRequestSerializer | 강좌 비교 분석 요청 검증
class ComparisonAnalyzeRequestSerializer(serializers.Serializer):
    """
    [설계 의도]
    - 강좌 비교 분석 요청 검증
    - POST /api/v1/comparisons/analyze/ 의 request body 처리

    [상세 고려 사항]
    - course_ids: 최소 1개, 최대 3개 제한
    - weekly_hours: 1~168 (주당 최대 시간)
    - user_preferences: 중첩 Serializer로 검증
    """

    course_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=MIN_COURSE_COMPARISON_COUNT,
        max_length=MAX_COURSE_COMPARISON_COUNT,
        help_text="비교할 강좌 ID 리스트 (최소 1개, 최대 3개)"
    )

    weekly_hours = serializers.IntegerField(
        min_value=MIN_WEEKLY_HOURS,
        max_value=MAX_WEEKLY_HOURS,
        help_text="주당 학습 가능 시간 (1~168)"
    )

    user_preferences = UserPreferencesSerializer(
        help_text="사용자 선호도 (각 항목 0~5)"
    )

    def validate_course_ids(self, value):
        """
        [설계 의도]
        - 중복 ID 제거
        - 빈 리스트 방지

        [상세 고려 사항]
        - 중복 제거 후에도 최소 1개 보장
        """
        # 중복 제거
        unique_ids = list(set(value))

        if len(unique_ids) == 0:
            raise serializers.ValidationError(
                "최소 1개의 강좌를 선택해주세요."
            )

        return unique_ids

# 3.2 ComparisonResultSerializer | 강좌별 비교 분석 결과 직렬화
class ComparisonResultSerializer(serializers.Serializer):
    """
    [설계 의도]
    - 강좌별 비교 분석 결과 직렬화
    - course + ai_review + match_score + sentiment + timeline을 하나로 묶음

    [상세 고려 사항]
    - 중첩 Serializer 활용하여 관련 데이터 함께 제공
    - 프론트엔드에서 추가 API 호출 없이 렌더링 가능
    """

    course = SimpleCourseSerializer(read_only=True)
    ai_review = CourseAIReviewSerializer(read_only=True)
    match_score = serializers.FloatField(read_only=True)
    sentiment = SentimentResultSerializer(read_only=True)
    timeline = TimelineResultSerializer(read_only=True)

# 3.3 ComparisonAnalyzeResponseSerializer | 강좌 비교 분석 최종 응답 직렬화
class ComparisonAnalyzeResponseSerializer(serializers.Serializer):
    """
    [설계 의도]
    - 강좌 비교 분석 최종 응답 직렬화
    - results 리스트로 여러 강좌 결과 포함
    """

    results = ComparisonResultSerializer(
        many=True,
        read_only=True,
        help_text="비교 분석 결과 리스트 (매칭 점수 내림차순)"
    )


# =========================
# 4. 부가 Serializer
# =========================
 

# 4.1 SentimentResultSerializer | 감성분석 결과 직렬화
class SentimentResultSerializer(serializers.Serializer):
    """
    [설계 의도]
    - 감성분석 결과 직렬화
    - SentimentService에서 계산한 데이터를 구조화

    [상세 고려 사항]
    - 모델에 매핑되지 않는 계산 데이터이므로 Serializer 사용
    - read_only로 출력 전용
    """

    positive_ratio = serializers.FloatField(
        read_only=True,
        help_text="긍정 리뷰 비율 (%)"
    )
    review_count = serializers.IntegerField(
        read_only=True,
        help_text="총 리뷰 개수"
    )
    # NOTE 신뢰도는 'high' | 'low' 문자열로 표현, 추후 INT 등급으로 변경 검토 가능
    reliability = serializers.CharField(
        read_only=True,
        help_text="신뢰도 (high | low)"
    )

# 4.2 TimelineResultSerializer | 타임라인 시뮬레이션 결과 직렬화
class TimelineResultSerializer(serializers.Serializer):
    """
    [설계 의도]
    - "내가 이 강의 완강할 수 있을까?" 타임라인 시뮬레이션 결과 직렬화
    - TimelineService에서 계산한 데이터를 구조화

    [상세 고려 사항]
    - 계산 데이터이므로 Serializer 사용
    - read_only로 출력 전용
    """

    min_hours_per_week = serializers.IntegerField(
        read_only=True,
        help_text="주당 필요 학습 시간"
    )
    total_weeks = serializers.IntegerField(
        read_only=True,
        help_text="총 학습 주차"
    )
    remaining_weeks = serializers.IntegerField(
        read_only=True,
        help_text="남은 주차"
    )
    status = serializers.CharField(
        read_only=True,
        help_text="학습 강도 (적정 | 널널 | 빠듯 | 종료)" # Threshold 기준은 우선 0.8, 1.2 -> TimelineService 참고
    )
    ratio = serializers.FloatField(
        read_only=True,
        help_text="필요시간/가능시간 비율"
    )



