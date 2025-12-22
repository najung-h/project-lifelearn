# apps/comparisons/services/timeline_service.py

"""
[설계 의도]
[설계 의도]
- 사용자의 주당 학습 가능 시간과 강좌 정보를 기반으로
  실제 수강이 가능한지 타임라인 시뮬레이션을 수행하는 서비스 레이어
- 단순 추천이 아니라,
  "이 강좌를 지금 내 상황에서 들을 수 있는가?"에 대한 정량적 판단 제공

[이 서비스의 역할]
- Course 객체 + 사용자 입력(weekly_hours)을 받아
  → 주당 최소 필요 학습 시간 계산
  → 사용자 대비 학습 강도(ratio) 산출
  → 직관적인 상태값(적정/널널/빠듯)으로 변환

[상세 고려 사항]
- threshold 기준:
  - 적정: ratio < 0.8
  - 널널: 0.8 <= ratio < 1.2
  - 빠듯: ratio >= 1.2
- 주당 필요 학습 시간 = 총 학습 시간 / 남은 주차
  (단, UI 혼란 방지를 위해 최소 1시간 보장)
- 현재 시각 기준으로 남은 기간 계산
- 0으로 나누기, 데이터 누락 등 예외 케이스 방어
"""

from typing import Dict
from datetime import date
from django.utils import timezone
from apps.courses.models import Course


class TimelineService:
    """
    강좌 수강 가능성 판단을 담당하는 도메인 서비스 클래스

    - View / Serializer에서 직접 계산 로직을 갖지 않도록 분리
    - 이후 다른 추천 로직(AI, 비교함 등)에서도 재사용 가능
    """
    # =========================
    # 상태값 상수 정의
    # =========================
    STATUS_OPTIMAL = '적정'     # 부담 없는 수준
    STATUS_RELAXED = '널널'     # 여유 있는 수준
    STATUS_TIGHT = '빠듯'       # 빡빡한 수준
    STATUS_FINISHED = '종료'    # 이미 종료된 강좌
    STATUS_UNKNOWN = '판정불가' # 판단 불가능 (입력값 부족)

    # =========================
    # 판정 임계값 상수
    # =========================
    THRESHOLD_OPTIMAL = 0.8
    THRESHOLD_TIGHT = 1.2

    def calculate_timeline(
        self,
        course: Course,
        weekly_hours: int
    ) -> Dict:
        """
        강좌 타임라인 시뮬레이션 실행
        """
        # =========================
        # 1. 총 학습 시간 계산
        # =========================
        # course_playtime은 "분 단위"로 저장되어 있으므로 시간 단위로 변환
        playtime_raw = course.course_playtime or 0

        if playtime_raw > 0:
            total_hours = playtime_raw / 60
        else:
            # 학습 시간이 없거나 0인 경우
            total_hours = float(playtime_raw)

        # =========================
        # 2. 주차 정보 계산
        # =========================
        # 강좌 전체 주차 수
        total_weeks = course.week or 0

        # 현재 시점 기준 남은 주차 계산 (private 메서드 위임)
        remaining_weeks = self._calculate_remaining_weeks(course)

        # =========================
        # 3. 기본 변수 초기화
        # =========================
        min_hours_per_week = 0.0  # 주당 최소 필요 학습 시간
        ratio = 0.0               # 사용자 대비 학습 강도 비율
        status = self.STATUS_UNKNOWN

        # =========================
        # 4. 케이스별 분기 처리
        # =========================

        # --- 케이스 A: 이미 종료된 강좌 ---
        if remaining_weeks <= 0:
            return self._format_response(
                min_hours=0,
                total_weeks=total_weeks,
                remaining_weeks=0,
                status=self.STATUS_FINISHED,
                ratio=0.0
            )

        # =========================
        # 주당 필요 학습 시간 계산
        # =========================
        # 총 학습 시간을 남은 주차로 나누되,
        # UX 관점에서 최소 1시간은 보장
        min_hours_per_week = max(
            total_hours / remaining_weeks,
            1.0
        )

        # --- 케이스 B: 사용자가 학습 시간을 입력하지 않은 경우 ---
        # (0이거나 음수 → 비교 자체가 불가능)
        if weekly_hours <= 0:
            return self._format_response(
                min_hours=min_hours_per_week,
                total_weeks=total_weeks,
                remaining_weeks=remaining_weeks,
                status=self.STATUS_UNKNOWN,
                ratio=0.0
            )

        # --- 케이스 C: 정상적인 비교 가능 ---
        # ratio = (필요 시간) / (사용자 가능 시간)
        ratio = round(min_hours_per_week / weekly_hours, 2)

        # =========================
        # 상태 판정 로직
        # =========================
        if ratio < self.THRESHOLD_OPTIMAL:
            status = self.STATUS_OPTIMAL
        elif ratio < self.THRESHOLD_TIGHT:
            status = self.STATUS_RELAXED
        else:
            status = self.STATUS_TIGHT

        # 최종 결과 반환
        return self._format_response(
            min_hours=min_hours_per_week,
            total_weeks=total_weeks,
            remaining_weeks=remaining_weeks,
            status=status,
            ratio=ratio
        )

    def _calculate_remaining_weeks(self, course: Course) -> int:
        """
        현재 시각 기준으로 강좌 종료일까지 남은 주차 계산
        """
        # [상세 고려 사항] study_end가 없으면 총 주차(기본값 15)를 그대로 반환
        if not course.study_end:
            return course.week or 15 # 한 학기가 일반적으로 15주 정도 되는 것이라고 가정하고 설계함.

        # 현재 날짜 (타입 일관성을 위해 .date() 호출)
        now = timezone.now().date()
        
        # study_end가 datetime인 경우를 대비해 date 객체로 변환
        end_date = course.study_end if isinstance(course.study_end, date) else course.study_end.date()

        # 남은 일수 계산
        remaining_days = (end_date - now).days

        if remaining_days <= 0:
            return 0

        # [상세 고려 사항] 남은 주차 (소수점 올림 처리)
        # (days + 6) // 7 로직은 일주일이 1일만 남아도 1주로 계산함
        return (remaining_days + 6) // 7

    def _format_response(
        self, 
        min_hours: float, 
        total_weeks: int, 
        remaining_weeks: int, 
        status: str, 
        ratio: float
    ) -> Dict:
        """
        시뮬레이션 결과를 UI 친화적인 형태로 정리

        - 소수점 제거
        - 음수 방어
        - JSON 직렬화 용이
        """
        return {
            'min_hours_per_week': int(round(min_hours)), # 주간 최소 필요 학습 시간
            'total_weeks': int(total_weeks),             # 총 주차 수
            'remaining_weeks': max(remaining_weeks, 0),  # 남은 주차 수
            'status': status,                            # 학습 강도 상태값  | '적정' / '널널' / '빠듯' / '종료' / '판정불가'
            'ratio': ratio                               # 학습 강도 비율 | 0.0 이상
        }


# 싱글톤 인스턴스 관리
_service_instance = None

def get_timeline_service() -> TimelineService:
    """
    TimelineService 싱글톤 반환

    - 불필요한 인스턴스 생성을 방지
    - View / API 레벨에서 일관된 서비스 사용 가능
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = TimelineService()
    return _service_instance