# apps/comparisons/management/commands/generate_ai_reviews.py

import os
import json
import time
import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.courses.models import Course
from apps.comparisons.models import CourseAIReview

"""
[설계의도]
- 모든 강좌(Course)에 대해 LLM 기반의 'AI 평가(CourseAIReview)'를 생성/저장하는 Django management command
- 테스트/운영 상황에 맞게 처리 범위를 제어(--limit, --course-id)하고,
  재생성 정책을 선택(--force)하며,
  호출 속도 제한(--delay)으로 API Rate Limit을 피하도록 설계

[상세 고려사항]
- API 키는 코드에 하드코딩하지 않고 환경변수(GMS_KEY)로 주입하여 보안/운영 편의성을 확보
- 이미 평가가 존재하는 강좌는 기본적으로 스킵(ai_review__isnull=True)하여 비용/시간을 절감
  (단, --force 옵션이면 update_or_create로 덮어쓰기)
- 각 강좌별 DB 저장은 transaction.atomic()으로 감싸
  부분 저장/불완전 저장을 방지하고 원자성을 확보
- 실패한 강좌는 전체 작업을 중단하지 않고 continue로 넘어가
  “대량 처리 배치 작업”에서 흔한 부분 실패 허용 전략 적용
- LLM 응답은 JSON 모드(response_format=json_object)를 사용하고,
  추가로 json.loads + 필수 필드/점수 범위 검증을 통해 데이터 품질을 방어
"""

MODEL_VERSION = 'gpt-4o-mini'
PROMPT_VERSION = 'v1.0'

