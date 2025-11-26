from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal, InvalidOperation
import uuid
import os


class User(AbstractUser):
    """Custom User model with role-based access control"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('approver_level_1', 'Approver Level 1'),
        ('approver_level_2', 'Approver Level 2'),
        ('finance', 'Finance'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    department = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_staff_role(self):
        return self.role == 'staff'
    
    def is_approver_level_1(self):
        return self.role == 'approver_level_1'
    
    def is_approver_level_2(self):
        return self.role == 'approver_level_2'
    
    def is_finance(self):
        return self.role == 'finance'
    
    def can_approve(self):
        return self.role in ['approver_level_1', 'approver_level_2', 'admin']

    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


def upload_to_proforma(instance, filename):
    """Generate upload path for proforma documents"""
    return f'proformas/{instance.id}/{filename}'


def upload_to_po(instance, filename):
    """Generate upload path for purchase order documents"""
    return f'purchase_orders/{instance.id}/{filename}'


def upload_to_receipt(instance, filename):
    """Generate upload path for receipt documents"""
    return f'receipts/{instance.id}/{filename}'


class PurchaseRequest(models.Model):
    """Purchase Request model with approval workflow"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Document fields
    proforma = models.FileField(upload_to=upload_to_proforma, blank=True, null=True)
    purchase_order = models.FileField(upload_to=upload_to_po, blank=True, null=True)
    receipt = models.FileField(upload_to=upload_to_receipt, blank=True, null=True)
    
    # Extracted data from documents
    proforma_data = models.JSONField(default=dict, blank=True)
    purchase_order_data = models.JSONField(default=dict, blank=True)
    receipt_data = models.JSONField(default=dict, blank=True)
    receipt_validation_result = models.JSONField(default=dict, blank=True)
    
    # Approval tracking
    requires_level_1_approval = models.BooleanField(default=True)
    requires_level_2_approval = models.BooleanField(default=True)
    level_1_approved = models.BooleanField(default=False)
    level_2_approved = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['created_by', 'status']),
        ]
    
    def can_be_edited(self):
        """Check if request can still be edited"""
        return self.status == 'pending' and not (self.level_1_approved or self.level_2_approved)
    
    def can_be_approved(self, user):
        """Check if user can approve this request"""
        if getattr(user, 'is_admin', None) and user.is_admin():
            return True
        if self.status != 'pending':
            return False
        # Check if user has already approved/rejected this request
        if self.approvals.filter(approver=user).exists():
            return False
        if user.is_approver_level_1() and not self.level_1_approved:
            return True
        if user.is_approver_level_2() and self.level_1_approved and not self.level_2_approved:
            return True
        return False
    
    def has_user_approved(self, user):
        """Check if user has already approved this request"""
        return self.approvals.filter(approver=user, action='approved').exists()
    
    def has_user_rejected(self, user):
        """Check if user has already rejected this request"""
        return self.approvals.filter(approver=user, action='rejected').exists()
    
    def approve(self, user):
        """Approve request at appropriate level"""
        if getattr(user, 'is_admin', None) and user.is_admin():
            self.level_1_approved = True
            self.level_2_approved = True
            self.status = 'approved'
        elif user.is_approver_level_1() and not self.level_1_approved:
            self.level_1_approved = True
            if not self.requires_level_2_approval:
                self.status = 'approved'
        elif user.is_approver_level_2() and self.level_1_approved and not self.level_2_approved:
            self.level_2_approved = True
            self.status = 'approved'
        self.save()
    
    def reject(self):
        """Reject the request"""
        self.status = 'rejected'
        self.save()

    def cancel(self):
        """Cancel the request via finance override"""
        self.status = 'cancelled'
        self.save()

    def has_proforma_discrepancies(self, amount_tolerance=Decimal('1.00')) -> bool:
        """Check if extracted proforma data matches the original request"""
        if not self.proforma_data:
            return True

        proforma_amount = self.proforma_data.get('amount')
        try:
            proforma_amount = Decimal(str(proforma_amount))
        except (InvalidOperation, TypeError):
            return True

        if proforma_amount is None or abs(Decimal(self.amount) - proforma_amount) > amount_tolerance:
            return True

        proforma_items = self.proforma_data.get('items') or []
        request_items = list(self.items.all())

        if not request_items or not proforma_items:
            return True

        proforma_map = {
            (item.get('name') or '').strip().lower(): item
            for item in proforma_items
            if item
        }

        request_names = set()
        for req_item in request_items:
            key = (req_item.name or '').strip().lower()
            request_names.add(key)
            proforma_item = proforma_map.get(key)
            if not proforma_item:
                return True
            qty = proforma_item.get('quantity')
            try:
                qty = int(qty)
            except (TypeError, ValueError):
                return True
            price_value = proforma_item.get('price', proforma_item.get('unit_price'))
            try:
                price_value = Decimal(str(price_value))
            except (InvalidOperation, TypeError):
                return True
            if qty != req_item.quantity:
                return True
            if abs(price_value - Decimal(req_item.unit_price)) > Decimal('0.01'):
                return True

        # Extra proforma items not in request
        for name in proforma_map.keys():
            if name and name not in request_names:
                return True

        return False
    
    def is_fully_approved(self):
        """Check if all required approvals are complete"""
        if self.requires_level_1_approval and not self.level_1_approved:
            return False
        if self.requires_level_2_approval and not self.level_2_approved:
            return False
        return True
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


class RequestItem(models.Model):
    """Items within a purchase request"""
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price
    
    def __str__(self):
        return f"{self.name} x{self.quantity}"


class Approval(models.Model):
    """Track approval history"""
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approvals')
    level = models.CharField(max_length=20)  # 'level_1' or 'level_2'
    action = models.CharField(max_length=20)  # 'approved' or 'rejected'
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.approver.username} {self.action} {self.request.title} at {self.level}"

