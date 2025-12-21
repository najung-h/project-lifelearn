from django.shortcuts import render

<<<<<<< Updated upstream
# Create your views here.
=======
from .models import Course, CourseReview
from .serializers import CourseDetailSerializer, CourseReviewSerializer
from apps.mypage.serializers import SimpleCourseSerializer

class CourseDetailView(generics.RetrieveAPIView):
    """
    [API]
    - GET: /api/v1/courses/{course_id}/
    
    [설계 의도]
    - 강좌의 상세 정보 및 유저별 맞춤 정보(찜 여부)를 제공
    - 상세 페이지는 비로그인 유저도 접근 가능해야 하므로 AllowAny 적용
    """
    queryset = Course.objects.all()
    serializer_class = CourseDetailSerializer
    permission_classes = [AllowAny] # 누구나 조회 가능

    def get_serializer_context(self):
        # SerializerMethodField에서 request.user를 사용하기 위해 context 전달
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

class CourseReviewListView(generics.ListAPIView):
    """
    [API]
    - GET: /api/v1/courses/{course_id}/reviews/
    """
    serializer_class = CourseReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        course_id = self.kwargs.get('course_id') # urls.py의 변수명과 일치해야 함 (보통 pk 또는 course_id)
        # 만약 urls.py에서 <int:course_id>라고 썼다면 위처럼, <int:pk>라면 self.kwargs['pk']
        # 안전하게 kwargs에서 가져옴
        return CourseReview.objects.filter(course_id=course_id).select_related('user').order_by('-created_at')

# 서버 시작 시 클라이언트 생성
ES_CLIENT = Elasticsearch(getattr(settings, 'ELASTICSEARCH_URL', 'http://elasticsearch:9200'))

class CourseRecommendationView(APIView):
    def get(self, request, course_id):
        # 1. 기준 강좌 벡터 추출
        target_course = get_object_or_404(Course, id=course_id)
        query_vector = target_course.embedding

        if query_vector is None:
            return Response([])

        try:
            # 2. 순수 k-NN 쿼리 (8.x 버전 스타일 키워드 인자 사용 권장)
            # vector 필드가 'embedding'이고 dense_vector 타입이어야 함.
            res = ES_CLIENT.search(
                index="kmooc_courses",
                knn={
                    "field": "embedding",
                    "query_vector": list(query_vector), # 벡터 리스트 변환
                    "k": 5,
                    "num_candidates": 200
                },
                source=["id"] # _source에는 id만 가져옴
            )
            
            # 3. 유사도 순서대로 ID 리스트 추출 (자기 자신은 필터링)
            hits = res.get("hits", {}).get("hits", [])
            hit_ids = []
            for hit in hits:
                source = hit.get("_source", {})
                h_id = source.get("id")
                # h_id가 있고, 현재 강좌 ID와 다르면 추가
                if h_id is not None and int(h_id) != int(course_id):
                    hit_ids.append(int(h_id))
            
            hit_ids = hit_ids[:4] # 최대 4개

            # 4. DB 데이터 조회
            course_queryset = Course.objects.filter(id__in=hit_ids)
            
            # 5. 유사도 기준 내림차순 정렬 (DB 조회 시 순서가 섞이므로 재정렬)
            course_map = {course.id: course for course in course_queryset}
            sorted_courses = [course_map[cid] for cid in hit_ids if cid in course_map]

            serializer = SimpleCourseSerializer(sorted_courses, many=True)
            return Response(serializer.data)

        except Exception as e:
            import traceback
            print(f"❌ [Recommendation Error]: {str(e)}")
            print(traceback.format_exc())
            # 에러 발생 시 500 대신 빈 리스트 반환하여 프론트엔드 에러 방지
            return Response([], status=200)
>>>>>>> Stashed changes
