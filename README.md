# 프로젝트 개요
### 기존 K-MOOC의 검색 및 추천 한계를 극복하고, 개인화된 학습 경험을 제공하는 플랫폼
<br>
<br>

# As Is  - To Be

### AS Is
| As Is | To Be |
| :---: | :---: |
| 중복 강좌 표시 | 검색 기능 개선 |
| ![이미지](./docs/images/as_is_중복.gif) | ![이미지](./docs/images/.png) |
| 검색 | 검색 기능 개선 |
| ![이미지](./docs/images/as_is_검색.gif) | ![이미지](./docs/images/.png) |
| 추천 | 맞춤 강의 추천 |
| ![이미지](./docs/images/as_is_추천.gif) | ![이미지](./docs/images/.png) |
| - | AI 강좌 분석 |
| ![이미지](./docs/images/.png) | ![이미지](./docs/images/.png) |
| UI/UX | UI/UX 개선 |
| ![이미지](./docs/images/as_is_팝업.gif) | ![이미지](./docs/images/.png) |
| 커뮤니티 | 커뮤니티 |
| ![이미지](./docs/images/as_is_커뮤.gif) | ![이미지](./docs/images/.png) |

<br>
<br>

# 팀원
<table>
  <tr>
    <td align="center" width="200px">
      <a href="https://github.com/srogsrogi"> <img src="./docs/images/bubble1.svg" alt="말풍선1" width="100%" />
      </a>
    </td>
    <td align="center" width="200px">
      <a href="./docs/trouble_shooting/나정현.md"> <img src="./docs/images/bubble2.svg" alt="말풍선1" width="100%" />
      </a>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="https://github.com/srogsrogi.png" width="100px" style="border-radius: 50%;" />
      <br />
      <b>강한결</b> <br> (역할)
    </td>
    <td align="center">
      <img src="https://github.com/najung-h.png" width="100px" style="border-radius: 50%;" />
      <br />
      <b>나정현</b> <br> (담당)
    </td>
  </tr>
</table>

<br>
<br>

# 참고 문서
| 내용 | 링크 |
|---|---|
| 단계별로 구현 과정 중 학습한 내용, 어려웠던 부분, 새로 배운 것들 및 느낀 점을 상세히 기록한 README.md | `backend/apps/{각 앱}/README.md` |
| 데이터베이스 모델링 (ERD) | [ERD 보러가기](docs/erd.md) |
| 추천 알고리즘에 대한 기술적 설명 |  |
| 핵심 기능에 대한 설명 | [기능정의서 보러가기](docs/기능정의서.md) |
| 생성형 AI를 활용한 부분 | [LLM으로 강의 평가하기](./backend/apps/comparisons/management/commands/generate_ai_reviews.py) [임베딩하기]|
| (배포했을 경우) 서비스 URL | [사이트 바로가기](life-learn.site) |
| commit message convention | [커밋 메시지 컨벤션](docs/commit-convention.md) |
| git branch rule | [깃 브랜치 전략](docs/git-branch-rule.md) |

<br>
<br>

# 기술 스택 요약
| 분류 | 기술 | 용도 |
|------|------|------|
| 백엔드 프레임워크 | Django 5.2 | 웹 애플리케이션 프레임워크 |
| REST API | Django REST Framework | API 구축 |
| 인증 | dj-rest-auth, django-allauth | 토큰 인증, 소셜 로그인 |
| 데이터베이스 | PostgreSQL (추정) | 관계형 데이터베이스 |
| 검색 엔진 | ElasticSearch | 강좌 추천 (KNN) |
| AI | OpenAI API | LLM 기반 코멘트, 리뷰 요약 |
| AI | AIOps | 프롬프트, 모델명 버전 관리 및 성능 모니터링 |
| ML | MLOps | 모델 학습, 평가 커맨드 생성 및 버전 관리 및 성능 모니터링 |
| 감성분석 | sk-learn | 리뷰 감성분석 |
| API 문서화 | drf-spectacular | Swagger/ReDoc 자동 생성 |
<br>
<br>

## 아키텍쳐
```
```
<br>
<br>

# 설계 원칙
```
```
<br>
<br>

# 실행 방법
1. 로컬

2. 도커

<br>
<br>

# 향후 기술적 개선 방향
- **CI/CD**: GitHub Actions를 활용한 자동 배포
- **Airflow**: Airflow를 통한 데이터 적재 자동화 도입
- **AIOps 및 MLOps** : MLFlow / Grafana를 이용하여 버전 관리 및 성능 모니터링 도입

