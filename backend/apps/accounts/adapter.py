from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from django.http import HttpRequest
from django.db import transaction

from .models import User, UserConsent


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    [ 설계 의도 ]
    - Custom User 모델에서 name 필드가 필수(blank=False)인 구조를 사용하는 경우,
      django-allauth의 기본 소셜 회원가입 로직만으로는 name 값이 채워지지 않아
      User 생성 단계에서 무결성 오류가 발생할 수 있다.
    - 특히 Google OAuth의 경우 name 정보가 extra_data에 존재하지만,
      allauth는 이를 자동으로 User.name에 매핑하지 않는다.
    - 따라서 소셜 로그인 최초 가입 시점에 name 필드를 보완하는 책임을
      SocialAccountAdapter 계층에서 명확히 가져간다.

    - 또한 서비스 정책상 회원 가입 시 UserConsent(약관 동의) 생성이 필수라면,
      User 생성과 Consent 생성은 논리적으로 하나의 작업 단위로 취급되어야 한다.
    - 이를 위해 save_user 전체를 트랜잭션으로 감싸
      부분 실패로 인한 데이터 불일치 상태를 예방한다.

    [ 상세 구현 사항 ]
    - DefaultSocialAccountAdapter.save_user 를 override 하되,
      allauth의 기본 동작은 최대한 유지(super 호출)하고
      우리 도메인 제약 조건(name 필수)만 최소한으로 보완한다.
    - 본 Adapter는 "소셜 최초 가입" 시점에만 개입하며,
      기존 유저 로그인에는 영향을 주지 않는다.
    """

    @transaction.atomic
    def save_user(self, request: HttpRequest, sociallogin: SocialLogin, form=None) -> User:
        """
        [ 설계 의도 ]
        - 소셜 로그인 성공 후, 아직 로컬 User와 매핑되지 않은 경우 호출되는 메서드이다.
        - 이 메서드는 '소셜 계정 기반 최초 회원가입'의 단일 진입점 역할을 한다.
        - 따라서 User 생성과 그에 수반되는 필수 보완 로직을 이 위치에서 처리한다.

        [ 상세 구현 사항 ]
        처리 흐름:
        1) allauth가 제공하는 기본 User 생성 로직을 그대로 호출한다.
        2) 생성된 User 객체의 name 필드가 비어 있는 경우에만,
           소셜 제공자(Google)의 extra_data를 활용하여 name 값을 보완한다.
        3) 트랜잭션 범위 내에서 처리하여,
           User 저장 중 예외 발생 시 전체 롤백을 보장한다.

        트랜잭션 적용 이유:
        - User 생성 이후 추가 로직(name 보완, 향후 Consent 생성 등)이
          논리적으로 하나의 가입 행위에 속하므로,
          중간 실패 시 불완전한 가입 상태를 방지해야 한다.
        """

        # [ 상세 구현 사항 ]
        # 1) allauth 기본 로직을 통해 User 인스턴스를 생성한다.
        #    - 이메일, username, social account 연결 등
        #      allauth 내부 표준 절차를 그대로 따른다.
        user = super().save_user(request, sociallogin, form)

        # [ 설계 의도 ]
        # 2) Custom User 모델에서 name이 필수인 경우를 대비한 보완 로직
        #
        # [ 상세 구현 사항 ]
        # - 이미 name 값이 존재하는 경우에는 덮어쓰지 않는다.
        # - sociallogin.account.extra_data는 OAuth provider가 내려준 원본 사용자 정보이다.
        # - Google의 경우 일반적으로 다음 필드가 포함될 수 있다:
        #   * name          : 전체 이름
        #   * given_name    : 이름
        #   * family_name  : 성
        # - extra_data가 None일 가능성을 고려하여 or {}로 방어 처리한다.
        if not user.name:
            extra = sociallogin.account.extra_data or {}

            # [ 상세 구현 사항 ]
            # 우선순위 1: provider가 내려준 전체 이름(name)
            name = (extra.get("name") or "").strip()

            # [ 상세 구현 사항 ]
            # 우선순위 2: given_name + family_name 조합
            # - 전체 이름이 없는 경우를 대비한 fallback 전략
            if not name:
                given = (extra.get("given_name") or "").strip()
                family = (extra.get("family_name") or "").strip()
                name = f"{given} {family}".strip()

            # [ 상세 구현 사항 ]
            # - update_fields를 명시하여 name 필드만 부분 업데이트한다.
            # - 불필요한 전체 row update를 방지하고,
            #   의도하지 않은 필드 변경 가능성을 줄인다.
            user.name = name
            user.save(update_fields=["name"])

        # [ 설계 의도 ]
        # - User 객체 생성 및 필수 필드 보완이 모두 완료된 상태의 User를 반환한다.
        # - 이후 allauth는 이 User를 기준으로 소셜 계정 연결을 마무리한다.
        return user
