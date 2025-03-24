from django.contrib import admin
from .models import User, Department, Ticket

# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin configuration for the User model."""
    # Fields shown in the list view
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'is_staff', 'is_active', 'date_joined', 'last_login')
    list_filter = ('role', 'department', 'is_staff', 'is_superuser', 'is_active', 'date_joined')# Filters shown on the right side of the list page
    search_fields = ('username', 'email', 'first_name', 'last_name')# Fields that can be searched
    ordering = ['role', 'username'] # Default ordering of list view
    readonly_fields = ('date_joined', 'last_login')# Fields that are read-only

    # Field grouping for detail/edit view
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

    # Fields shown when creating a new user in admin
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

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'sender_email', 'priority', 'assigned_user', 'created_at')
    search_fields = ('title', 'sender_email')
    list_filter = ('status', 'priority', 'assigned_user', 'created_at')