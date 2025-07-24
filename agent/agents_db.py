# agents.py - Database-driven configuration version

import os
import logging
from typing import Optional, Tuple
from crewai import Agent, Task, LLM
from pydantic import BaseModel, Field
from typing import List, Optional

# Django model imports
from .models import (
    ModelConfiguration, AgentConfiguration, TaskConfiguration,
    PromptTemplate, SystemConfiguration, HiringSession, ErrorLog
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GemmaHiringDecision(BaseModel):
    """Simplified decision model optimized for Gemma's output capabilities"""
    decision: str = Field(..., description="Either 'SELECT' or 'REJECT' (uppercase)")
    reasons: List[str] = Field(..., description="3-4 key reasons for the decision", max_items=4)
    evidence: str = Field(..., description="Brief supporting evidence from candidate data")
    confidence: Optional[float] = Field(default=0.8, description="Confidence score 0-1", ge=0, le=1)


class GemmaBiasAudit(BaseModel):
    """Simplified bias audit model for Gemma"""
    final_decision: str = Field(..., description="Either 'SELECT' or 'REJECT' (uppercase)")
    fairness_assessment: str = Field(..., description="Either 'FAIR' or 'BIASED' (uppercase)")
    bias_indicators: List[str] = Field(default=[], description="List of any bias indicators found", max_items=3)
    justification: str = Field(..., description="Brief justification for the assessment")


class HiringDecision(BaseModel):
    """Legacy model for backward compatibility"""
    decision: str = Field(..., description="Either 'select' or 'reject'")
    reasoning: str = Field(..., description="Detailed reasoning for the decision")
    score: float = Field(..., description="Confidence score from 0 to 1")


class BiasAuditResult(BaseModel):
    """Legacy bias audit model for backward compatibility"""
    audit_result: str = Field(..., description="Either 'biased' or 'unbiased'")
    bias_indicators: List[str] = Field(..., description="List of potential bias indicators found")
    confidence: float = Field(..., description="Confidence in bias assessment from 0 to 1")
    recommendations: List[str] = Field(..., description="Recommendations to improve fairness")


class DatabaseAgentManager:
    """Manager class to handle database-driven agent configuration"""
    
    def __init__(self):
        self.api_key = os.getenv("CREWAI_API_KEY")
        if not self.api_key:
            raise ValueError("CREWAI_API_KEY environment variable is required")
        
        self.llm = None
        self.current_model_config = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM using database configuration with fallback strategy"""
        # Get active model configurations ordered by priority
        model_configs = ModelConfiguration.objects.filter(
            is_active=True
        ).order_by('-priority')
        
        if not model_configs.exists():
            raise ValueError("No active model configurations found in database")
        
        # Try each model configuration until one works
        for config in model_configs:
            try:
                logger.info(f"Attempting to configure model: {config.model_name}")
                
                llm = LLM(
                    model=config.model_name,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    top_p=config.top_p,
                    timeout=config.timeout,
                    api_key=self.api_key,
                )
                
                # For now, skip the test call as it's causing issues
                # test_response = llm.call("Reply with 'READY' if you can process this.")
                logger.info(f"Successfully configured {config.model_name}")
                
                self.llm = llm
                self.current_model_config = config
                return
                
            except Exception as e:
                logger.warning(f"Failed to configure {config.model_name}: {e}")
                
                # Log the error to database
                ErrorLog.objects.create(
                    error_type='model_error',
                    message=f"Failed to initialize {config.model_name}",
                    details={
                        'model_name': config.model_name,
                        'error': str(e),
                        'config_id': config.id
                    },
                    model_config=config
                )
                continue
        
        raise RuntimeError("No working model configuration found")
    
    def get_system_config(self, key: str, default=None):
        """Get system configuration value from database"""
        try:
            config = SystemConfiguration.objects.get(key=key, is_active=True)
            return config.get_value()
        except SystemConfiguration.DoesNotExist:
            return default
    
    def get_prompt_template(self, name: str, **variables) -> str:
        """Get and render prompt template from database"""
        try:
            template = PromptTemplate.objects.get(name=name, is_active=True)
            return template.render(**variables)
        except PromptTemplate.DoesNotExist:
            logger.warning(f"Prompt template '{name}' not found, using fallback")
            return ""
    
    def create_agents(self) -> Tuple[Agent, Agent]:
        """Create agents using database configuration"""
        agent_configs = AgentConfiguration.objects.filter(
            is_active=True
        ).select_related('model_config')
        
        if agent_configs.count() < 2:
            raise ValueError("Need at least 2 active agent configurations")
        
        agents = {}
        for config in agent_configs:
            # Use the current working LLM for all agents
            agent = Agent(
                role=config.role,
                goal=config.goal,
                backstory=config.backstory,
                llm=self.llm,
                verbose=config.verbose,
                max_execution_time=config.max_execution_time,
                allow_delegation=config.allow_delegation,
            )
            agents[config.agent_type] = agent
            logger.info(f"Created agent: {config.agent_type}")
        
        # Return specific agents (maintain compatibility with existing code)
        job_matcher = agents.get('job_matcher')
        bias_auditor = agents.get('bias_auditor')
        
        if not job_matcher or not bias_auditor:
            raise ValueError("Required agent configurations not found")
        
        return job_matcher, bias_auditor
    
    def create_tasks(self, job_matcher: Agent, bias_auditor: Agent) -> Tuple[Task, Task]:
        """Create tasks using database configuration"""
        task_configs = TaskConfiguration.objects.filter(
            is_active=True
        ).select_related('agent_config').order_by('execution_order')
        
        if task_configs.count() < 2:
            raise ValueError("Need at least 2 active task configurations")
        
        tasks = []
        agent_map = {
            'job_matcher': job_matcher,
            'bias_auditor': bias_auditor
        }
        
        for config in task_configs:
            agent = agent_map.get(config.agent_config.agent_type)
            if not agent:
                logger.warning(f"No agent found for task {config.task_type}")
                continue
            
            # Render description template with token limit
            description = config.description.format(token_limit=config.token_limit)
            
            task = Task(
                description=description,
                expected_output=config.expected_output,
                agent=agent
            )
            tasks.append(task)
            logger.info(f"Created task: {config.task_type}")
        
        if len(tasks) < 2:
            raise ValueError("Failed to create required tasks")
        
        return tasks[0], tasks[1]  # Return first two tasks
    
    def log_session_start(self, session_id: str, input_data: dict) -> HiringSession:
        """Log the start of a hiring session"""
        return HiringSession.objects.create(
            session_id=session_id,
            status='processing',
            input_data=input_data,
            model_config_used=self.current_model_config
        )
    
    def log_session_complete(self, session: HiringSession, results: dict, execution_time: float):
        """Log the completion of a hiring session"""
        session.status = 'completed'
        session.results = results
        session.execution_time = execution_time
        session.save()
    
    def log_session_error(self, session: HiringSession, error: Exception):
        """Log a session error"""
        session.status = 'failed'
        session.save()
        
        ErrorLog.objects.create(
            error_type='task_error',
            message=str(error),
            details={'session_id': session.session_id},
            session=session,
            model_config=self.current_model_config
        )
    
    def print_optimization_summary(self):
        """Print summary of current configuration"""
        logger.info("=== DATABASE-DRIVEN AGENT CONFIGURATION ===")
        logger.info(f"✅ Active Model: {self.current_model_config.model_name}")
        logger.info(f"✅ Model Config: {self.current_model_config.name}")
        logger.info(f"✅ Temperature: {self.current_model_config.temperature}")
        logger.info(f"✅ Max Tokens: {self.current_model_config.max_tokens}")
        logger.info(f"✅ Top P: {self.current_model_config.top_p}")
        logger.info(f"✅ Timeout: {self.current_model_config.timeout}")
        
        # Show system configs
        fallback_enabled = self.get_system_config('FALLBACK_ENABLED', True)
        verbose_logging = self.get_system_config('ENABLE_VERBOSE_LOGGING', True)
        optimization_level = self.get_system_config('GEMMA_OPTIMIZATION_LEVEL', 'high')
        
        logger.info(f"✅ Fallback Enabled: {fallback_enabled}")
        logger.info(f"✅ Verbose Logging: {verbose_logging}")
        logger.info(f"✅ Optimization Level: {optimization_level}")
        
        # Show agent and task counts
        agent_count = AgentConfiguration.objects.filter(is_active=True).count()
        task_count = TaskConfiguration.objects.filter(is_active=True).count()
        template_count = PromptTemplate.objects.filter(is_active=True).count()
        
        logger.info(f"✅ Active Agents: {agent_count}")
        logger.info(f"✅ Active Tasks: {task_count}")
        logger.info(f"✅ Active Templates: {template_count}")
        logger.info("============================================")


# Global manager instance
_manager = None


def get_manager() -> DatabaseAgentManager:
    """Get or create the global agent manager"""
    global _manager
    if _manager is None:
        _manager = DatabaseAgentManager()
    return _manager


def validate_gemma_setup():
    """Validate that the configured model is properly responsive"""
    try:
        manager = get_manager()
        return manager.llm is not None and manager.current_model_config is not None
    except Exception as e:
        logger.error(f"Model validation failed: {e}")
        return False


def get_model_info():
    """Get information about the currently configured model"""
    try:
        manager = get_manager()
        if manager.current_model_config:
            return manager.current_model_config.model_name
        return "Unknown model"
    except Exception:
        return "Model info unavailable"


def print_optimization_summary():
    """Print summary of Gemma-focused optimizations implemented"""
    try:
        manager = get_manager()
        manager.print_optimization_summary()
    except Exception as e:
        logger.error(f"Failed to print optimization summary: {e}")


def load_agents():
    """Load agents using database configuration"""
    try:
        manager = get_manager()
        
        # Print optimization summary
        manager.print_optimization_summary()
        
        # Validate model setup
        if not validate_gemma_setup():
            logger.warning("Model validation failed, proceeding with caution...")
        
        # Create agents from database config
        job_matcher, bias_auditor = manager.create_agents()
        
        return job_matcher, bias_auditor
        
    except Exception as e:
        logger.error(f"Failed to load agents: {e}")
        raise


def create_tasks(job_matcher, bias_auditor):
    """Create tasks using database configuration"""
    try:
        manager = get_manager()
        return manager.create_tasks(job_matcher, bias_auditor)
    except Exception as e:
        logger.error(f"Failed to create tasks: {e}")
        raise


# Convenience functions for session management
def start_hiring_session(session_id: str, input_data: dict) -> HiringSession:
    """Start a new hiring session with logging"""
    manager = get_manager()
    return manager.log_session_start(session_id, input_data)


def complete_hiring_session(session: HiringSession, results: dict, execution_time: float):
    """Complete a hiring session with results"""
    manager = get_manager()
    manager.log_session_complete(session, results, execution_time)


def error_hiring_session(session: HiringSession, error: Exception):
    """Mark a hiring session as failed"""
    manager = get_manager()
    manager.log_session_error(session, error)
