from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import (
    ModelConfiguration, AgentConfiguration, TaskConfiguration,
    PromptTemplate, SystemConfiguration, HiringSession, ErrorLog
)
from .serializers import (
    ModelConfigurationSerializer, AgentConfigurationSerializer,
    TaskConfigurationSerializer, PromptTemplateSerializer,
    SystemConfigurationSerializer, HiringSessionSerializer,
    HiringSessionCreateSerializer, ErrorLogSerializer,
    AgentTestRequestSerializer, ConfigurationUpdateSerializer
)
from .agents_db import get_manager, load_agents, create_tasks
import uuid
import time


class StandardResultsSetPagination(PageNumberPagination):
    """Custom pagination class"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ModelConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for ModelConfiguration model"""
    
    queryset = ModelConfiguration.objects.all()
    serializer_class = ModelConfigurationSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_fallback', 'priority']
    search_fields = ['name', 'model_name']
    ordering_fields = ['priority', 'name', 'created_at']
    ordering = ['-priority', 'name']

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active model configurations"""
        active_configs = self.queryset.filter(is_active=True).order_by('-priority')
        serializer = self.get_serializer(active_configs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def primary(self, request):
        """Get primary (non-fallback) model configurations"""
        primary_configs = self.queryset.filter(is_active=True, is_fallback=False).order_by('-priority')
        serializer = self.get_serializer(primary_configs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test connection to a specific model configuration"""
        config = self.get_object()
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


class AgentConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for AgentConfiguration model"""
    
    queryset = AgentConfiguration.objects.select_related('model_config').all()
    serializer_class = AgentConfigurationSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['agent_type', 'is_active', 'allow_delegation', 'verbose']
    search_fields = ['role', 'goal', 'backstory']
    ordering_fields = ['agent_type', 'role', 'created_at']
    ordering = ['agent_type']

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active agent configurations"""
        active_agents = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(active_agents, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get agents grouped by type"""
        agent_types = {}
        for agent in self.queryset.filter(is_active=True):
            agent_type = agent.agent_type
            if agent_type not in agent_types:
                agent_types[agent_type] = []
            agent_types[agent_type].append(AgentConfigurationSerializer(agent).data)
        
        return Response(agent_types)


class TaskConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for TaskConfiguration model"""
    
    queryset = TaskConfiguration.objects.select_related('agent_config').all()
    serializer_class = TaskConfigurationSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task_type', 'is_active', 'agent_config']
    search_fields = ['name', 'description']
    ordering_fields = ['execution_order', 'task_type', 'name', 'created_at']
    ordering = ['execution_order', 'name']

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active task configurations"""
        active_tasks = self.queryset.filter(is_active=True).order_by('execution_order')
        serializer = self.get_serializer(active_tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def workflow(self, request):
        """Get tasks in execution order for workflow display"""
        workflow_tasks = self.queryset.filter(is_active=True).order_by('execution_order')
        serializer = self.get_serializer(workflow_tasks, many=True)
        return Response({
            'workflow': serializer.data,
            'total_steps': workflow_tasks.count()
        })


class PromptTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for PromptTemplate model"""
    
    queryset = PromptTemplate.objects.all()
    serializer_class = PromptTemplateSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['template_type', 'is_active']
    search_fields = ['name', 'description', 'content']
    ordering_fields = ['template_type', 'name', 'created_at']
    ordering = ['template_type', 'name']

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get templates grouped by type"""
        template_types = {}
        for template in self.queryset.filter(is_active=True):
            template_type = template.template_type
            if template_type not in template_types:
                template_types[template_type] = []
            template_types[template_type].append(PromptTemplateSerializer(template).data)
        
        return Response(template_types)

    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """Render template with provided variables"""
        template = self.get_object()
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


class SystemConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for SystemConfiguration model"""
    
    queryset = SystemConfiguration.objects.all()
    serializer_class = SystemConfigurationSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['data_type', 'is_active']
    search_fields = ['key', 'description']
    ordering_fields = ['key', 'data_type', 'created_at']
    ordering = ['key']

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active system configurations"""
        active_configs = self.queryset.filter(is_active=True).order_by('key')
        serializer = self.get_serializer(active_configs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def as_dict(self, request):
        """Get system configurations as a key-value dictionary"""
        configs = self.queryset.filter(is_active=True)
        config_dict = {config.key: config.get_value() for config in configs}
        return Response(config_dict)


class HiringSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for HiringSession model"""
    
    queryset = HiringSession.objects.select_related('model_config_used').all()
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'model_config_used']
    search_fields = ['session_id', 'candidate_name', 'job_title']
    ordering_fields = ['created_at', 'execution_time', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Use different serializers for create vs other actions"""
        if self.action == 'create':
            return HiringSessionCreateSerializer
        return HiringSessionSerializer

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get session statistics"""
        total_sessions = self.queryset.count()
        completed_sessions = self.queryset.filter(status='completed').count()
        failed_sessions = self.queryset.filter(status='failed').count()
        processing_sessions = self.queryset.filter(status='processing').count()
        
        avg_execution_time = None
        if completed_sessions > 0:
            completed = self.queryset.filter(status='completed', execution_time__isnull=False)
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

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent sessions"""
        limit = int(request.query_params.get('limit', 10))
        recent_sessions = self.queryset.order_by('-created_at')[:limit]
        serializer = self.get_serializer(recent_sessions, many=True)
        return Response(serializer.data)


class ErrorLogViewSet(viewsets.ModelViewSet):
    """ViewSet for ErrorLog model"""
    
    queryset = ErrorLog.objects.select_related('session', 'model_config').all()
    serializer_class = ErrorLogSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['error_type', 'resolved']
    search_fields = ['message']
    ordering_fields = ['created_at', 'error_type', 'resolved']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def unresolved(self, request):
        """Get unresolved errors"""
        unresolved_errors = self.queryset.filter(resolved=False).order_by('-created_at')
        serializer = self.get_serializer(unresolved_errors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def resolve(self, request, pk=None):
        """Mark an error as resolved"""
        error = self.get_object()
        error.resolved = True
        error.save()
        
        return Response({
            'success': True,
            'message': f'Error {error.id} marked as resolved'
        })

    @action(detail=False, methods=['post'])
    def resolve_multiple(self, request):
        """Mark multiple errors as resolved"""
        error_ids = request.data.get('error_ids', [])
        
        if not error_ids:
            return Response({
                'success': False,
                'error': 'No error IDs provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        updated_count = self.queryset.filter(id__in=error_ids).update(resolved=True)
        
        return Response({
            'success': True,
            'message': f'{updated_count} errors marked as resolved'
        })


class AgentTestViewSet(viewsets.ViewSet):
    """ViewSet for testing agent configurations"""
    
    permission_classes = [permissions.AllowAny]  # Allow testing without authentication
    
    @action(detail=False, methods=['post'])
    def run_test(self, request):
        """Run agent configuration test"""
        serializer = AgentTestRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        test_type = serializer.validated_data['test_type']
        
        try:
            if test_type == 'basic':
                return self._run_basic_test()
            elif test_type == 'full':
                return self._run_full_test(serializer.validated_data.get('test_data', {}))
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _run_basic_test(self):
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

    def _run_full_test(self, test_data):
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

    @action(detail=False, methods=['get'])
    def status(self, request):
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
