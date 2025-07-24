from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class ModelConfiguration(models.Model):
    """Configuration settings for AI models"""
    name = models.CharField(max_length=100, unique=True, help_text="Configuration name (e.g., 'gemma_primary')")
    model_name = models.CharField(max_length=200, help_text="Full model identifier (e.g., 'gemini/gemma-7b')")
    temperature = models.FloatField(
        default=0.3, 
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        help_text="Temperature for response randomness (0.0-2.0)"
    )
    max_tokens = models.IntegerField(
        default=2048,
        validators=[MinValueValidator(1), MaxValueValidator(8192)],
        help_text="Maximum tokens for model response"
    )
    top_p = models.FloatField(
        default=0.9,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Top-p sampling parameter (0.0-1.0)"
    )
    timeout = models.IntegerField(
        default=180,
        validators=[MinValueValidator(30), MaxValueValidator(600)],
        help_text="Timeout in seconds"
    )
    priority = models.IntegerField(
        default=1,
        help_text="Priority for fallback selection (higher = try first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this configuration is active"
    )
    is_fallback = models.BooleanField(
        default=False,
        help_text="Whether this is a fallback configuration"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'name']

    def __str__(self):
        return f"{self.name} ({self.model_name})"


class AgentConfiguration(models.Model):
    """Configuration for CrewAI agents"""
    AGENT_TYPES = [
        ('job_matcher', 'Job Matching Agent'),
        ('bias_auditor', 'Bias Auditing Agent'),
        ('custom', 'Custom Agent'),
    ]
    
    agent_type = models.CharField(max_length=50, choices=AGENT_TYPES, unique=True)
    role = models.CharField(max_length=200, help_text="Agent role/title")
    goal = models.TextField(help_text="Agent's primary goal")
    backstory = models.TextField(help_text="Agent's background and expertise")
    max_execution_time = models.IntegerField(
        default=300,
        validators=[MinValueValidator(60), MaxValueValidator(600)],
        help_text="Maximum execution time in seconds"
    )
    allow_delegation = models.BooleanField(
        default=False,
        help_text="Whether agent can delegate tasks"
    )
    verbose = models.BooleanField(
        default=True,
        help_text="Whether to enable verbose logging"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this agent configuration is active"
    )
    model_config = models.ForeignKey(
        ModelConfiguration,
        on_delete=models.CASCADE,
        help_text="Model configuration to use for this agent"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_agent_type_display()} - {self.role}"


class TaskConfiguration(models.Model):
    """Configuration for CrewAI tasks"""
    TASK_TYPES = [
        ('job_matching', 'Job Matching Task'),
        ('bias_audit', 'Bias Audit Task'),
        ('custom', 'Custom Task'),
    ]
    
    task_type = models.CharField(max_length=50, choices=TASK_TYPES, unique=True)
    name = models.CharField(max_length=200, help_text="Task name")
    description = models.TextField(help_text="Task description/instructions")
    expected_output = models.TextField(help_text="Expected output format")
    token_limit = models.IntegerField(
        default=1500,
        validators=[MinValueValidator(100), MaxValueValidator(4000)],
        help_text="Recommended token limit for this task"
    )
    agent_config = models.ForeignKey(
        AgentConfiguration,
        on_delete=models.CASCADE,
        help_text="Agent configuration to assign this task to"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this task configuration is active"
    )
    execution_order = models.IntegerField(
        default=1,
        help_text="Order of task execution (lower numbers execute first)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['execution_order', 'name']

    def __str__(self):
        return f"{self.get_task_type_display()} - {self.name}"


class PromptTemplate(models.Model):
    """Reusable prompt templates"""
    TEMPLATE_TYPES = [
        ('instruction', 'Task Instruction'),
        ('analysis', 'Analysis Prompt'),
        ('decision', 'Decision Making'),
        ('review', 'Review Process'),
        ('system', 'System Message'),
    ]
    
    name = models.CharField(max_length=200, unique=True, help_text="Template name")
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    content = models.TextField(help_text="Prompt template content")
    variables = models.JSONField(
        default=list,
        help_text="List of variable names that can be substituted in this template"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of when to use this template"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

    def render(self, **kwargs):
        """Render template with provided variables"""
        content = self.content
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            content = content.replace(placeholder, str(value))
        return content


class SystemConfiguration(models.Model):
    """Global system configuration settings"""
    key = models.CharField(max_length=100, unique=True, help_text="Configuration key")
    value = models.TextField(help_text="Configuration value")
    data_type = models.CharField(
        max_length=20,
        choices=[
            ('string', 'String'),
            ('integer', 'Integer'),
            ('float', 'Float'),
            ('boolean', 'Boolean'),
            ('json', 'JSON'),
        ],
        default='string'
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this configuration setting"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key} = {self.value}"

    def get_value(self):
        """Get the typed value based on data_type"""
        if self.data_type == 'integer':
            return int(self.value)
        elif self.data_type == 'float':
            return float(self.value)
        elif self.data_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'json':
            return json.loads(self.value)
        return self.value


class HiringSession(models.Model):
    """Track hiring evaluation sessions"""
    session_id = models.CharField(max_length=100, unique=True)
    candidate_name = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    input_data = models.JSONField(
        default=dict,
        help_text="Input data for the hiring evaluation"
    )
    results = models.JSONField(
        default=dict,
        help_text="Results from the hiring evaluation"
    )
    model_config_used = models.ForeignKey(
        ModelConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Model configuration used for this session"
    )
    execution_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Total execution time in seconds"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.session_id} - {self.status}"


class ErrorLog(models.Model):
    """Log errors and issues for debugging"""
    ERROR_TYPES = [
        ('model_error', 'Model Error'),
        ('api_error', 'API Error'),
        ('configuration_error', 'Configuration Error'),
        ('task_error', 'Task Execution Error'),
        ('validation_error', 'Validation Error'),
    ]
    
    error_type = models.CharField(max_length=50, choices=ERROR_TYPES)
    message = models.TextField(help_text="Error message")
    details = models.JSONField(
        default=dict,
        help_text="Additional error details and context"
    )
    session = models.ForeignKey(
        HiringSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Related hiring session if applicable"
    )
    model_config = models.ForeignKey(
        ModelConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Model configuration when error occurred"
    )
    resolved = models.BooleanField(
        default=False,
        help_text="Whether this error has been resolved"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_error_type_display()}: {self.message[:100]}"
