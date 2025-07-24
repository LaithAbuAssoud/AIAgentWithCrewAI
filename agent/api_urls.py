from django.urls import path, include
from rest_framework.documentation import include_docs_urls

from . import api_views

# Define URL patterns for RESTful function-based views
urlpatterns = [
    # Model Configuration APIs
    path('api/models/', api_views.model_configurations, name='model-configurations'),
    path('api/models/<int:pk>/', api_views.model_configuration_detail, name='model-configuration-detail'),
    path('api/models/active/', api_views.model_configurations_active, name='model-configurations-active'),
    path('api/models/primary/', api_views.model_configurations_primary, name='model-configurations-primary'),
    path('api/models/<int:pk>/test-connection/', api_views.model_configuration_test_connection, name='model-configuration-test-connection'),
    
    # Agent Configuration APIs
    path('api/agents/', api_views.agent_configurations, name='agent-configurations'),
    path('api/agents/<int:pk>/', api_views.agent_configuration_detail, name='agent-configuration-detail'),
    path('api/agents/active/', api_views.agent_configurations_active, name='agent-configurations-active'),
    path('api/agents/by-type/', api_views.agent_configurations_by_type, name='agent-configurations-by-type'),
    
    # Task Configuration APIs
    path('api/tasks/', api_views.task_configurations, name='task-configurations'),
    path('api/tasks/<int:pk>/', api_views.task_configuration_detail, name='task-configuration-detail'),
    path('api/tasks/active/', api_views.task_configurations_active, name='task-configurations-active'),
    path('api/tasks/workflow/', api_views.task_configurations_workflow, name='task-configurations-workflow'),
    
    # Prompt Template APIs
    path('api/templates/', api_views.prompt_templates, name='prompt-templates'),
    path('api/templates/<int:pk>/', api_views.prompt_template_detail, name='prompt-template-detail'),
    path('api/templates/by-type/', api_views.prompt_templates_by_type, name='prompt-templates-by-type'),
    path('api/templates/<int:pk>/render/', api_views.prompt_template_render, name='prompt-template-render'),
    
    # System Configuration APIs
    path('api/system-config/', api_views.system_configurations, name='system-configurations'),
    path('api/system-config/<int:pk>/', api_views.system_configuration_detail, name='system-configuration-detail'),
    path('api/system-config/active/', api_views.system_configurations_active, name='system-configurations-active'),
    path('api/system-config/as-dict/', api_views.system_configurations_as_dict, name='system-configurations-as-dict'),
    
    # Hiring Session APIs
    path('api/sessions/', api_views.hiring_sessions, name='hiring-sessions'),
    path('api/sessions/<int:pk>/', api_views.hiring_session_detail, name='hiring-session-detail'),
    path('api/sessions/statistics/', api_views.hiring_sessions_statistics, name='hiring-sessions-statistics'),
    path('api/sessions/recent/', api_views.hiring_sessions_recent, name='hiring-sessions-recent'),
    
    # Error Log APIs
    path('api/errors/', api_views.error_logs, name='error-logs'),
    path('api/errors/<int:pk>/', api_views.error_log_detail, name='error-log-detail'),
    path('api/errors/unresolved/', api_views.error_logs_unresolved, name='error-logs-unresolved'),
    path('api/errors/<int:pk>/resolve/', api_views.error_log_resolve, name='error-log-resolve'),
    path('api/errors/resolve-multiple/', api_views.error_logs_resolve_multiple, name='error-logs-resolve-multiple'),
    
    # Agent Test APIs
    path('api/test/run/', api_views.agent_test_run, name='agent-test-run'),
    path('api/test/status/', api_views.agent_test_status, name='agent-test-status'),
    
    # API Documentation
    path('api/docs/', include_docs_urls(title='AI Agent API')),
    
    # DRF Browsable API Authentication
    path('api-auth/', include('rest_framework.urls')),
]
