from django.core.mail import send_mail
from django.conf import settings

def send_status_update_email(report):
    subject = f"Update on Defect Report #{report.id}: {report.title}"
    message = (
        f"Hello Tester,\n\n"
        f"The status of your report '{report.title}' has been updated to: {report.get_status_display()}.\n\n"
        f"View details at: http://127.0.0.1:8000/api/defects/{report.id}/\n\n"
        f"Best,\n\n"
        f"BetaTrax Team"
    )
    recipient = report.testerEmail
    recipient_list = [recipient]
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to write email to file: {e}")
        return False