from django.urls import path
from .views import *

urlpatterns = [
    path('defect/', post_new_report, name='post_new_report'),
    path('defects/<str:status>/', get_reports, name='get_reports'),
    path('defects/Assigned/dev=<int:id>/', get_assigned_defects, name='get_assigned_defects'),
    path('defect/<int:id>/', get_full_report, name='get_full_report'),
    path('defects/<int:id>/<str:new_status>/dev=<int:dev_id>/', patch_update_report, name='patch_update_report'),
    path('defects/<int:id>/<str:new_status>/dev=<int:dev_id>/severity=<int:new_severity>/', patch_update_report, name='patch_update_report'),
    path('defects/<int:id>/<str:new_status>/dev=<int:dev_id>/priority=<int:new_priority>/', patch_update_report, name='patch_update_report'),
    path('defects/<int:id>/<str:new_status>/dev=<int:dev_id>/severity=<int:new_severity>/priority=<int:new_priority>/', patch_update_report, name='patch_update_report'),
    # path('defects/<int:id>/comment/', post_comment, name='post_comment'),
]