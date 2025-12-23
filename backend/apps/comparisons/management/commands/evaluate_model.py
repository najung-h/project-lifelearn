# apps/comparisons/management/commands/evaluate_model.py

"""
[설계 의도]
- 저장된 감성분석 모델을 새로운 테스트 데이터로 평가하여
  운영 중인 모델의 성능을 모니터링하고, 모델 업데이트 필요 여부를 판단하기 위함
- Django management command로 구현해 CI/배포 파이프라인에서
  모델 검증을 자동화할 수 있도록 함

[상세 고려사항]
- train_model과 동일한 데이터 검증 로직 재사용
- 평가 결과를 JSON으로 저장해 시계열 분석 가능
- 혼동 행렬, 분류 리포트 등 상세 지표 제공
  - labels: negative(0), positive(1)
- 모델 로드 실패 시 명확한 에러 메시지
- 다양한 테스트 데이터셋을 지정할 수 있도록 CLI 옵션 제공
- 평가 결과를 콘솔에 요약 출력하고, --verbose 옵션으로
    샘플별 예측 결과도 확인 가능
- 평가 결과 저장 경로를 유연하게 지정할 수 있도록 옵션 제공

[사용 예시]
python manage.py evaluate_model
python manage.py evaluate_model --test-data fixtures/new_test.csv
python manage.py evaluate_model --model-path ai_models/v2.0/model.joblib
python manage.py evaluate_model --output evaluation_results/custom_eval.json --verbose


"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)

# 기본 경로 상수
# 하드 코딩은 지양.
DEFAULT_MODEL_PATH = Path(settings.BASE_DIR) / "apps" / "comparisons" / "ai_models" / "sentiment_pipeline.joblib"
DEFAULT_TEST_DATA_PATH = Path(settings.BASE_DIR) / "apps" / "comparisons" / "fixtures" / "sentiment_test_data.csv"
DEFAULT_OUTPUT_DIR = Path(settings.BASE_DIR) / "apps" / "comparisons" / "evaluation_results"

# Numpy 타입을 JSON 직렬화할 수 없으므로 변환 헬퍼
    # Python의 json은 numpy.int64, numpy.float32 같은 타입을 기본적으로 직렬화 못함
    # 그래서 "numpy 타입이면 python 기본 타입으로 바꿔서" dump할 수 있게 만든 커스텀 인코더

class NumpyEncoder(json.JSONEncoder):                   # json.JSONEncoder 상속해서 default()만 오버라이드
    def default(self, obj):                             # json.dump()가 모르는 타입을 만났을 때 호출되는 훅
        if isinstance(obj, np.integer):                 # numpy 정수형이면
            return int(obj)                             # python int로 변환
        if isinstance(obj, np.floating):                # numpy 실수 타입이면
            return float(obj)                           # python float로 변환
        if isinstance(obj, np.ndarray):                 # numpy 배열이면
            return obj.tolist()                         # 리스트로 변환 (JSON 호환)
        return super(NumpyEncoder, self).default(obj)   # 그 외 타입은 부모 처리로 넘김.

class Command(BaseCommand): # BaseCommand 상속, 장고가 manage.py 커맨드로 실행할 클래스 (규약!)
    """
    감성분석 모델 평가 커맨드

    [사용 예시]
    python manage.py evaluate_model
    python manage.py evaluate_model --test-data fixtures/new_test.csv
    python manage.py evaluate_model --model-path ai_models/v2.0/model.joblib
    """

    help = '감성분석 모델 평가 및 성능 측정'

    # CLI 옵션 정의
    def add_arguments(self, parser):
        """
        [설계 의도]
        - 테스트 데이터, 모델 경로, 출력 경로를 CLI 옵션으로 제공
        - 다양한 시나리오에서 평가를 유연하게 수행하기 위함

        [옵션 설명]
        --test-data: 테스트 데이터 CSV 파일 경로
        --model-path: 평가할 모델 파일 경로 (joblib)
        --output: 평가 결과 JSON 저장 경로 (자동 생성)
        --verbose: 상세 출력 여부
        """
        parser.add_argument(
            '--test-data',
            type=str,
            default=str(DEFAULT_TEST_DATA_PATH),
            help='테스트 데이터 CSV 파일 경로 (content, label 컬럼 필요)'
        )

        parser.add_argument(
            '--model-path',
            type=str,
            default=str(DEFAULT_MODEL_PATH),
            help='평가할 모델 파일 경로 (.joblib)'
        )

        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='평가 결과 JSON 저장 경로 (기본: evaluation_results/YYYYMMDD_HHMMSS.json)'
        )

        parser.add_argument(
            '--verbose',
            action='store_true',
            help='상세 출력 (샘플별 예측 결과 표시)'
        )

    def handle(self, *args, **options):
        """
        평가 메인 로직

        [처리 흐름]
        1. 모델 로드
        2. 테스트 데이터 로드 및 검증
        3. 예측 수행
        4. 평가 지표 계산
        5. 결과 출력 및 저장
        """
        # 시작 안내
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('감성분석 모델 평가 시작'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        # =====================================
        # 1. 모델 로드
        # =====================================

        model_path = Path(options['model_path'])
        self.stdout.write(f'\n[1/5] 모델 로드: {model_path}')

        if not model_path.exists():
            raise CommandError(
                f'모델 파일을 찾을 수 없습니다: {model_path}\n'
                f'먼저 "python manage.py train_model"로 모델을 학습해주세요.'
            )

        try:
            pipeline = joblib.load(model_path) # 파이프라인 로드
            self.stdout.write('  ✓ 모델 로드 완료')

            # 모델 정보 출력
            if hasattr(pipeline, 'classes_'):
                self.stdout.write(f'  ✓ 클래스: {list(pipeline.classes_)}')

        except Exception as e:
            raise CommandError(f'모델 로드 중 오류 발생: {str(e)}')

        # =====================================
        # 2. 테스트 데이터 로드
        # =====================================

        test_data_path = Path(options['test_data'])
        self.stdout.write(f'\n[2/5] 테스트 데이터 로드: {test_data_path}')

        if not test_data_path.exists():
            raise CommandError(f'테스트 데이터를 찾을 수 없습니다: {test_data_path}')

        try:
            df = pd.read_csv(test_data_path, encoding='utf-8-sig')
            self.stdout.write(f'  ✓ 총 {len(df)}개 데이터 로드')
        except Exception as e:
            raise CommandError(f'테스트 데이터 로드 중 오류: {str(e)}')

        # 데이터 검증
        required_columns = ['content', 'label']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise CommandError(
                f'필수 컬럼이 없습니다: {missing_columns}\n'
                f'CSV 파일은 "content"와 "label" 컬럼을 포함해야 합니다.'
            )

        # 결측치 제거
        original_len = len(df)
        df = df.dropna(subset=['content', 'label'])

        if len(df) < original_len:
            self.stdout.write(
                self.style.WARNING(
                    f'  ! 결측치 {original_len - len(df)}개를 제거했습니다.'
                )
            )

        # =====================================
        # 3. 예측 수행
        # =====================================

        self.stdout.write(f'\n[3/5] 예측 수행')

        X_test = df['content']
        y_test = df['label']

        try:
            y_pred = pipeline.predict(X_test)

            if hasattr(pipeline, "predict_proba"):
                y_proba = pipeline.predict_proba(X_test)
            else:
                y_proba = None
                self.stdout.write(self.style.WARNING("  ! 이 모델은 확률 예측(predict_proba)을 지원하지 않습니다."))
                
            self.stdout.write(f'  ✓ {len(y_pred)}개 샘플 예측 완료')

        except Exception as e:
            raise CommandError(f'예측 중 오류 발생: {str(e)}')

        # =====================================
        # 4. 평가 지표 계산
        # - 라벨 순서 고정 (negative, positive) = (0, 1)
        # =====================================

        self.stdout.write(f'\n[4/5] 평가 지표 계산')

        # 순서 고정 # 헷갈리지 않도록 
        TARGET_LABELS = ['negative', 'positive']

        # 정확도
        accuracy = accuracy_score(y_test, y_pred)
        self.stdout.write(f'  ✓ 정확도: {accuracy:.4f} ({accuracy*100:.2f}%)')

        # Precision, Recall, F1 (클래스별)
        precision, recall, f1, support = precision_recall_fscore_support(
            y_test, y_pred, average=None, labels=TARGET_LABELS
        )

        # 분류 리포트
        report_dict = classification_report(
            y_test, y_pred,
            output_dict=True,
            labels=TARGET_LABELS
        )

        self.stdout.write('\n  클래스별 성능:')
        for i, label in enumerate(TARGET_LABELS):
            self.stdout.write(
                f'    {label:10s} - Precision: {precision[i]:.4f}, '
                f'Recall: {recall[i]:.4f}, F1: {f1[i]:.4f}, '
                f'Support: {support[i]}'
            )

        # 혼동 행렬
        cm = confusion_matrix(y_test, y_pred, labels=TARGET_LABELS)

        self.stdout.write('\n  Confusion Matrix:')
        self.stdout.write(f'    TN: {cm[0][0]:4d}  |  FP: {cm[0][1]:4d}')
        self.stdout.write(f'    FN: {cm[1][0]:4d}  |  TP: {cm[1][1]:4d}')

        # Verbose 모드: 예측 샘플 출력
        if options['verbose']:
            self.stdout.write('\n  예측 샘플 (처음 5개):')
            for i in range(min(5, len(df))):
                text = X_test.iloc[i][:50] + '...'
                true_label = y_test.iloc[i]
                pred_label = y_pred[i]

                conf_str = ""
                if y_proba is not None:
                    confidence = max(y_proba[i])
                    conf_str = f'(신뢰도: {confidence:.2f})'

                match_icon = '✓' if true_label == pred_label else '✗'
                self.stdout.write(
                    f'    {match_icon} "{text}"\n'
                    f'      실제: {true_label}, 예측: {pred_label} {conf_str}'
                )

        # =====================================
        # 5. 결과 저장
        # =====================================

        self.stdout.write(f'\n[5/5] 결과 저장')

        # 출력 경로 결정
        if options['output']:
            output_path = Path(options['output'])
        else:
            DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = DEFAULT_OUTPUT_DIR / f'evaluation_{timestamp}.json'

        # 평가 결과 구성
        evaluation_result = {
            'timestamp': datetime.now().isoformat(),
            'model_path': str(model_path),
            'test_data_path': str(test_data_path),
            'test_size': len(df),
            'metrics': {
                'accuracy': float(accuracy),
                'precision_negative': float(precision[0]),    # negative
                'recall_negative': float(recall[0]),          # negative
                'f1_negative': float(f1[0]),                  # negative
                'precision_positive': float(precision[1]),    # positive
                'recall_positive': float(recall[1]),          # positive
                'f1_positive': float(f1[1])                   # positive
            },
            'confusion_matrix': {
                'TN': int(cm[0][0]),
                'FP': int(cm[0][1]),
                'FN': int(cm[1][0]),
                'TP': int(cm[1][1])
            },
            'classification_report': report_dict
        }

        # JSON 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation_result, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)

        self.stdout.write(f'  ✓ 평가 결과 저장: {output_path}')

        # 완료
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('평가 완료!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))