from django.core.management.base import BaseCommand
from agent.models import (
    ModelConfiguration, AgentConfiguration, TaskConfiguration, 
    PromptTemplate, SystemConfiguration
)


class Command(BaseCommand):
    help = 'Populate database with default agent configurations'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate agent configurations...'))
        
        # Create Model Configurations
        self.create_model_configs()
        
        # Create System Configurations
        self.create_system_configs()
        
        # Create Prompt Templates
        self.create_prompt_templates()
        
        # Create Agent Configurations
        self.create_agent_configs()
        
        # Create Task Configurations
        self.create_task_configs()
        
        self.stdout.write(self.style.SUCCESS('Successfully populated all configurations!'))

    def create_model_configs(self):
        """Create model configurations for Gemma and fallback models"""
        
        # Primary Gemma models
        gemma_models = [
            {
                'name': 'gemma_7b_primary',
                'model_name': 'gemini/gemma-7b',
                'priority': 10,
                'is_fallback': False
            },
            {
                'name': 'gemma_2b_primary',
                'model_name': 'gemini/gemma-2b',
                'priority': 9,
                'is_fallback': False
            },
            {
                'name': 'codegemma_7b',
                'model_name': 'gemini/codegemma-7b',
                'priority': 8,
                'is_fallback': False
            },
            {
                'name': 'gemma_hf_9b',
                'model_name': 'huggingface/google/gemma-2-9b-it',
                'priority': 7,
                'is_fallback': True
            },
            {
                'name': 'gemma_hf_2b',
                'model_name': 'huggingface/google/gemma-2-2b-it',
                'priority': 6,
                'is_fallback': True
            },
            {
                'name': 'gemini_flash_fallback',
                'model_name': 'gemini/gemini-2.0-flash',
                'priority': 5,
                'is_fallback': True
            }
        ]
        
        for config in gemma_models:
            model_config, created = ModelConfiguration.objects.get_or_create(
                name=config['name'],
                defaults={
                    'model_name': config['model_name'],
                    'temperature': 0.3,
                    'max_tokens': 2048,
                    'top_p': 0.9,
                    'timeout': 180,
                    'priority': config['priority'],
                    'is_active': True,
                    'is_fallback': config['is_fallback']
                }
            )
            if created:
                self.stdout.write(f'Created model config: {config["name"]}')
            else:
                self.stdout.write(f'Model config already exists: {config["name"]}')

    def create_system_configs(self):
        """Create system configuration settings"""
        
        system_configs = [
            {
                'key': 'MAX_RETRY_ATTEMPTS',
                'value': '3',
                'data_type': 'integer',
                'description': 'Maximum number of retry attempts for failed model calls'
            },
            {
                'key': 'DEFAULT_TIMEOUT',
                'value': '180',
                'data_type': 'integer',
                'description': 'Default timeout for model operations in seconds'
            },
            {
                'key': 'ENABLE_VERBOSE_LOGGING',
                'value': 'true',
                'data_type': 'boolean',
                'description': 'Enable verbose logging for debugging'
            },
            {
                'key': 'FALLBACK_ENABLED',
                'value': 'true',
                'data_type': 'boolean',
                'description': 'Enable automatic fallback to alternative models'
            },
            {
                'key': 'GEMMA_OPTIMIZATION_LEVEL',
                'value': 'high',
                'data_type': 'string',
                'description': 'Optimization level for Gemma models (low, medium, high)'
            }
        ]
        
        for config in system_configs:
            sys_config, created = SystemConfiguration.objects.get_or_create(
                key=config['key'],
                defaults={
                    'value': config['value'],
                    'data_type': config['data_type'],
                    'description': config['description'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created system config: {config["key"]}')

    def create_prompt_templates(self):
        """Create reusable prompt templates"""
        
        templates = [
            {
                'name': 'job_matching_instruction',
                'template_type': 'instruction',
                'content': '''INSTRUCTIONS: Analyze the candidate and make a hiring decision.

ANALYZE:
- Resume: Skills, experience, education
- Job Requirements: Match qualifications to role needs
- Interview: Communication and fit assessment

PROVIDE:
1. Decision: SELECT or REJECT
2. Key reasons (3-4 bullet points)
3. Supporting evidence from candidate data

Keep response under {token_limit} tokens.''',
                'variables': ['token_limit'],
                'description': 'Main instruction template for job matching tasks'
            },
            {
                'name': 'bias_audit_instruction',
                'template_type': 'review',
                'content': '''INSTRUCTIONS: Review the hiring decision for fairness.

CHECK:
- Decision based on job qualifications? (Yes/No)
- Any bias indicators found? (List them)
- Decision aligns with merit criteria? (Yes/No)

PROVIDE:
1. Final decision: SELECT or REJECT
2. Fairness assessment: FAIR or BIASED
3. Brief justification

Keep response under {token_limit} tokens.''',
                'variables': ['token_limit'],
                'description': 'Bias audit instruction template'
            },
            {
                'name': 'job_matching_output',
                'template_type': 'system',
                'content': '''DECISION: [SELECT or REJECT]

REASONS:
- Point 1
- Point 2
- Point 3

EVIDENCE: Specific examples from resume/interview supporting the decision.''',
                'variables': [],
                'description': 'Expected output format for job matching decisions'
            },
            {
                'name': 'bias_audit_output',
                'template_type': 'system',
                'content': '''FINAL DECISION: [SELECT or REJECT]
FAIRNESS: [FAIR or BIASED]
JUSTIFICATION: Brief explanation of decision validity and any bias concerns.''',
                'variables': [],
                'description': 'Expected output format for bias audit results'
            }
        ]
        
        for template in templates:
            prompt_template, created = PromptTemplate.objects.get_or_create(
                name=template['name'],
                defaults={
                    'template_type': template['template_type'],
                    'content': template['content'],
                    'variables': template['variables'],
                    'description': template['description'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created prompt template: {template["name"]}')

    def create_agent_configs(self):
        """Create agent configurations"""
        
        # Get primary model configuration
        primary_model = ModelConfiguration.objects.filter(
            is_active=True, 
            is_fallback=False
        ).order_by('-priority').first()
        
        if not primary_model:
            primary_model = ModelConfiguration.objects.filter(is_active=True).first()
            
        if not primary_model:
            self.stdout.write(self.style.ERROR('No active model configuration found'))
            return
        
        agents = [
            {
                'agent_type': 'job_matcher',
                'role': 'Hiring Decision Maker',
                'goal': 'Make hiring decisions: SELECT or REJECT candidates based on job fit',
                'backstory': '''You are an experienced hiring manager. You analyze resumes and job requirements to make clear hiring decisions. You provide direct reasoning for each decision.''',
                'max_execution_time': 300,
                'allow_delegation': False,
                'verbose': True
            },
            {
                'agent_type': 'bias_auditor',
                'role': 'Decision Reviewer',
                'goal': 'Review hiring decisions for fairness and provide final SELECT or REJECT decision',
                'backstory': '''You are a fair hiring expert. You check decisions for bias and ensure they are based on job qualifications. You validate final hiring recommendations.''',
                'max_execution_time': 300,
                'allow_delegation': False,
                'verbose': True
            }
        ]
        
        for agent in agents:
            agent_config, created = AgentConfiguration.objects.get_or_create(
                agent_type=agent['agent_type'],
                defaults={
                    'role': agent['role'],
                    'goal': agent['goal'],
                    'backstory': agent['backstory'],
                    'max_execution_time': agent['max_execution_time'],
                    'allow_delegation': agent['allow_delegation'],
                    'verbose': agent['verbose'],
                    'is_active': True,
                    'model_config': primary_model
                }
            )
            if created:
                self.stdout.write(f'Created agent config: {agent["agent_type"]}')

    def create_task_configs(self):
        """Create task configurations"""
        
        # Get agent configurations
        job_matcher = AgentConfiguration.objects.filter(agent_type='job_matcher').first()
        bias_auditor = AgentConfiguration.objects.filter(agent_type='bias_auditor').first()
        
        # Get prompt templates
        job_instruction = PromptTemplate.objects.filter(name='job_matching_instruction').first()
        bias_instruction = PromptTemplate.objects.filter(name='bias_audit_instruction').first()
        job_output = PromptTemplate.objects.filter(name='job_matching_output').first()
        bias_output = PromptTemplate.objects.filter(name='bias_audit_output').first()
        
        tasks = [
            {
                'task_type': 'job_matching',
                'name': 'Job Matching Decision',
                'description': job_instruction.content if job_instruction else 'Job matching task description',
                'expected_output': job_output.content if job_output else 'Decision with reasoning',
                'token_limit': 1500,
                'agent_config': job_matcher,
                'execution_order': 1
            },
            {
                'task_type': 'bias_audit',
                'name': 'Bias Audit Review',
                'description': bias_instruction.content if bias_instruction else 'Bias audit task description',
                'expected_output': bias_output.content if bias_output else 'Fairness assessment',
                'token_limit': 1000,
                'agent_config': bias_auditor,
                'execution_order': 2
            }
        ]
        
        for task in tasks:
            if task['agent_config']:  # Only create if agent exists
                task_config, created = TaskConfiguration.objects.get_or_create(
                    task_type=task['task_type'],
                    defaults={
                        'name': task['name'],
                        'description': task['description'],
                        'expected_output': task['expected_output'],
                        'token_limit': task['token_limit'],
                        'agent_config': task['agent_config'],
                        'execution_order': task['execution_order'],
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f'Created task config: {task["task_type"]}')
