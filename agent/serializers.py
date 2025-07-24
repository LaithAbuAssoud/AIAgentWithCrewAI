from rest_framework import serializers
from .models import (
    ModelConfiguration, AgentConfiguration, TaskConfiguration,
    PromptTemplate, SystemConfiguration, HiringSession, ErrorLog
)


class ModelConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for ModelConfiguration model"""
    
    class Meta:
        model = ModelConfiguration
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate_temperature(self, value):
        """Validate temperature is within valid range"""
        if not 0.0 <= value <= 2.0:
            raise serializers.ValidationError("Temperature must be between 0.0 and 2.0")
        return value

    def validate_max_tokens(self, value):
        """Validate max_tokens is positive"""
        if value <= 0:
            raise serializers.ValidationError("Max tokens must be positive")
        return value

    def validate_top_p(self, value):
        """Validate top_p is within valid range"""
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError("Top-p must be between 0.0 and 1.0")
        return value


class AgentConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for AgentConfiguration model"""
    
    model_config_name = serializers.CharField(source='model_config.name', read_only=True)
    agent_type_display = serializers.CharField(source='get_agent_type_display', read_only=True)
    
    class Meta:
        model = AgentConfiguration
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate_max_execution_time(self, value):
        """Validate execution time is reasonable"""
        if not 60 <= value <= 600:
            raise serializers.ValidationError("Execution time must be between 60 and 600 seconds")
        return value


class TaskConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for TaskConfiguration model"""
    
    agent_config_name = serializers.CharField(source='agent_config.role', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    
    class Meta:
        model = TaskConfiguration
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate_token_limit(self, value):
        """Validate token limit is reasonable"""
        if not 100 <= value <= 4000:
            raise serializers.ValidationError("Token limit must be between 100 and 4000")
        return value


class PromptTemplateSerializer(serializers.ModelSerializer):
    """Serializer for PromptTemplate model"""
    
    template_type_display = serializers.CharField(source='get_template_type_display', read_only=True)
    variable_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PromptTemplate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_variable_count(self, obj):
        """Get the number of variables in the template"""
        return len(obj.variables) if obj.variables else 0

    def validate_content(self, value):
        """Validate template content is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Template content cannot be empty")
        return value


class SystemConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for SystemConfiguration model"""
    
    typed_value = serializers.SerializerMethodField()
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)
    
    class Meta:
        model = SystemConfiguration
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_typed_value(self, obj):
        """Get the properly typed value"""
        return obj.get_value()

    def validate(self, data):
        """Validate that value matches data_type"""
        value = data.get('value')
        data_type = data.get('data_type')
        
        if value is not None and data_type:
            try:
                if data_type == 'integer':
                    int(value)
                elif data_type == 'float':
                    float(value)
                elif data_type == 'boolean':
                    if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                        raise ValueError("Invalid boolean value")
                elif data_type == 'json':
                    import json
                    json.loads(value)
            except (ValueError, TypeError) as e:
                raise serializers.ValidationError(f"Value '{value}' is not valid for data type '{data_type}'")
        
        return data


class HiringSessionSerializer(serializers.ModelSerializer):
    """Serializer for HiringSession model"""
    
    model_config_name = serializers.CharField(source='model_config_used.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = HiringSession
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'execution_time')

    def get_duration_formatted(self, obj):
        """Get formatted execution time"""
        if obj.execution_time:
            return f"{obj.execution_time:.2f}s"
        return None


class HiringSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new hiring sessions"""
    
    class Meta:
        model = HiringSession
        fields = ('session_id', 'candidate_name', 'job_title', 'input_data')

    def validate_session_id(self, value):
        """Ensure session_id is unique"""
        if HiringSession.objects.filter(session_id=value).exists():
            raise serializers.ValidationError("Session ID already exists")
        return value


class ErrorLogSerializer(serializers.ModelSerializer):
    """Serializer for ErrorLog model"""
    
    session_id = serializers.CharField(source='session.session_id', read_only=True)
    model_config_name = serializers.CharField(source='model_config.name', read_only=True)
    error_type_display = serializers.CharField(source='get_error_type_display', read_only=True)
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = ErrorLog
        fields = '__all__'
        read_only_fields = ('created_at',)

    def get_time_since(self, obj):
        """Get human-readable time since error occurred"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return "Just now"
        elif diff < timedelta(hours=1):
            return f"{diff.seconds // 60} minutes ago"
        elif diff < timedelta(days=1):
            return f"{diff.seconds // 3600} hours ago"
        else:
            return f"{diff.days} days ago"


class AgentTestRequestSerializer(serializers.Serializer):
    """Serializer for agent test requests"""
    
    test_type = serializers.ChoiceField(choices=['basic', 'full'], default='basic')
    test_data = serializers.DictField(required=False, allow_empty=True)
    
    def validate_test_data(self, value):
        """Validate test data structure for full tests"""
        test_type = self.initial_data.get('test_type')
        
        if test_type == 'full' and value:
            required_fields = ['candidate_name', 'job_title']
            missing_fields = [field for field in required_fields if field not in value]
            
            if missing_fields:
                raise serializers.ValidationError(
                    f"For full tests, the following fields are required: {', '.join(missing_fields)}"
                )
        
        return value


class ConfigurationUpdateSerializer(serializers.Serializer):
    """Serializer for configuration update requests"""
    
    config_type = serializers.ChoiceField(choices=['model', 'agent', 'task', 'template', 'system'])
    config_id = serializers.IntegerField()
    updates = serializers.DictField()
    
    def validate(self, data):
        """Validate that config exists and updates are allowed"""
        config_type = data['config_type']
        config_id = data['config_id']
        updates = data['updates']
        
        # Define allowed fields for each config type
        allowed_fields = {
            'model': ['temperature', 'max_tokens', 'top_p', 'timeout', 'priority', 'is_active'],
            'agent': ['role', 'goal', 'backstory', 'max_execution_time', 'allow_delegation', 'verbose', 'is_active'],
            'task': ['name', 'description', 'expected_output', 'token_limit', 'execution_order', 'is_active'],
            'template': ['content', 'description', 'variables', 'is_active'],
            'system': ['value', 'description', 'is_active']
        }
        
        # Check if all update fields are allowed
        invalid_fields = set(updates.keys()) - set(allowed_fields.get(config_type, []))
        if invalid_fields:
            raise serializers.ValidationError(
                f"Invalid fields for {config_type} configuration: {', '.join(invalid_fields)}"
            )
        
        return data
