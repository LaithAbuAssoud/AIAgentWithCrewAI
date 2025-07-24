from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.db.models import Q
import uuid
import time

from .models import (
    ModelConfiguration, AgentConfiguration, TaskConfiguration,
    PromptTemplate, SystemConfiguration, HiringSession, ErrorLog
)
from .serializers import (
    ModelConfigurationSerializer, AgentConfigurationSerializer,
    TaskConfigurationSerializer, PromptTemplateSerializer,
    SystemConfigurationSerializer, HiringSessionSerializer,
    HiringSessionCreateSerializer, ErrorLogSerializer,
    AgentTestRequestSerializer
)
from .agents_db import get_manager, load_agents, create_tasks


def paginate_queryset(queryset, request, page_size=20):
    """Helper function to paginate querysets"""
    page = request.GET.get('page', 1)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    return {
        'results': page_obj.object_list,
        'count': paginator.count,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'total_pages': paginator.num_pages
    }


def apply_filters_and_search(queryset, request, search_fields=None, filter_fields=None):
    """Helper function to apply filters and search"""
    # Apply search
    search = request.GET.get('search')
    if search and search_fields:
        search_query = Q()
        for field in search_fields:
            search_query |= Q(**{f"{field}__icontains": search})
        queryset = queryset.filter(search_query)
    
    # Apply filters
    if filter_fields:
        for field in filter_fields:
            value = request.GET.get(field)
            if value is not None:
                queryset = queryset.filter(**{field: value})
    
    # Apply ordering
    ordering = request.GET.get('ordering')
    if ordering:
        queryset = queryset.order_by(ordering)
    
    return queryset


