from django.urls import path
from . import views
from .views import get_latest_status

urlpatterns = [

    # Video Feed
    path('video_feed/', views.video_feed_view, name='video_feed'),

    # Status API
    path('api/latest_status/', get_latest_status, name='latest_status'),

    # Home And Landing
    path('', views.home, name='home'),
    path('landing/', views.landing_page, name='landing'),

    # Event Logs API
    path('api/logs/', views.event_logs_view, name='event_logs'),

    # Analytics API
    path('api/analytics/', views.analytics_view, name='analytics'),

    # Authentication API
    path('api/register/', views.register_view, name='register'),
    path('api/login/', views.login_view, name='login'),
    path('api/logout/', views.logout_view, name='logout'),
    path('api/current-user/', views.current_user_view, name='current_user'),

    # Frontend Pages
    path('login/', views.login_page, name='login_page'),
    path('register/', views.register_page, name='register_page'),

    # Lift API
    path('api/lift/process-image/', views.process_lift_image, name='process_lift_image'),
    path('api/lift/process-video/', views.process_lift_video, name='process_lift_video'),
    path('api/lift/usage-stats/', views.lift_usage_stats, name='lift_usage_stats'),
    path('api/lift/list/', views.lift_list, name='lift_list'),
]
