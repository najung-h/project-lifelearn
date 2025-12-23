from django.urls import path
from .views import (
    CourseDetailView, 
    CourseReviewListView, 
    CourseRecommendationView
)

# 개요
"""
/api/v1/courses/
├── <int:pk>/                       # 강좌 상세
├── <int:course_id>/reviews/        # 리뷰 목록
└── <int:course_id>/recommendations/ # 추천 강좌
"""

urlpatterns = [
    # 1. 강의 상세 정보 조회: /api/v1/courses/<id>/
    path('<int:pk>/', CourseDetailView.as_view(), name='course-detail'),
    
    # 2. 강의 리뷰 목록 조회: /api/v1/courses/<id>/reviews/
    path('<int:course_id>/reviews/', CourseReviewListView.as_view(), name='course-reviews'),
    
    # 3. 추천 강의 조회: /api/v1/courses/<id>/recommendations/
    path('<int:course_id>/recommendations/', CourseRecommendationView.as_view(), name='course-recommendations'),
]
