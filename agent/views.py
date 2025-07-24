from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import (
    ModelConfiguration, AgentConfiguration, TaskConfiguration,
    PromptTemplate, SystemConfiguration, HiringSession, ErrorLog
)
from .agents_db import get_manager
import json


def configuration_dashboard(request):
    """Display current agent configuration dashboard"""
    
    context = {
        'model_configs': ModelConfiguration.objects.filter(is_active=True).order_by('-priority'),
        'agent_configs': AgentConfiguration.objects.filter(is_active=True),
        'task_configs': TaskConfiguration.objects.filter(is_active=True).order_by('execution_order'),
        'system_configs': SystemConfiguration.objects.filter(is_active=True).order_by('key'),
        'prompt_templates': PromptTemplate.objects.filter(is_active=True).order_by('template_type', 'name'),
        'recent_sessions': HiringSession.objects.all().order_by('-created_at')[:10],
        'recent_errors': ErrorLog.objects.filter(resolved=False).order_by('-created_at')[:5],
    }
    
    return render(request, 'agent/configuration_dashboard.html', context)


def api_configuration_status(request):
    """API endpoint to get current configuration status"""
    
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
        
        status = {
            'status': 'operational',
            'current_model': {
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
        }
        
        return JsonResponse(status)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'manager_initialized': False,
            'model_available': False,
        }, status=500)


