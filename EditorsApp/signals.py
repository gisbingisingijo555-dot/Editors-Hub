from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from .models import EditorProfile


@receiver(pre_save, sender=EditorProfile)
def send_status_email(sender, instance, **kwargs):

    if not instance.pk:
        return

    try:
        old = EditorProfile.objects.get(pk=instance.pk)
    except EditorProfile.DoesNotExist:
        return

    if old.status != instance.status:

        email = instance.user.email
        username = instance.user.username

        # ✅ APPROVED
        if instance.status == 'approved':

            html_content = render_to_string('emails/approved.html', {
                'username': username
            })

            msg = EmailMultiAlternatives(
                subject="🎉 Profile Approved",
                body="Your profile has been approved.",
                from_email=settings.EMAIL_HOST_USER,
                to=[email],
            )

            msg.attach_alternative(html_content, "text/html")
            msg.send()


        # ❌ REJECTED
        elif instance.status == 'rejected':

            reason = instance.rejection_reason or "No reason provided"

            html_content = render_to_string('emails/rejected.html', {
                'username': username,
                'reason': reason
            })

            msg = EmailMultiAlternatives(
                subject="Application Rejected",
                body="Your application was rejected.",
                from_email=settings.EMAIL_HOST_USER,
                to=[email],
            )

            msg.attach_alternative(html_content, "text/html")
            msg.send()