# ===== MODEL CONFIGURATION APIs =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def model_configurations(request):
    """
    GET: List all model configurations with filtering and pagination
    POST: Create a new model configuration
    """
    if request.method == 'GET':
        queryset = ModelConfiguration.objects.all()
        
        # Apply filters and search
        search_fields = ['name', 'model_name']
        filter_fields = ['is_active', 'is_fallback', 'priority']
        queryset = apply_filters_and_search(queryset, request, search_fields, filter_fields)
        
        # Default ordering
        queryset = queryset.order_by('-priority', 'name')
        
        # Paginate results
        paginated = paginate_queryset(queryset, request)
        serializer = ModelConfigurationSerializer(paginated['results'], many=True)
        
        return Response({
            'count': paginated['count'],
            'next': paginated['next'],
            'previous': paginated['previous'],
            'total_pages': paginated['total_pages'],
            'results': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = ModelConfigurationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def model_configuration_detail(request, pk):
    """
    GET: Retrieve a specific model configuration
    PUT/PATCH: Update a model configuration
    DELETE: Delete a model configuration
    """
    config = get_object_or_404(ModelConfiguration, pk=pk)
    
    if request.method == 'GET':
        serializer = ModelConfigurationSerializer(config)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = ModelConfigurationSerializer(config, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def model_configurations_active(request):
    """Get only active model configurations"""
    queryset = ModelConfiguration.objects.filter(is_active=True).order_by('-priority')
    serializer = ModelConfigurationSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def model_configurations_primary(request):
    """Get primary (non-fallback) model configurations"""
    queryset = ModelConfiguration.objects.filter(is_active=True, is_fallback=False).order_by('-priority')
    serializer = ModelConfigurationSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def model_configuration_test_connection(request, pk):
    """Test connection to a specific model configuration"""
    config = get_object_or_404(ModelConfiguration, pk=pk)
    try:
        # This would test the actual model connection
        # For now, we'll simulate it
        return Response({
            'success': True,
            'message': f'Connection to {config.model_name} successful',
            'config': ModelConfigurationSerializer(config).data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ===== AGENT CONFIGURATION APIs =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def agent_configurations(request):
    """
    GET: List all agent configurations with filtering and pagination
    POST: Create a new agent configuration
    """
    if request.method == 'GET':
        queryset = AgentConfiguration.objects.select_related('model_config').all()
        
        # Apply filters and search
        search_fields = ['role', 'goal', 'backstory']
        filter_fields = ['agent_type', 'is_active', 'allow_delegation', 'verbose']
        queryset = apply_filters_and_search(queryset, request, search_fields, filter_fields)
        
        # Default ordering
        queryset = queryset.order_by('agent_type')
        
        # Paginate results
        paginated = paginate_queryset(queryset, request)
        serializer = AgentConfigurationSerializer(paginated['results'], many=True)
        
        return Response({
            'count': paginated['count'],
            'next': paginated['next'],
            'previous': paginated['previous'],
            'total_pages': paginated['total_pages'],
            'results': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = AgentConfigurationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def agent_configuration_detail(request, pk):
    """
    GET: Retrieve a specific agent configuration
    PUT/PATCH: Update an agent configuration
    DELETE: Delete an agent configuration
    """
    config = get_object_or_404(AgentConfiguration, pk=pk)
    
    if request.method == 'GET':
        serializer = AgentConfigurationSerializer(config)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = AgentConfigurationSerializer(config, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def agent_configurations_active(request):
    """Get only active agent configurations"""
    queryset = AgentConfiguration.objects.filter(is_active=True)
    serializer = AgentConfigurationSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def agent_configurations_by_type(request):
    """Get agents grouped by type"""
    agent_types = {}
    for agent in AgentConfiguration.objects.filter(is_active=True):
        agent_type = agent.agent_type
        if agent_type not in agent_types:
            agent_types[agent_type] = []
        agent_types[agent_type].append(AgentConfigurationSerializer(agent).data)
    
    return Response(agent_types)


# ===== TASK CONFIGURATION APIs =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def task_configurations(request):
    """
    GET: List all task configurations with filtering and pagination
    POST: Create a new task configuration
    """
    if request.method == 'GET':
        queryset = TaskConfiguration.objects.select_related('agent_config').all()
        
        # Apply filters and search
        search_fields = ['name', 'description']
        filter_fields = ['task_type', 'is_active', 'agent_config']
        queryset = apply_filters_and_search(queryset, request, search_fields, filter_fields)
        
        # Default ordering
        queryset = queryset.order_by('execution_order', 'name')
        
        # Paginate results
        paginated = paginate_queryset(queryset, request)
        serializer = TaskConfigurationSerializer(paginated['results'], many=True)
        
        return Response({
            'count': paginated['count'],
            'next': paginated['next'],
            'previous': paginated['previous'],
            'total_pages': paginated['total_pages'],
            'results': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = TaskConfigurationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def task_configuration_detail(request, pk):
    """
    GET: Retrieve a specific task configuration
    PUT/PATCH: Update a task configuration
    DELETE: Delete a task configuration
    """
    config = get_object_or_404(TaskConfiguration, pk=pk)
    
    if request.method == 'GET':
        serializer = TaskConfigurationSerializer(config)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = TaskConfigurationSerializer(config, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def task_configurations_active(request):
    """Get only active task configurations"""
    queryset = TaskConfiguration.objects.filter(is_active=True).order_by('execution_order')
    serializer = TaskConfigurationSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def task_configurations_workflow(request):
    """Get tasks in execution order for workflow display"""
    workflow_tasks = TaskConfiguration.objects.filter(is_active=True).order_by('execution_order')
    serializer = TaskConfigurationSerializer(workflow_tasks, many=True)
    return Response({
        'workflow': serializer.data,
        'total_steps': workflow_tasks.count()
    })


# ===== PROMPT TEMPLATE APIs =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def prompt_templates(request):
    """
    GET: List all prompt templates with filtering and pagination
    POST: Create a new prompt template
    """
    if request.method == 'GET':
        queryset = PromptTemplate.objects.all()
        
        # Apply filters and search
        search_fields = ['name', 'description', 'content']
        filter_fields = ['template_type', 'is_active']
        queryset = apply_filters_and_search(queryset, request, search_fields, filter_fields)
        
        # Default ordering
        queryset = queryset.order_by('template_type', 'name')
        
        # Paginate results
        paginated = paginate_queryset(queryset, request)
        serializer = PromptTemplateSerializer(paginated['results'], many=True)
        
        return Response({
            'count': paginated['count'],
            'next': paginated['next'],
            'previous': paginated['previous'],
            'total_pages': paginated['total_pages'],
            'results': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = PromptTemplateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def prompt_template_detail(request, pk):
    """
    GET: Retrieve a specific prompt template
    PUT/PATCH: Update a prompt template
    DELETE: Delete a prompt template
    """
    template = get_object_or_404(PromptTemplate, pk=pk)
    
    if request.method == 'GET':
        serializer = PromptTemplateSerializer(template)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = PromptTemplateSerializer(template, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def prompt_templates_by_type(request):
    """Get templates grouped by type"""
    template_types = {}
    for template in PromptTemplate.objects.filter(is_active=True):
        template_type = template.template_type
        if template_type not in template_types:
            template_types[template_type] = []
        template_types[template_type].append(PromptTemplateSerializer(template).data)
    
    return Response(template_types)


@api_view(['POST'])
@permission_classes([AllowAny])
def prompt_template_render(request, pk):
    """Render template with provided variables"""
    template = get_object_or_404(PromptTemplate, pk=pk)
    variables = request.data.get('variables', {})
    
    try:
        rendered_content = template.render(**variables)
        return Response({
            'success': True,
            'rendered_content': rendered_content,
            'variables_used': list(variables.keys())
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ===== SYSTEM CONFIGURATION APIs =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def system_configurations(request):
    """
    GET: List all system configurations with filtering and pagination
    POST: Create a new system configuration
    """
    if request.method == 'GET':
        queryset = SystemConfiguration.objects.all()
        
        # Apply filters and search
        search_fields = ['key', 'description']
        filter_fields = ['data_type', 'is_active']
        queryset = apply_filters_and_search(queryset, request, search_fields, filter_fields)
        
        # Default ordering
        queryset = queryset.order_by('key')
        
        # Paginate results
        paginated = paginate_queryset(queryset, request)
        serializer = SystemConfigurationSerializer(paginated['results'], many=True)
        
        return Response({
            'count': paginated['count'],
            'next': paginated['next'],
            'previous': paginated['previous'],
            'total_pages': paginated['total_pages'],
            'results': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = SystemConfigurationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def system_configuration_detail(request, pk):
    """
    GET: Retrieve a specific system configuration
    PUT/PATCH: Update a system configuration
    DELETE: Delete a system configuration
    """
    config = get_object_or_404(SystemConfiguration, pk=pk)
    
    if request.method == 'GET':
        serializer = SystemConfigurationSerializer(config)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = SystemConfigurationSerializer(config, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def system_configurations_active(request):
    """Get only active system configurations"""
    queryset = SystemConfiguration.objects.filter(is_active=True).order_by('key')
    serializer = SystemConfigurationSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def system_configurations_as_dict(request):
    """Get system configurations as a key-value dictionary"""
    configs = SystemConfiguration.objects.filter(is_active=True)
    config_dict = {config.key: config.get_value() for config in configs}
    return Response(config_dict)


# ===== HIRING SESSION APIs =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def hiring_sessions(request):
    """
    GET: List all hiring sessions with filtering and pagination
    POST: Create a new hiring session
    """
    if request.method == 'GET':
        queryset = HiringSession.objects.select_related('model_config_used').all()
        
        # Apply filters and search
        search_fields = ['session_id', 'candidate_name', 'job_title']
        filter_fields = ['status', 'model_config_used']
        queryset = apply_filters_and_search(queryset, request, search_fields, filter_fields)
        
        # Default ordering
        queryset = queryset.order_by('-created_at')
        
        # Paginate results
        paginated = paginate_queryset(queryset, request)
        serializer = HiringSessionSerializer(paginated['results'], many=True)
        
        return Response({
            'count': paginated['count'],
            'next': paginated['next'],
            'previous': paginated['previous'],
            'total_pages': paginated['total_pages'],
            'results': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = HiringSessionCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def hiring_session_detail(request, pk):
    """
    GET: Retrieve a specific hiring session
    PUT/PATCH: Update a hiring session
    DELETE: Delete a hiring session
    """
    session = get_object_or_404(HiringSession, pk=pk)
    
    if request.method == 'GET':
        serializer = HiringSessionSerializer(session)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = HiringSessionSerializer(session, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def hiring_sessions_statistics(request):
    """Get session statistics"""
    total_sessions = HiringSession.objects.count()
    completed_sessions = HiringSession.objects.filter(status='completed').count()
    failed_sessions = HiringSession.objects.filter(status='failed').count()
    processing_sessions = HiringSession.objects.filter(status='processing').count()
    
    avg_execution_time = None
    if completed_sessions > 0:
        completed = HiringSession.objects.filter(status='completed', execution_time__isnull=False)
        if completed.exists():
            avg_execution_time = sum(s.execution_time for s in completed) / completed.count()

    return Response({
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'failed_sessions': failed_sessions,
        'processing_sessions': processing_sessions,
        'success_rate': round((completed_sessions / total_sessions * 100) if total_sessions > 0 else 0, 2),
        'average_execution_time': round(avg_execution_time, 2) if avg_execution_time else None
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def hiring_sessions_recent(request):
    """Get recent sessions"""
    limit = int(request.GET.get('limit', 10))
    recent_sessions = HiringSession.objects.order_by('-created_at')[:limit]
    serializer = HiringSessionSerializer(recent_sessions, many=True)
    return Response(serializer.data)


# ===== ERROR LOG APIs =====

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def error_logs(request):
    """
    GET: List all error logs with filtering and pagination
    POST: Create a new error log
    """
    if request.method == 'GET':
        queryset = ErrorLog.objects.select_related('session', 'model_config').all()
        
        # Apply filters and search
        search_fields = ['message']
        filter_fields = ['error_type', 'resolved']
        queryset = apply_filters_and_search(queryset, request, search_fields, filter_fields)
        
        # Default ordering
        queryset = queryset.order_by('-created_at')
        
        # Paginate results
        paginated = paginate_queryset(queryset, request)
        serializer = ErrorLogSerializer(paginated['results'], many=True)
        
        return Response({
            'count': paginated['count'],
            'next': paginated['next'],
            'previous': paginated['previous'],
            'total_pages': paginated['total_pages'],
            'results': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = ErrorLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def error_log_detail(request, pk):
    """
    GET: Retrieve a specific error log
    PUT/PATCH: Update an error log
    DELETE: Delete an error log
    """
    error = get_object_or_404(ErrorLog, pk=pk)
    
    if request.method == 'GET':
        serializer = ErrorLogSerializer(error)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = ErrorLogSerializer(error, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        error.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def error_logs_unresolved(request):
    """Get unresolved errors"""
    unresolved_errors = ErrorLog.objects.filter(resolved=False).order_by('-created_at')
    serializer = ErrorLogSerializer(unresolved_errors, many=True)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([AllowAny])
def error_log_resolve(request, pk):
    """Mark an error as resolved"""
    error = get_object_or_404(ErrorLog, pk=pk)
    error.resolved = True
    error.save()
    
    return Response({
        'success': True,
        'message': f'Error {error.id} marked as resolved'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def error_logs_resolve_multiple(request):
    """Mark multiple errors as resolved"""
    error_ids = request.data.get('error_ids', [])
    
    if not error_ids:
        return Response({
            'success': False,
            'error': 'No error IDs provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    updated_count = ErrorLog.objects.filter(id__in=error_ids).update(resolved=True)
    
    return Response({
        'success': True,
        'message': f'{updated_count} errors marked as resolved'
    })


# ===== AGENT TEST APIs =====

@api_view(['POST'])
@permission_classes([AllowAny])
def agent_test_run(request):
    """Run agent configuration test"""
    serializer = AgentTestRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    test_type = serializer.validated_data['test_type']
    
    try:
        if test_type == 'basic':
            return _run_basic_test()
        elif test_type == 'full':
            return _run_full_test(serializer.validated_data.get('test_data', {}))
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def agent_test_status(request):
    """Get current system status"""
    try:
        manager = get_manager()
        
        # Get active configurations count
        active_models = ModelConfiguration.objects.filter(is_active=True).count()
        active_agents = AgentConfiguration.objects.filter(is_active=True).count()
        active_tasks = TaskConfiguration.objects.filter(is_active=True).count()
        active_templates = PromptTemplate.objects.filter(is_active=True).count()
        
        # Get current model info
        current_model = manager.current_model_config
        
        # Get recent sessions
        total_sessions = HiringSession.objects.count()
        successful_sessions = HiringSession.objects.filter(status='completed').count()
        failed_sessions = HiringSession.objects.filter(status='failed').count()
        
        # Get unresolved errors
        unresolved_errors = ErrorLog.objects.filter(resolved=False).count()
        
        return Response({
            'status': 'operational',
            'current_model': {
                'id': current_model.id if current_model else None,
                'name': current_model.name if current_model else 'Unknown',
                'model_name': current_model.model_name if current_model else 'Unknown',
                'temperature': current_model.temperature if current_model else 0,
                'max_tokens': current_model.max_tokens if current_model else 0,
            },
            'configuration_counts': {
                'active_models': active_models,
                'active_agents': active_agents,
                'active_tasks': active_tasks,
                'active_templates': active_templates,
            },
            'session_stats': {
                'total_sessions': total_sessions,
                'successful_sessions': successful_sessions,
                'failed_sessions': failed_sessions,
                'success_rate': round((successful_sessions / total_sessions * 100) if total_sessions > 0 else 0, 2),
            },
            'health': {
                'unresolved_errors': unresolved_errors,
                'manager_initialized': manager is not None,
                'model_available': current_model is not None,
            }
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e),
            'manager_initialized': False,
            'model_available': False,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===== HELPER FUNCTIONS =====

def _run_basic_test():
    """Run basic configuration test"""
    manager = get_manager()
    
    # Test system configs
    fallback_enabled = manager.get_system_config('FALLBACK_ENABLED', False)
    max_retries = manager.get_system_config('MAX_RETRY_ATTEMPTS', 3)
    
    # Test prompt templates
    job_prompt = manager.get_prompt_template('job_matching_instruction', token_limit=1500)
    bias_prompt = manager.get_prompt_template('bias_audit_instruction', token_limit=1000)
    
    return Response({
        'success': True,
        'test_type': 'basic',
        'results': {
            'manager_initialized': True,
            'model_available': manager.current_model_config is not None,
            'system_configs_accessible': fallback_enabled is not None,
            'prompt_templates_accessible': bool(job_prompt and bias_prompt),
            'current_model': manager.current_model_config.name if manager.current_model_config else None,
            'system_configs': {
                'fallback_enabled': fallback_enabled,
                'max_retries': max_retries
            }
        }
    })


def _run_full_test(test_data):
    """Run full agent test with sample data"""
    manager = get_manager()
    
    # Load agents and tasks
    job_matcher, bias_auditor = load_agents()
    job_task, bias_task = create_tasks(job_matcher, bias_auditor)
    
    # Create test session
    session_id = f"api_test_{uuid.uuid4().hex[:8]}"
    test_input = test_data if test_data else {
        'candidate_name': 'Test Candidate',
        'job_title': 'Test Position',
        'resume': 'Sample resume content...',
        'interview_notes': 'Sample interview notes...'
    }
    
    start_time = time.time()
    session = manager.log_session_start(session_id, test_input)
    
    # Simulate processing (in real scenario, this would run the crew)
    time.sleep(2)
    
    execution_time = time.time() - start_time
    test_results = {
        'job_matching_decision': 'SELECT',
        'bias_audit_result': 'FAIR',
        'confidence': 0.85,
        'test_mode': True
    }
    
    manager.log_session_complete(session, test_results, execution_time)
    
    return Response({
        'success': True,
        'test_type': 'full',
        'session_id': session_id,
        'execution_time': execution_time,
        'results': test_results,
        'test_input': test_input
    })
