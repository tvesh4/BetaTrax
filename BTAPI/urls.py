from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import *

DocumentedTokenObtainPairView = extend_schema_view(
    post=extend_schema(
        tags=['Authentication'],
        summary='Obtain a JWT access + refresh token pair',
    ),
)(TokenObtainPairView)

DocumentedTokenRefreshView = extend_schema_view(
    post=extend_schema(
        tags=['Authentication'],
        summary='Exchange a refresh token for a new access token',
    ),
)(TokenRefreshView)

urlpatterns = [
    path('token/', DocumentedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', DocumentedTokenRefreshView.as_view(), name='token_refresh'),
    path('defect/', post_new_report, name='post_new_report'),
    path('reports/<str:status>/', get_reports, name='get_reports'),
    path('reports/assigned/<str:id>/', get_assigned_defects, name='get_assigned_defects'),
    path('defect/<str:id>/', get_full_report, name='get_full_report'),
    path('update/<str:id>/', patch_update_report, name='patch_update_report'),
    path('comment/<str:id>/', post_comment, name='post_comment'),
    path('product/', post_new_product, name='post_new_product'),
    path('metric/<str:id>/', get_developer_metric, name='get_developer_metric'),
]
