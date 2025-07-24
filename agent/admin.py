from django.contrib import admin
from .models import (
    ModelConfiguration, AgentConfiguration, TaskConfiguration,
    PromptTemplate, SystemConfiguration, HiringSession, ErrorLog
)


@admin.register(ModelConfiguration)
class ModelConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_name', 'temperature', 'max_tokens', 'priority', 'is_active', 'is_fallback']
    list_filter = ['is_active', 'is_fallback', 'priority']
    search_fields = ['name', 'model_name']
    ordering = ['-priority', 'name']
    
    fieldsets = (
        ('Basic Configuration', {
            'fields': ('name', 'model_name', 'is_active', 'is_fallback', 'priority')
        }),
        ('Model Parameters', {
            'fields': ('temperature', 'max_tokens', 'top_p', 'timeout'),
            'description': 'Adjust these parameters to optimize model performance'
        }),
    )


@admin.register(AgentConfiguration)
class AgentConfigurationAdmin(admin.ModelAdmin):
    list_display = ['agent_type', 'role', 'model_config', 'max_execution_time', 'is_active']
    list_filter = ['agent_type', 'is_active', 'model_config', 'allow_delegation', 'verbose']
    search_fields = ['role', 'goal']
    ordering = ['agent_type']
    
    fieldsets = (
        ('Agent Identity', {
            'fields': ('agent_type', 'role', 'goal', 'backstory')
        }),
        ('Configuration', {
            'fields': ('model_config', 'max_execution_time', 'allow_delegation', 'verbose', 'is_active')
        }),
    )


@admin.register(TaskConfiguration)
class TaskConfigurationAdmin(admin.ModelAdmin):
    list_display = ['task_type', 'name', 'agent_config', 'token_limit', 'execution_order', 'is_active']
    list_filter = ['task_type', 'is_active', 'agent_config']
    search_fields = ['name', 'description']
    ordering = ['execution_order', 'task_type']
    
    fieldsets = (
        ('Task Definition', {
            'fields': ('task_type', 'name', 'description', 'expected_output')
        }),
        ('Execution Settings', {
            'fields': ('agent_config', 'token_limit', 'execution_order', 'is_active')
        }),
    )


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active', 'created_at']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'description', 'content']
    ordering = ['template_type', 'name']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'template_type', 'description', 'is_active')
        }),
        ('Template Content', {
            'fields': ('content', 'variables'),
            'description': 'Use {variable_name} placeholders for dynamic content'
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['content'].widget.attrs['rows'] = 10
        form.base_fields['content'].widget.attrs['cols'] = 80
        return form


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'data_type', 'is_active']
    list_filter = ['data_type', 'is_active']
    search_fields = ['key', 'description']
    ordering = ['key']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('key', 'value', 'data_type', 'is_active')
        }),
        ('Documentation', {
            'fields': ('description',)
        }),
    )


@admin.register(HiringSession)
class HiringSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'candidate_name', 'job_title', 'status', 'execution_time', 'created_at']
    list_filter = ['status', 'model_config_used', 'created_at']
    search_fields = ['session_id', 'candidate_name', 'job_title']
    ordering = ['-created_at']
    readonly_fields = ['session_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_id', 'candidate_name', 'job_title', 'status')
        }),
        ('Configuration', {
            'fields': ('model_config_used', 'execution_time')
        }),
        ('Data', {
            'fields': ('input_data', 'results'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ['error_type', 'message_short', 'session', 'model_config', 'resolved', 'created_at']
    list_filter = ['error_type', 'resolved', 'model_config', 'created_at']
    search_fields = ['message', 'session__session_id']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Error Information', {
            'fields': ('error_type', 'message', 'resolved')
        }),
        ('Context', {
            'fields': ('session', 'model_config', 'details')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def message_short(self, obj):
        return obj.message[:100] + "..." if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Message'
    
    actions = ['mark_resolved']
    
    def mark_resolved(self, request, queryset):
        queryset.update(resolved=True)
    mark_resolved.short_description = "Mark selected errors as resolved"
