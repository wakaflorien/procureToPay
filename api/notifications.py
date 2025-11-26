"""
Email notification service for purchase request approvals and rejections
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import PurchaseRequest, Approval


def send_approval_notification(purchase_request: PurchaseRequest, approval: Approval):
    """Send email notification when a request is approved"""
    try:
        # Get the requester (staff member who created the request)
        requester = purchase_request.created_by
        
        # Determine notification type
        if purchase_request.status == 'approved':
            subject = f'Purchase Request Approved: {purchase_request.title}'
            action = 'approved'
            message_type = 'final approval' if purchase_request.level_2_approved else 'level 1 approval'
        else:
            subject = f'Purchase Request Partially Approved: {purchase_request.title}'
            action = 'partially approved'
            message_type = 'level 1 approval'
        
        # Prepare email context
        context = {
            'requester_name': requester.get_full_name() or requester.username,
            'request_title': purchase_request.title,
            'request_id': str(purchase_request.id),
            'request_amount': purchase_request.amount,
            'approver_name': approval.approver.get_full_name() or approval.approver.username,
            'approval_level': approval.level,
            'comments': approval.comments,
            'action': action,
            'message_type': message_type,
            'status': purchase_request.status,
            'request_url': f'{settings.FRONTEND_URL}/requests/{purchase_request.id}' if hasattr(settings, 'FRONTEND_URL') else None,
        }
        
        # Render email template
        html_message = render_to_string('emails/approval_notification.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[requester.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Also notify next approver if needed
        if purchase_request.status != 'approved' and purchase_request.requires_level_2_approval:
            send_next_approver_notification(purchase_request)
            
    except Exception as e:
        # Log error but don't fail the approval process
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send approval notification: {str(e)}")


def send_rejection_notification(purchase_request: PurchaseRequest, approval: Approval):
    """Send email notification when a request is rejected"""
    try:
        # Get the requester (staff member who created the request)
        requester = purchase_request.created_by
        
        subject = f'Purchase Request Rejected: {purchase_request.title}'
        
        # Prepare email context
        context = {
            'requester_name': requester.get_full_name() or requester.username,
            'request_title': purchase_request.title,
            'request_id': str(purchase_request.id),
            'request_amount': purchase_request.amount,
            'rejector_name': approval.approver.get_full_name() or approval.approver.username,
            'rejection_level': approval.level,
            'comments': approval.comments,
            'request_url': f'{settings.FRONTEND_URL}/requests/{purchase_request.id}' if hasattr(settings, 'FRONTEND_URL') else None,
        }
        
        # Render email template
        html_message = render_to_string('emails/rejection_notification.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[requester.email],
            html_message=html_message,
            fail_silently=False,
        )
            
    except Exception as e:
        # Log error but don't fail the rejection process
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send rejection notification: {str(e)}")


def send_next_approver_notification(purchase_request: PurchaseRequest):
    """Notify the next approver in the workflow"""
    try:
        # Find level 2 approvers
        level_2_approvers = purchase_request.__class__.objects.none()
        from .models import User
        approvers = User.objects.filter(role='approver_level_2')
        
        if not approvers.exists():
            return
        
        subject = f'Purchase Request Pending Approval: {purchase_request.title}'
        
        for approver in approvers:
            context = {
                'approver_name': approver.get_full_name() or approver.username,
                'request_title': purchase_request.title,
                'request_id': str(purchase_request.id),
                'request_amount': purchase_request.amount,
                'requester_name': purchase_request.created_by.get_full_name() or purchase_request.created_by.username,
                'request_url': f'{settings.FRONTEND_URL}/requests/{purchase_request.id}' if hasattr(settings, 'FRONTEND_URL') else None,
            }
            
            html_message = render_to_string('emails/pending_approval_notification.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[approver.email],
                html_message=html_message,
                fail_silently=False,
            )
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send next approver notification: {str(e)}")

