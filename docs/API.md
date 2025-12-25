# API 설계 문서

## 개요

본 문서는 `LIFE-LEARN`의 REST API 엔드포인트를 정리한 문서입니다.

- Base URL: `/api/v1/`
- 모든 API는 JSON 형식으로 요청/응답합니다.
- 인증이 필요한 API는 Authorization 헤더에 토큰을 포함해야 합니다.

```markdown
1. 인증 (Accounts) - /api/v1/accounts/
- 회원가입, 로그인, 로그아웃
- Google 소셜 로그인
- 비밀번호 변경 및 재설정
2. 마이페이지 (Mypage) - /api/v1/mypage/
- 대시보드 통계
- 강좌 관리 (수강 목록, 수강평)
- 위시리스트
- 커뮤니티 활동 조회
- 스크랩 목록
- 프로필 관리
3. 커뮤니티 (Community) - /api/v1/community/
- 게시판 목록
- 게시글 CRUD
- 게시글 검색
- 댓글/대댓글 관리
- 좋아요 & 스크랩
4. 강좌 (Courses) - /api/v1/courses/
- 강좌 목록/상세 조회
- 리뷰 목록
- 추천 강좌
- 상세한 쿼리 파라미터 및 정렬 옵션
5. 강좌 비교 (Comparisons) - /api/v1/comparisons/
- 강좌 비교 분석
- AI 평가, 리뷰 요약, 감성분석
```

<br>

## 1. 인증 (Accounts)

**Base URL:** `/api/v1/accounts/`

### 1.1 회원가입 및 로그인

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| POST | `/accounts/registration/` | 회원가입 | ❌ |
| POST | `/accounts/login/` | 로그인 | ❌ |
| POST | `/accounts/logout/` | 로그아웃 | ✅ |
| GET | `/accounts/user/` | 사용자 정보 조회 | ✅ |
| POST | `/accounts/google/` | Google 소셜 로그인 | ❌ |

### 1.2 비밀번호 관리

| Method | Endpoint | 설명 | 인증 필요 |
|--------|-------------|-----------|---|
| POST | `/accounts/mypage/profile/password/change/` | 비밀번호 변경 | ✅ |

> **참고:** dj-rest-auth를 사용하여 추가 엔드포인트가 제공됩니다.
> - `/accounts/password/reset/` - 비밀번호 재설정 요청
> - `/accounts/password/reset/confirm/` - 비밀번호 재설정 확인

<br>

## 2. 마이페이지 (Mypage)

**Base URL:** `/api/v1/mypage/`

### 2.1 대시보드

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/mypage/dashboard/stats/` | 학습 현황 요약 통계 | ✅ |

### 2.2 강좌 관리

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/mypage/courses/recent/` | 최근 학습 강좌 (이어듣기) | ✅ |
| GET | `/mypage/courses/` | 수강 강좌 목록 | ✅ |
| GET | `/mypage/courses/<int:course_id>/status/` | 강좌 수강 상세 정보 | ✅ |
| POST | `/mypage/courses/<int:course_id>/rating/` | 수강평 등록/수정 | ✅ |
| DELETE | `/mypage/courses/<int:course_id>/rating/` | 수강평 삭제 | ✅ |

**쿼리 파라미터 (강좌 목록):**
- `status`: 수강 상태 필터링 (`enrolled` | `completed`)

### 2.3 관심 강좌 (Wishlist)

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/mypage/wishlist/` | 찜한 강좌 목록 | ✅ |
| POST | `/mypage/wishlist/<int:course_id>/` | 위시리스트 추가 | ✅ |
| DELETE | `/mypage/wishlist/<int:course_id>/` | 위시리스트 삭제 | ✅ |

### 2.4 커뮤니티 활동

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/mypage/community/stats/` | 커뮤니티 활동 통계 | ✅ |
| GET | `/mypage/community/posts/` | 내가 쓴 글 목록 | ✅ |
| GET | `/mypage/community/comments/` | 내가 쓴 댓글 목록 | ✅ |

### 2.5 스크랩

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/mypage/scraps/` | 스크랩한 게시글 목록 | ✅ |

### 2.6 프로필

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/mypage/profile/` | 내 정보 조회 | ✅ |
| PUT | `/mypage/profile/` | 내 정보 수정 | ✅ |

<br>

## 3. 커뮤니티 (Community)

**Base URL:** `/api/v1/community/`

### 3.1 게시판

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/community/boards/` | 전체 게시판 목록 조회 | ❌ |

**응답 정보:**
- 게시판별 게시글 수(`posts_count`) 포함

<br>

### 3.2 게시글

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/community/<int:board_id>/posts/` | 특정 게시판 게시글 목록 조회 (ID 기준) | ❌ |
| POST | `/community/<int:board_id>/posts/` | 특정 게시판에 게시글 작성 | ✅ |
| GET | `/community/<str:board_name>/posts/` | 특정 게시판 게시글 목록 조회 (이름 기준) | ❌ |
| GET | `/community/posts/<int:post_id>/` | 게시글 상세 조회 | ❌ |
| PUT | `/community/posts/<int:post_id>/` | 게시글 전체 수정 | ✅ |
| PATCH | `/community/posts/<int:post_id>/` | 게시글 부분 수정 | ✅ |
| DELETE | `/community/posts/<int:post_id>/` | 게시글 삭제 | ✅ |
<br>

