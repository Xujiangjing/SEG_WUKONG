from django.contrib import admin
from .models import User, Department

# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin configuration for the User model."""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'is_staff', 'is_active', 'date_joined', 'last_login')
    list_filter = ('role', 'department', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ['role', 'username']
    readonly_fields = ('date_joined', 'last_login')
    fieldsets = (
        ('Personal Info', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'password')
        }),
        ('Role and Department', {
            'fields': ('role', 'department')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'password1', 'password2'),
        }),
    )
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin configuration for the Department model."""
    list_display = ('name', 'description')
    search_fields = ('name',)
    ordering = ['name']
