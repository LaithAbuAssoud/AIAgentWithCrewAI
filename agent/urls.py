from django.urls import path, include
from . import views

app_name = 'agent'

urlpatterns = [
    # Dashboard and main views
    path('', views.configuration_dashboard, name='dashboard'),
    
    # Legacy function-based API endpoints (kept for backward compatibility)
    path('api/status/', views.api_configuration_status, name='api_status'),
    path('api/test/', views.agent_test_api, name='api_test'),
    path('api/configurations/', views.get_active_configurations_api, name='api_configurations'),
    path('api/sessions/', views.get_session_history_api, name='api_sessions'),
    path('api/errors/', views.get_error_logs_api, name='api_errors'),
    path('api/update-model/', views.update_model_config_api, name='api_update_model'),
    path('api/update-template/', views.update_prompt_template_api, name='api_update_template'),
    
    # Include new DRF API URLs
    path('', include('agent.api_urls')),
]