class Command(BaseCommand):
    help = 'LLM을 사용하여 모든 강좌에 대한 AI 평가 생성'

    def add_arguments(self, parser):
        """
        [설계의도]
        - 배치 작업에서 흔히 필요한 "범위 제어/재실행 정책/속도 제한"을 CLI 옵션으로 제공

        [상세 고려사항]
        - --limit: 개발/테스트 시 일부만 돌려 빠르게 검증할 수 있도록 함
        - --force: 이미 평가가 있어도 다시 생성(업데이트)할 수 있도록 함
        - --course-id: 특정 강좌 1개만 대상으로 디버깅/테스트 가능
        - --delay: API rate limit 및 서버 부하 완화를 위해 호출 간 sleep 제어
        """
        # 처리할 강좌 수를 제한
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='처리할 강좌 수 제한 (테스트용)'
        )
        # 이미 AI 평가가 있어도 재생성할지 여부
        parser.add_argument(
            '--force',
            action='store_true',
            help='이미 평가가 있는 강좌도 재생성'
        )
        # 특정 강좌만 평가(테스트/디버깅용)
        parser.add_argument(
            '--course-id',
            type=int,
            default=None,
            help='특정 강좌만 평가 (테스트용)'
        )
        # API 호출 간 대기 시간
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='API 호출 간 대기 시간 (초)'
        )

    def handle(self, *args, **options):
        """
        [설계의도]
        - 커맨드 실행 시 전체 제어 흐름(설정 → 대상 추출 → 반복 처리 → 결과 요약)을 담당하는 엔트리포인트

        [상세 고려사항]
        - stdout에 진행률/성공/실패를 출력해 배치 실행 로그로 활용 가능
        - 강좌 단위로 try/except 처리하여 일부 실패가 전체를 중단시키지 않도록 함
        """
        # 스타일 출력
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('강좌 AI 평가 생성 시작'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        # =============================================
        # 1. GMS API 설정
        # =============================================
        gms_url = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions"
        gms_key = os.environ.get("GMS_KEY")

        # 키 없으면 즉시 중단
        if not gms_key:
            raise CommandError('GMS_KEY 환경변수가 설정되지 않았습니다.')

        # =============================================
        # 2. 처리할 강좌 필터링
        # =============================================
        if options['course_id']:
            # (A) 특정 강좌만
            courses = Course.objects.filter(id=options['course_id'])
            if not courses.exists():
                raise CommandError(f"ID {options['course_id']} 강좌를 찾을 수 없습니다.")

        elif options['force']:
            # (B) 모든 강좌 (재생성)
            courses = Course.objects.all()

        else:
            # (C) AI 평가가 없는 강좌만
            courses = Course.objects.filter(ai_review__isnull=True)

        # 제한 적용
        if options['limit']:
            # QuerySet slicing -> DB 쿼리로 변환되어 효율적
            courses = courses[:options['limit']]

        # slicing된 QuerySet의 개수 확인
        total_count = courses.count()

        # 처리할 게 없다면 깔끔하게 종료
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('처리할 강좌가 없습니다.'))
            return

        # 진행 시작 안내
        self.stdout.write(f'\n총 {total_count}개 강좌 처리 시작\n')

        # =============================================
        # 3. 통계 변수
        # =============================================
        success_count = 0    # 성공적으로 저장까지 완료한 강좌 수
        error_count = 0      # 처리 중 예외가 발생한 강의 수
        skip_count = 0       # 이미 평가가 있어 스킵한 강의 수 # 확장 가능성 고려

        # =============================================
        # 4. 각 강좌 처리
        # =============================================
        for idx, course in enumerate(courses, 1):
            # 진행률 출력 : 현재 몇 번째 / 몇 개 중에
            self.stdout.write(f'\n[{idx}/{total_count}] 처리 중: {course.name} (ID: {course.id})')

            try:
                # LLM 호출하여 AI 평가 생성
                ai_review_data = self._generate_ai_review(
                    course,
                    gms_url,
                    gms_key
                )

                # DB 저장 (원자성 보장)
                with transaction.atomic():
                    ai_review, created = CourseAIReview.objects.update_or_create(
                        course=course,
                        defaults={
                            'course_summary': ai_review_data['course_summary'][:999],  # 길이 제한
                            'average_rating': ai_review_data['average_rating'],
                            'theory_rating': ai_review_data['theory_rating'],
                            'practical_rating': ai_review_data['practical_rating'],
                            'difficulty_rating': ai_review_data['difficulty_rating'],
                            'duration_rating': ai_review_data['duration_rating'],
                            # 메타데이터
                            'model_version': MODEL_VERSION,
                            'prompt_version': PROMPT_VERSION
                        }
                    )

                action = '생성' if created else '업데이트'
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ {action} 완료 - 종합: {ai_review_data["average_rating"]}/5'
                    )
                )

                success_count += 1

                # Rate Limiting
                if idx < total_count:
                    time.sleep(options['delay'])

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ 에러 발생: {str(e)}')
                )
                continue

        # 5. 결과 요약
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('작업 완료'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'✓ 성공: {success_count}개')
        self.stdout.write(f'✗ 실패: {error_count}개')
        self.stdout.write(f'총 처리: {success_count + error_count}개\n')

    def _generate_ai_review(self, course, gms_url, gms_key):
        """
        LLM을 호출하여 강좌 평가 생성

        Args:
            course: Course 인스턴스
            gms_url: GMS API URL
            gms_key: GMS API 키

        Returns:
            dict: AI 평가 데이터
        """
        # System Prompt
        system_prompt = """
당신은 온라인 강좌 평가 전문가입니다.
주어진 강좌 정보를 분석하여 객관적이고 일관된 평가를 제공해야 합니다.

평가 기준:
1. 이론적 깊이 (theory_rating): 개념과 원리의 깊이
   - 0-1: 매우 기초적, 개념 소개 수준
   - 2-3: 중급, 원리와 개념 설명
   - 4-5: 고급, 심화 이론 및 수학적 증명 포함

2. 실무적 활용도 (practical_rating): 실무 적용 가능성
   - 0-1: 이론 중심, 실습 거의 없음
   - 2-3: 기본 실습 포함
   - 4-5: 프로젝트 중심, 포트폴리오 제작 가능

3. 학습 난이도 (difficulty_rating): 학습자 요구 수준
   - 0-1: 입문자용, 비전공자 가능
   - 2-3: 중급, 기본 지식 필요
   - 4-5: 고급, 전문 지식 필수

4. 학습 기간 (duration_rating): 필요한 학습 기간
   - 0-1: 1-4주 (단기)
   - 2-3: 5-8주 (중기)
   - 4-5: 9주 이상 (장기)

종합 평점(average_rating)은 위 4개 항목의 평균값(소숫점 한 자리수까지 반올림)입니다.

반드시 JSON 형식으로만 응답하세요.
"""

        # User Prompt
        user_prompt = f"""
다음 강좌를 평가해주세요:

**강좌명**: {course.name}

**운영 기관**: {course.org_name or 'N/A'}

**교수자**: {course.professor or 'N/A'}

**분류**: {course.classfy_name} > {course.middle_classfy_name}

**주차 수**: {course.week or 'N/A'}주

**총 학습 시간**: {course.course_playtime or 'N/A'}분

**강좌 설명**:
{course.summary or '설명 없음'}

위 정보를 바탕으로 다음 형식의 JSON으로 평가해주세요:

{{
  "course_summary": "2-3문장으로 강좌의 핵심 내용과 특징 요약",
  "average_rating": 0.0-5.0 실수 (소수점 첫째 자리까지),
  "theory_rating": 0.0-5.0 실수 (소수점 첫째 자리까지),
  "practical_rating": 0.0-5.0 실수 (소수점 첫째 자리까지),
  "difficulty_rating": 0.0-5.0 실수 (소수점 첫째 자리까지),
  "duration_rating": 0.0-5.0 실수 (소수점 첫째 자리까지),
  "reasoning": {{
    "theory": "이론 깊이 평가 이유",
    "practical": "실무 활용도 평가 이유",
    "difficulty": "난이도 평가 이유",
    "duration": "학습 기간 평가 이유"
  }}
}}
"""

        # API 요청 데이터
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {gms_key}"
        }

        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},  # JSON 모드 활성화
            "temperature": 0.3,  # 일관성을 위해 낮은 temperature
            "max_tokens": 500
        }

        # API 호출
        response = requests.post(
            gms_url,
            headers=headers,
            data=json.dumps(data),
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(
                f"GMS API 호출 실패 (Status: {response.status_code}): {response.text}"
            )

        # 응답 파싱
        result = response.json()
        content = result['choices'][0]['message']['content']

        # JSON 파싱
        try:
            ai_review = json.loads(content)
        except json.JSONDecodeError as e:
            raise Exception(f"JSON 파싱 실패: {content}")

        # 필수 필드 검증
        required_fields = [
            'course_summary',
            'average_rating',
            'theory_rating',
            'practical_rating',
            'difficulty_rating',
            'duration_rating'
        ]

        for field in required_fields:
            if field not in ai_review:
                raise Exception(f"필수 필드 누락: {field}")

        # 점수 범위 검증 (0-5)
        rating_fields = [
            'average_rating',
            'theory_rating',
            'practical_rating',
            'difficulty_rating',
            'duration_rating'
        ]

        for field in rating_fields:
            value = ai_review[field]
            # int와 float 모두 허용하되, 소수점 이하는 버림 처리
            if not isinstance(value, (int, float)) or value < 0 or value > 5:
                raise Exception(f"{field} 값이 유효하지 않음: {value} (0-5 사이의 숫자여야 함)")

        return ai_review