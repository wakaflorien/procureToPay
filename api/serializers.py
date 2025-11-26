from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, PurchaseRequest, RequestItem, Approval


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'department']
        read_only_fields = ['id']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name', 'role', 'department']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class RequestItemSerializer(serializers.ModelSerializer):
    """Serializer for RequestItem"""
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = RequestItem
        fields = ['id', 'name', 'description', 'quantity', 'unit_price', 'total_price']
        read_only_fields = ['id']


class ApprovalSerializer(serializers.ModelSerializer):
    """Serializer for Approval history"""
    approver = UserSerializer(read_only=True)
    
    class Meta:
        model = Approval
        fields = ['id', 'approver', 'level', 'action', 'comments', 'created_at']
        read_only_fields = ['id', 'created_at']


class PurchaseRequestSerializer(serializers.ModelSerializer):
    """Serializer for PurchaseRequest"""
    created_by = UserSerializer(read_only=True)
    items = RequestItemSerializer(many=True, required=False)
    approvals = ApprovalSerializer(many=True, read_only=True)
    can_be_edited = serializers.ReadOnlyField()
    can_be_approved = serializers.SerializerMethodField()
    has_user_approved = serializers.SerializerMethodField()
    has_user_rejected = serializers.SerializerMethodField()
    needs_receipt_upload = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseRequest
        fields = [
            'id', 'title', 'description', 'amount', 'status',
            'created_by', 'created_at', 'updated_at',
            'proforma', 'purchase_order', 'receipt',
            'proforma_data', 'purchase_order_data', 'receipt_data', 'receipt_validation_result',
            'requires_level_1_approval', 'requires_level_2_approval',
            'level_1_approved', 'level_2_approved',
            'items', 'approvals', 'can_be_edited', 'can_be_approved', 'has_user_approved', 'has_user_rejected',
            'needs_receipt_upload',
        ]
        read_only_fields = [
            'id', 'created_by', 'created_at', 'updated_at',
            'purchase_order', 'purchase_order_data', 'receipt_validation_result',
            'level_1_approved', 'level_2_approved',
        ]
    
    def get_can_be_approved(self, obj):
        """Check if current user can approve this request"""
        request = self.context.get('request')
        if request and request.user:
            return obj.can_be_approved(request.user)
        return False
    
    def get_has_user_approved(self, obj):
        """Check if current user has already approved this request"""
        request = self.context.get('request')
        if request and request.user:
            return obj.has_user_approved(request.user)
        return False
    
    def get_has_user_rejected(self, obj):
        """Check if current user has already rejected this request"""
        request = self.context.get('request')
        if request and request.user:
            return obj.has_user_rejected(request.user)
        return False

    def get_needs_receipt_upload(self, obj):
        """Flag if staff should upload receipt after approvals"""
        return obj.status == 'approved' and not obj.receipt
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        # Get created_by from kwargs if provided (from perform_create), otherwise from context
        created_by = validated_data.pop('created_by', None)
        if created_by is None:
            created_by = self.context['request'].user
        
        request = PurchaseRequest.objects.create(
            created_by=created_by,
            **validated_data
        )
        for item_data in items_data:
            RequestItem.objects.create(request=request, **item_data)
        return request
    
    def update(self, instance, validated_data):
        # Only allow updates if request is pending and not yet approved
        if not instance.can_be_edited():
            raise serializers.ValidationError("Cannot edit request that has been approved or rejected")
        
        items_data = validated_data.pop('items', None)
        
        # Update request fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items if provided
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                RequestItem.objects.create(request=instance, **item_data)
        
        return instance


class PurchaseRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view"""
    created_by = serializers.StringRelatedField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseRequest
        fields = [
            'id', 'title', 'amount', 'status', 'created_by',
            'created_at', 'updated_at', 'items_count',
            'level_1_approved', 'level_2_approved',
        ]
    
    def get_items_count(self, obj):
        return obj.items.count()


class ApproveRequestSerializer(serializers.Serializer):
    """Serializer for approval action"""
    comments = serializers.CharField(required=True, allow_blank=False, help_text="Comments are required for approval decisions")


class RejectRequestSerializer(serializers.Serializer):
    """Serializer for rejection action"""
    comments = serializers.CharField(required=True, allow_blank=False, help_text="Comments are required for rejection decisions")