@csrf_exempt
def agent_test_api(request):
    """API endpoint to test agent configuration"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Get test parameters
        test_type = data.get('test_type', 'basic')
        
        if test_type == 'basic':
            return run_basic_test()
        elif test_type == 'full':
            return run_full_test(data)
        else:
            return JsonResponse({'error': 'Invalid test type'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def run_basic_test():
    """Run basic configuration test"""
    try:
        manager = get_manager()
        
        # Test system configs
        fallback_enabled = manager.get_system_config('FALLBACK_ENABLED', False)
        max_retries = manager.get_system_config('MAX_RETRY_ATTEMPTS', 3)
        
        # Test prompt templates
        job_prompt = manager.get_prompt_template('job_matching_instruction', token_limit=1500)
        bias_prompt = manager.get_prompt_template('bias_audit_instruction', token_limit=1000)
        
        return JsonResponse({
            'success': True,
            'test_type': 'basic',
            'results': {
                'manager_initialized': True,
                'model_available': manager.current_model_config is not None,
                'system_configs_accessible': fallback_enabled is not None,
                'prompt_templates_accessible': bool(job_prompt and bias_prompt),
                'current_model': manager.current_model_config.name if manager.current_model_config else None,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def run_full_test(data):
    """Run full agent test with sample data"""
    try:
        from .agents_db import load_agents, create_tasks
        import uuid
        import time
        
        manager = get_manager()
        
        # Load agents and tasks
        job_matcher, bias_auditor = load_agents()
        job_task, bias_task = create_tasks(job_matcher, bias_auditor)
        
        # Create test session
        session_id = f"api_test_{uuid.uuid4().hex[:8]}"
        test_input = data.get('test_data', {
            'candidate_name': 'Test Candidate',
            'job_title': 'Test Position',
            'resume': 'Sample resume content...',
            'interview_notes': 'Sample interview notes...'
        })
        
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
        
        return JsonResponse({
            'success': True,
            'test_type': 'full',
            'session_id': session_id,
            'execution_time': execution_time,
            'results': test_results
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def update_model_config_api(request):
    """API endpoint to update model configuration"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        config_id = data.get('config_id')
        
        if not config_id:
            return JsonResponse({'error': 'config_id is required'}, status=400)
        
        try:
            config = ModelConfiguration.objects.get(id=config_id, is_active=True)
        except ModelConfiguration.DoesNotExist:
            return JsonResponse({'error': 'Model configuration not found'}, status=404)
        
        # Update allowed fields
        if 'temperature' in data:
            config.temperature = float(data['temperature'])
        if 'max_tokens' in data:
            config.max_tokens = int(data['max_tokens'])
        if 'top_p' in data:
            config.top_p = float(data['top_p'])
        if 'timeout' in data:
            config.timeout = int(data['timeout'])
        if 'priority' in data:
            config.priority = int(data['priority'])
        
        config.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Model configuration {config.name} updated successfully',
            'config': {
                'id': config.id,
                'name': config.name,
                'model_name': config.model_name,
                'temperature': config.temperature,
                'max_tokens': config.max_tokens,
                'top_p': config.top_p,
                'timeout': config.timeout,
                'priority': config.priority,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def update_prompt_template_api(request):
    """API endpoint to update prompt template"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        template_id = data.get('template_id')
        
        if not template_id:
            return JsonResponse({'error': 'template_id is required'}, status=400)
        
        try:
            template = PromptTemplate.objects.get(id=template_id, is_active=True)
        except PromptTemplate.DoesNotExist:
            return JsonResponse({'error': 'Prompt template not found'}, status=404)
        
        # Update allowed fields
        if 'content' in data:
            template.content = data['content']
        if 'description' in data:
            template.description = data['description']
        if 'variables' in data:
            template.variables = data['variables']
        
        template.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Prompt template {template.name} updated successfully',
            'template': {
                'id': template.id,
                'name': template.name,
                'template_type': template.template_type,
                'content': template.content,
                'variables': template.variables,
                'description': template.description,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_active_configurations_api(request):
    """API endpoint to get all active configurations"""
    try:
        data = {
            'model_configs': list(ModelConfiguration.objects.filter(is_active=True).values(
                'id', 'name', 'model_name', 'temperature', 'max_tokens', 'top_p', 'timeout', 'priority', 'is_fallback'
            )),
            'agent_configs': list(AgentConfiguration.objects.filter(is_active=True).values(
                'id', 'agent_type', 'role', 'goal', 'backstory', 'max_execution_time', 'allow_delegation', 'verbose'
            )),
            'task_configs': list(TaskConfiguration.objects.filter(is_active=True).values(
                'id', 'task_type', 'name', 'description', 'expected_output', 'token_limit', 'execution_order'
            )),
            'prompt_templates': list(PromptTemplate.objects.filter(is_active=True).values(
                'id', 'name', 'template_type', 'content', 'variables', 'description'
            )),
            'system_configs': list(SystemConfiguration.objects.filter(is_active=True).values(
                'id', 'key', 'value', 'data_type', 'description'
            )),
        }
        
        return JsonResponse({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_session_history_api(request):
    """API endpoint to get session history with optional filtering"""
    try:
        # Get query parameters
        limit = int(request.GET.get('limit', 20))
        status_filter = request.GET.get('status', None)
        
        # Build query
        query = HiringSession.objects.all()
        if status_filter:
            query = query.filter(status=status_filter)
        
        sessions = query.order_by('-created_at')[:limit]
        
        session_data = []
        for session in sessions:
            session_data.append({
                'id': session.id,
                'session_id': session.session_id,
                'candidate_name': session.candidate_name,
                'job_title': session.job_title,
                'status': session.status,
                'execution_time': session.execution_time,
                'model_used': session.model_config_used.name if session.model_config_used else None,
                'created_at': session.created_at.isoformat(),
                'input_data': session.input_data,
                'results': session.results,
            })
        
        return JsonResponse({
            'success': True,
            'sessions': session_data,
            'total_count': HiringSession.objects.count()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_error_logs_api(request):
    """API endpoint to get error logs with optional filtering"""
    try:
        # Get query parameters
        limit = int(request.GET.get('limit', 10))
        resolved = request.GET.get('resolved', 'false').lower() == 'true'
        error_type = request.GET.get('error_type', None)
        
        # Build query
        query = ErrorLog.objects.filter(resolved=resolved)
        if error_type:
            query = query.filter(error_type=error_type)
        
        errors = query.order_by('-created_at')[:limit]
        
        error_data = []
        for error in errors:
            error_data.append({
                'id': error.id,
                'error_type': error.error_type,
                'message': error.message,
                'session_id': error.session.session_id if error.session else None,
                'model_config': error.model_config.name if error.model_config else None,
                'resolved': error.resolved,
                'created_at': error.created_at.isoformat(),
                'details': error.details,
            })
        
        return JsonResponse({
            'success': True,
            'errors': error_data,
            'total_unresolved': ErrorLog.objects.filter(resolved=False).count()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
