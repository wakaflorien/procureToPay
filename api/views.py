from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import PurchaseRequest, Approval, User
from .serializers import (
    PurchaseRequestSerializer,
    PurchaseRequestListSerializer,
    ApproveRequestSerializer,
    RejectRequestSerializer,
    UserSerializer,
    UserRegistrationSerializer,
)
from .permissions import IsStaff, IsApprover, IsStaffOrFinance, IsFinance
from django.http import FileResponse, Http404
from .document_processor import DocumentProcessor


class PurchaseRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for PurchaseRequest with role-based access"""
    permission_classes = [IsAuthenticated]
    queryset = PurchaseRequest.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PurchaseRequestListSerializer
        return PurchaseRequestSerializer
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        # Handle schema generation (DRF-YASG)
        if getattr(self, 'swagger_fake_view', False):
            return PurchaseRequest.objects.none()
        
        # Handle cases where request might not be available (schema generation)
        if not hasattr(self, 'request') or not hasattr(self.request, 'user'):
            return PurchaseRequest.objects.none()
        
        user = self.request.user
        
        # Handle AnonymousUser for schema generation
        if not user.is_authenticated or not isinstance(user, User):
            return PurchaseRequest.objects.none()
        
        if getattr(user, 'is_admin', None) and user.is_admin():
            queryset = PurchaseRequest.objects.all()
        elif user.is_staff_role():
            # Staff can only see their own requests
            queryset = PurchaseRequest.objects.filter(created_by=user)
        elif user.can_approve():
            # Approvers can see pending requests and their reviewed requests
            queryset = PurchaseRequest.objects.filter(
                Q(status='pending') | Q(approvals__approver=user)
            ).distinct()
        elif user.is_finance():
            # Finance can only see approved requests (no filtering)
            queryset = PurchaseRequest.objects.filter(status='approved')
        else:
            queryset = PurchaseRequest.objects.none()

        status_filter = self.request.query_params.get('status')
        if status_filter in dict(PurchaseRequest.STATUS_CHOICES):
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def update(self, request, *args, **kwargs):
        """Update request - only if pending and not approved"""
        instance = self.get_object()
        
        # Check permissions
        if instance.created_by != request.user and not request.user.is_finance():
            return Response(
                {"detail": "You can only edit your own requests."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not instance.can_be_edited():
            return Response(
                {"detail": "Cannot edit request that has been approved or rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete request - only owner can delete pending requests"""
        instance = self.get_object()
        
        # Check permissions - only owner can delete
        if instance.created_by != request.user:
            return Response(
                {"detail": "You can only delete your own requests."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow deletion of pending requests
        if instance.status != 'pending':
            return Response(
                {"detail": "Can only delete pending requests."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if request has been approved (additional safety check)
        if instance.level_1_approved or instance.level_2_approved:
            return Response(
                {"detail": "Cannot delete request that has been approved."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], permission_classes=[IsApprover])
    def approve(self, request, pk=None):
        """Approve a purchase request"""
        purchase_request = self.get_object()
        serializer = ApproveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_admin_override = hasattr(request.user, 'is_admin') and request.user.is_admin()
        
        if not is_admin_override and not purchase_request.can_be_approved(request.user):
            return Response(
                {"detail": "You cannot approve this request at this time."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Use select_for_update to prevent concurrent approval race conditions
            purchase_request = PurchaseRequest.objects.select_for_update().get(pk=purchase_request.pk)
            
            # Re-check if request can still be approved (might have changed during concurrent access)
            if not is_admin_override and not purchase_request.can_be_approved(request.user):
                return Response(
                    {"detail": "Request status has changed. Please refresh and try again."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user has already approved/rejected this request
            if not is_admin_override and purchase_request.approvals.filter(approver=request.user).exists():
                return Response(
                    {"detail": "You have already performed an action on this request."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Determine approval level
            if is_admin_override:
                level = 'admin_override'
            else:
                level = 'level_1' if request.user.is_approver_level_1() else 'level_2'

            requires_level_2 = purchase_request.requires_level_2_approval
            will_complete_flow = False
            if is_admin_override:
                will_complete_flow = True
            elif not requires_level_2 and level == 'level_1':
                will_complete_flow = True
            elif requires_level_2 and level == 'level_2':
                will_complete_flow = True

            if will_complete_flow and not is_admin_override and purchase_request.has_proforma_discrepancies():
                return Response(
                    {
                        "detail": "Proforma data does not match the original request. Please escalate to finance for review."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create approval record
            Approval.objects.create(
                request=purchase_request,
                approver=request.user,
                level=level,
                action='approved',
                comments=serializer.validated_data.get('comments', '')
            )
            
            # Approve the request
            purchase_request.approve(request.user)
            
            # Generate PO if fully approved (last approver triggers this)
            if purchase_request.status == 'approved' and purchase_request.proforma_data:
                po_data = DocumentProcessor.generate_purchase_order_data(
                    purchase_request,
                    purchase_request.proforma_data
                )
                purchase_request.purchase_order_data = po_data
                purchase_request.save()
        
        return Response(
            PurchaseRequestSerializer(purchase_request, context={'request': request}).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsApprover])
    def reject(self, request, pk=None):
        """Reject a purchase request"""
        purchase_request = self.get_object()
        serializer = RejectRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_admin_override = hasattr(request.user, 'is_admin') and request.user.is_admin()
        
        if not is_admin_override and purchase_request.status != 'pending':
            return Response(
                {"detail": "Can only reject pending requests."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has already approved/rejected this request
        if not is_admin_override and purchase_request.approvals.filter(approver=request.user).exists():
            return Response(
                {"detail": "You have already performed an action on this request."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Use select_for_update to prevent concurrent rejection race conditions
            purchase_request = PurchaseRequest.objects.select_for_update().get(pk=purchase_request.pk)
            
            # Re-check if request is still pending (might have changed during concurrent access)
            if not is_admin_override and purchase_request.status != 'pending':
                return Response(
                    {"detail": "Request status has changed. Please refresh and try again."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Re-check if user has already performed an action
            if not is_admin_override and purchase_request.approvals.filter(approver=request.user).exists():
                return Response(
                    {"detail": "You have already performed an action on this request."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Determine approval level
            if is_admin_override:
                level = 'admin_override'
            else:
                level = 'level_1' if request.user.is_approver_level_1() else 'level_2'
            
            # Create approval record
            Approval.objects.create(
                request=purchase_request,
                approver=request.user,
                level=level,
                action='rejected',
                comments=serializer.validated_data.get('comments', '')
            )
            
            # Reject the request
            purchase_request.reject()
        
        return Response(
            PurchaseRequestSerializer(purchase_request, context={'request': request}).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsFinance])
    def cancel(self, request, pk=None):
        """Finance cancellation/manual override"""
        purchase_request = self.get_object()
        serializer = RejectRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if purchase_request.status == 'cancelled':
            return Response(
                {"detail": "Request is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            purchase_request = PurchaseRequest.objects.select_for_update().get(pk=purchase_request.pk)
            if purchase_request.status == 'cancelled':
                return Response(
                    {"detail": "Request is already cancelled."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Approval.objects.create(
                request=purchase_request,
                approver=request.user,
                level='finance_override',
                action='cancelled',
                comments=serializer.validated_data.get('comments', '')
            )
            purchase_request.cancel()

        return Response(
            PurchaseRequestSerializer(purchase_request, context={'request': request}).data,
            status=status.HTTP_200_OK
        )
    
    @swagger_auto_schema(
        method='post',
        operation_description="Upload a proforma invoice document (PDF or image) and extract data from it. "
                             "The system will automatically extract vendor information, amounts, items, and payment terms. "
                             "Supported formats: PDF, JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP.",
        operation_summary="Upload and process proforma invoice",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['proforma'],
            properties={
                'proforma': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Proforma invoice file (PDF or image). The file will be processed using OCR for images or text extraction for PDFs."
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Proforma uploaded and processed successfully. Returns extracted data including vendor, amount, items, and terms."
            ),
            400: openapi.Response(description="Bad request - No file provided or invalid file"),
            403: openapi.Response(description="Forbidden - Not authorized to submit proforma for this request"),
            500: openapi.Response(description="Internal server error - Error processing the document"),
        },
        tags=['Purchase Requests'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrFinance])
    def submit_proforma(self, request, pk=None):
        """Submit proforma document and extract data"""
        purchase_request = self.get_object()
        
        # Staff can only submit for their own requests, Finance can submit for any request
        if purchase_request.created_by != request.user and not request.user.is_finance():
            return Response(
                {"detail": "You can only submit proforma for your own requests."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if 'proforma' not in request.FILES:
            return Response(
                {"detail": "No proforma file provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        proforma_file = request.FILES['proforma']
        
        # Extract data from proforma BEFORE saving (file pointer needs to be at start)
        try:
            # Reset file pointer to beginning
            if hasattr(proforma_file, 'seek'):
                proforma_file.seek(0)
            
            proforma_data = DocumentProcessor.extract_proforma_data(proforma_file)
            
            # Reset file pointer again before saving
            if hasattr(proforma_file, 'seek'):
                proforma_file.seek(0)
            
            # Now save the file
            purchase_request.proforma = proforma_file
            purchase_request.proforma_data = proforma_data
            purchase_request.save()
            
            return Response({
                "message": "Proforma uploaded and processed successfully.",
                "extracted_data": proforma_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error processing proforma: {str(e)}")
            print(f"Traceback: {error_trace}")
            return Response(
                {"detail": f"Error processing proforma: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        method='post',
        operation_description="Upload a receipt document (PDF or image) and validate it against the purchase order. "
                             "The system will extract vendor, amount, and items from the receipt and compare them with the PO data. "
                             "Supported formats: PDF, JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP.",
        operation_summary="Upload and validate receipt against purchase order",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['receipt'],
            properties={
                'receipt': openapi.Schema(
                    type=openapi.TYPE_FILE,
                    description="Receipt file (PDF or image). The file will be processed and validated against the purchase order."
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Receipt uploaded and validated successfully. Returns validation results including matches and any errors/warnings."
            ),
            400: openapi.Response(description="Bad request - No file provided, request not approved, or PO not generated"),
            403: openapi.Response(description="Forbidden - Not authorized to submit receipt for this request"),
            500: openapi.Response(description="Internal server error - Error processing the receipt"),
        },
        tags=['Purchase Requests'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrFinance])
    def submit_receipt(self, request, pk=None):
        """Submit receipt and validate against PO"""
        purchase_request = self.get_object()
        
        # Staff can only submit for their own requests, Finance can submit for any request
        if purchase_request.created_by != request.user and not request.user.is_finance():
            return Response(
                {"detail": "You can only submit receipt for your own requests."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if purchase_request.status != 'approved':
            return Response(
                {"detail": "Can only submit receipt for approved requests."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not purchase_request.purchase_order_data:
            return Response(
                {"detail": "Purchase order not yet generated."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if 'receipt' not in request.FILES:
            return Response(
                {"detail": "No receipt file provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        receipt_file = request.FILES['receipt']
        purchase_request.receipt = receipt_file
        
        # Validate receipt against PO
        try:
            validation_result = DocumentProcessor.validate_receipt(
                receipt_file,
                purchase_request.purchase_order_data
            )
            purchase_request.receipt_validation_result = validation_result
            purchase_request.receipt_data = validation_result.get('receipt_data', {})
            purchase_request.save()
            
            return Response({
                "message": "Receipt uploaded and validated.",
                "validation_result": validation_result
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": f"Error processing receipt: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def download_proforma(self, request, pk=None):
        """Download proforma document - available to approvers, finance, and admins"""
        purchase_request = self.get_object()
        
        # Check permissions: approvers, finance, or admin can download
        if not (request.user.can_approve() or request.user.is_finance() or request.user.is_superuser):
            return Response(
                {"detail": "You do not have permission to download this document."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not purchase_request.proforma:
            raise Http404("Proforma document not found")
        
        try:
            response = FileResponse(
                purchase_request.proforma.open('rb'),
                content_type='application/pdf' if purchase_request.proforma.name.endswith('.pdf') else 'image/jpeg'
            )
            filename = purchase_request.proforma.name.split('/')[-1]
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response(
                {"detail": f"Error downloading proforma: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def download_receipt(self, request, pk=None):
        """Download receipt document - available to approvers, finance, and admins"""
        purchase_request = self.get_object()
        
        # Check permissions: approvers, finance, or admin can download
        if not (request.user.can_approve() or request.user.is_finance() or request.user.is_superuser):
            return Response(
                {"detail": "You do not have permission to download this document."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not purchase_request.receipt:
            raise Http404("Receipt document not found")
        
        try:
            response = FileResponse(
                purchase_request.receipt.open('rb'),
                content_type='application/pdf' if purchase_request.receipt.name.endswith('.pdf') else 'image/jpeg'
            )
            filename = purchase_request.receipt.name.split('/')[-1]
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response(
                {"detail": f"Error downloading receipt: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def download_purchase_order(self, request, pk=None):
        """Download purchase order document - available to approvers, finance, and admins"""
        purchase_request = self.get_object()
        
        # Check permissions: approvers, finance, or admin can download
        if not (request.user.can_approve() or request.user.is_finance() or request.user.is_superuser):
            return Response(
                {"detail": "You do not have permission to download this document."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not purchase_request.purchase_order:
            raise Http404("Purchase order document not found")
        
        try:
            response = FileResponse(
                purchase_request.purchase_order.open('rb'),
                content_type='application/pdf'
            )
            filename = purchase_request.purchase_order.name.split('/')[-1]
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response(
                {"detail": f"Error downloading purchase order: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile endpoint"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
