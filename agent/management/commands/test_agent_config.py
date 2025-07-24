from django.core.management.base import BaseCommand
from agent.agents_db import get_manager, load_agents, create_tasks
import time
import uuid


class Command(BaseCommand):
    help = 'Test the database-driven agent configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full-test',
            action='store_true',
            help='Run a full hiring evaluation test',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing database-driven agent configuration...'))
        
        try:
            # Test manager initialization
            manager = get_manager()
            self.stdout.write(self.style.SUCCESS('✅ Manager initialized successfully'))
            
            # Test agent loading
            job_matcher, bias_auditor = load_agents()
            self.stdout.write(self.style.SUCCESS('✅ Agents loaded successfully'))
            
            # Test task creation
            job_task, bias_task = create_tasks(job_matcher, bias_auditor)
            self.stdout.write(self.style.SUCCESS('✅ Tasks created successfully'))
            
            # Test system configuration access
            fallback_enabled = manager.get_system_config('FALLBACK_ENABLED', False)
            max_retries = manager.get_system_config('MAX_RETRY_ATTEMPTS', 3)
            self.stdout.write(self.style.SUCCESS(f'✅ System configs accessed: fallback={fallback_enabled}, retries={max_retries}'))
            
            # Test prompt template access
            job_prompt = manager.get_prompt_template('job_matching_instruction', token_limit=1500)
            bias_prompt = manager.get_prompt_template('bias_audit_instruction', token_limit=1000)
            
            if job_prompt and bias_prompt:
                self.stdout.write(self.style.SUCCESS('✅ Prompt templates accessed successfully'))
            else:
                self.stdout.write(self.style.WARNING('⚠️ Some prompt templates not found'))
            
            if options['full_test']:
                self.stdout.write(self.style.WARNING('Running full hiring evaluation test...'))
                self.run_full_test(manager, job_matcher, bias_auditor, job_task, bias_task)
            
            self.stdout.write(self.style.SUCCESS('🎉 All tests passed! Database-driven configuration is working.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Test failed: {e}'))
            raise

    def run_full_test(self, manager, job_matcher, bias_auditor, job_task, bias_task):
        """Run a full hiring evaluation test"""
        
        # Create a test session
        session_id = f"test_{uuid.uuid4().hex[:8]}"
        test_input = {
            'candidate_name': 'John Doe',
            'job_title': 'Software Engineer',
            'resume': 'Experienced Python developer with 5 years of experience...',
            'interview_notes': 'Strong technical skills, good communication...'
        }
        
        start_time = time.time()
        
        try:
            # Start session logging
            session = manager.log_session_start(session_id, test_input)
            self.stdout.write(f'📝 Started test session: {session_id}')
            
            # Simulate task execution
            self.stdout.write('🔄 Simulating job matching task...')
            time.sleep(2)  # Simulate processing time
            
            self.stdout.write('🔄 Simulating bias audit task...')
            time.sleep(1)  # Simulate processing time
            
            # Log successful completion
            execution_time = time.time() - start_time
            test_results = {
                'job_matching_decision': 'SELECT',
                'bias_audit_result': 'FAIR',
                'confidence': 0.85
            }
            
            manager.log_session_complete(session, test_results, execution_time)
            self.stdout.write(self.style.SUCCESS(f'✅ Test session completed in {execution_time:.2f}s'))
            
        except Exception as e:
            # Log error
            session = manager.log_session_start(session_id, test_input)
            manager.log_session_error(session, e)
            self.stdout.write(self.style.ERROR(f'❌ Test session failed: {e}'))
            raise