### 3.3 게시글 검색

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/community/posts/search/` | 게시글 검색 | ❌ |

**쿼리 파라미터:**
- `q`: 검색어 (필수)
- `board_id`: 게시판 필터 (선택, 없으면 전체 게시판 검색)

**예시:**
- `/community/posts/search/?q=파이썬`
- `/community/posts/search/?q=테스트&board_id=3`
<br>

### 3.4 댓글

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/community/posts/<int:post_id>/comments/` | 댓글 목록 조회 (최상위 + 대댓글 트리) | ❌ |
| POST | `/community/posts/<int:post_id>/comments/` | 댓글/대댓글 작성 | ✅ |
| PUT | `/community/posts/<int:post_id>/comments/<int:comment_id>/` | 댓글 수정 | ✅ |
| PATCH | `/community/posts/<int:post_id>/comments/<int:comment_id>/` | 댓글 부분 수정 | ✅ |
| DELETE | `/community/posts/<int:post_id>/comments/<int:comment_id>/` | 댓글 삭제 | ✅ |
<br>

### 3.5 좋아요 & 스크랩

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| POST | `/community/posts/<int:post_id>/likes/` | 게시글 좋아요 토글 | ✅ |
| POST | `/community/posts/<int:post_id>/scrap/` | 게시글 스크랩 토글 | ✅ |

<br>
<br>

## 4. 강좌 (Courses)

**Base URL:** `/api/v1/courses/`
<br>

### 4.1 강좌 조회

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/courses/` | 강좌 목록 조회 | ❌ |
| GET | `/courses/<int:pk>/` | 강좌 상세 조회 | ❌ |
| GET | `/courses/<int:course_id>/reviews/` | 강좌 리뷰 목록 조회 | ❌ |
| GET | `/courses/<int:course_id>/recommendations/` | 추천 강좌 조회 | ❌ |
<br>

### 4.2 강좌 목록 쿼리 파라미터

| 파라미터 | 타입 | 설명 | 예시 |
|----------|------|------|------|
| `search` | string | 강좌명/소개 검색 (icontains) | `?search=파이썬` |
| `classfy_name` | string | 대분류 필터링 | `?classfy_name=인문` |
| `middle_classfy_name` | string | 중분류 필터링 | `?middle_classfy_name=교육학` |
| `org_name` | string | 운영기관 필터링 | `?org_name=서울대학교` |
| `professor` | string | 교수 필터링 | `?professor=김교수` |
| `ordering` | string | 정렬 기준 | `?ordering=-average_rating` |
| `page` | int | 페이지 번호 | `?page=2` |
| `page_size` | int | 페이지 크기 | `?page_size=20` |
<br>

### 4.3 정렬 옵션 (ordering)

- `-average_rating`: 평점 높은순 **(기본값)**
- `average_rating`: 평점 낮은순
- `-created_at`: 최신순
- `created_at`: 오래된순
- `name`: 이름 오름차순
- `-name`: 이름 내림차순
- `-review_count`: 리뷰 많은순

<br>
<br>

## 5. 강좌 비교 (Comparisons)

**Base URL:** `/api/v1/comparisons/`

> **참고:** 현재 이 앱은 메인 urls.py에서 주석처리되어 있습니다.
<br>

### 5.1 비교 분석

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| POST | `/comparisons/analyze/` | 강좌 비교 분석 | ✅ |
<br>

### 5.2 AI 분석

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| GET | `/comparisons/courses/<int:course_id>/ai-review/` | 강좌 AI 평가 조회 | ❌ |
| GET | `/comparisons/courses/<int:course_id>/review-summary/` | 강좌 리뷰 요약 조회 | ❌ |
| GET | `/comparisons/courses/<int:course_id>/sentiment/` | 강좌 감성분석 조회 | ❌ |

<br>
<br>

## API 개발 도구

### Swagger / ReDoc (개발 환경에서만 사용 가능)

| Endpoint | 설명 |
|----------|------|
| `/api/schema/` | OpenAPI 스키마 |
| `/api/schema/swagger/` | Swagger UI |
| `/api/schema/redoc/` | ReDoc UI |

> **참고:** `DEBUG=True`일 때만 접근 가능합니다.

<br>

## 참고사항
<br>

### URL 패턴 설계 원칙

1. **RESTful 설계**: 리소스 중심의 URL 구조
2. **명확한 계층 구조**: `/리소스/<id>/하위리소스/`
3. **일관된 네이밍**: 복수형 명사 사용 (`courses`, `posts`, `comments`)
4. **명시적 액션**: 토글/검색 등의 특수 동작은 명시적 엔드포인트 사용
<br>

### 인증 방식

- dj-rest-auth 기반 토큰 인증
- Google OAuth 2.0 소셜 로그인 지원
- django-allauth 통합
<br>

### 페이지네이션

- 기본적으로 페이지네이션 적용
- `page`, `page_size` 파라미터로 제어
- 응답에 `count`, `next`, `previous` 정보 포함
