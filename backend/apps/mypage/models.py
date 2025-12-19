# backend/apps/mypage/models.py

from django.db import models

"""
[ 설계 의도 ]
본 mypage 앱은 독자적인 모델(DB Table)을 정의하지 않습니다.

1. 모델 배치 전략 (Domain-Driven):
   - 데이터의 주체가 되는 도메인별로 모델을 분리하여 배치하였습니다.
   - User 관련: accounts | `User`, `EmailVerfication`, `UserConsent`
   - 게시글/커뮤니티: community | `Board`, `Post`, `Comment`, `PostLikes`, `Scrap`
   - 강의/수강신청: courses | `Course`, `Enrollment`, `WishList`, `CourseReview`

2. mypage 앱의 역할:
   - View & Serializer 전용 앱 (Aggregation Layer)
   - 타 앱(accounts, community, courses)의 모델을 Import하여,
     사용자 중심의 데이터를 조회(Query)하고 가공하여 응답하는 역할을 수행합니다.

3. 기대 효과:
   - 앱 간의 불필요한 순환 참조(Circular Dependency) 방지
   - 데이터 소유권과 참조 로직의 명확한 분리
"""