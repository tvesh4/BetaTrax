from django.urls import path
from .views import *

urlpatterns = [
    path('defect/', post_new_report, name='post_new_report'),
    path('reports/<str:status>/', get_reports, name='get_reports'),
    path('reports/assigned/dev=<str:id>/', get_assigned_defects, name='get_assigned_defects'),
    path('defect/<str:id>/', get_full_report, name='get_full_report'),
    path('defect/<str:id>/<str:new_status>/dev=<str:dev_id>/severity=<str:new_severity>/priority=<str:new_priority>/', patch_update_report, name='patch_update_report'),
    path('defect/<str:id>/<str:new_status>/dev=<str:dev_id>/severity=<str:new_severity>/', patch_update_report, name='patch_update_report'),
    path('defect/<str:id>/<str:new_status>/dev=<str:dev_id>/priority=<str:new_priority>/', patch_update_report, name='patch_update_report'),
    path('defect/<str:id>/<str:new_status>/dev=<str:dev_id>/', patch_update_report, name='patch_update_report'),
    path('defect/<str:id>/<str:new_status>/severity=<str:new_severity>/priority=<str:new_priority>/', patch_update_report, name='patch_update_report'),
    path('defect/<str:id>/<str:new_status>/severity=<str:new_severity>/', patch_update_report, name='patch_update_report'),
    path('defect/<str:id>/<str:new_status>/priority=<str:new_priority>/', patch_update_report, name='patch_update_report'),
    path('defect/<str:id>/<str:new_status>/', patch_update_report, name='patch_update_report'),
    path('comment/<str:id>/', post_comment, name='post_comment'),
    path('product/', post_new_product, name='post_new_product'),
]