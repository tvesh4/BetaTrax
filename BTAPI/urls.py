from django.urls import path
from .views import *

urlpatterns = [
    path('defect/', post_new_report, name='post_new_report'),
    path('defects/New/', get_new_reports, name='get_new_reports'),
    path('defects/Assigned/dev=<int:id>/', get_assigned_defects, name='get_assigned_defects'),
    path('defects/<int:id>/', get_full_report, name='get_full_report'),
    path('defects/<int:id>/<str:new_status>/', patch_update_report, name='patch_update_report'),
    # path('defects/<int:id>/comment/', post_comment, name='post_comment'),
]