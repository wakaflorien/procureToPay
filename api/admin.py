from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PurchaseRequest, RequestItem, Approval


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'department', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'department')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'department')}),
    )


class RequestItemInline(admin.TabularInline):
    model = RequestItem
    extra = 1


class ApprovalInline(admin.TabularInline):
    model = Approval
    extra = 0
    readonly_fields = ['approver', 'level', 'action', 'comments', 'created_at']
    can_delete = False


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'amount', 'status', 'level_1_approved', 'level_2_approved', 'created_at']
    list_filter = ['status', 'created_at', 'level_1_approved', 'level_2_approved']
    search_fields = ['title', 'description', 'created_by__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'purchase_order_data', 'receipt_validation_result']
    inlines = [RequestItemInline, ApprovalInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'description', 'amount', 'status', 'created_by')
        }),
        ('Approval Status', {
            'fields': ('requires_level_1_approval', 'requires_level_2_approval',
                      'level_1_approved', 'level_2_approved')
        }),
        ('Documents', {
            'fields': ('proforma', 'purchase_order', 'receipt')
        }),
        ('Extracted Data', {
            'fields': ('proforma_data', 'purchase_order_data', 'receipt_data', 'receipt_validation_result'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ['request', 'approver', 'level', 'action', 'created_at']
    list_filter = ['action', 'level', 'created_at']
    readonly_fields = ['created_at']
    search_fields = ['request__title', 'approver__username']
