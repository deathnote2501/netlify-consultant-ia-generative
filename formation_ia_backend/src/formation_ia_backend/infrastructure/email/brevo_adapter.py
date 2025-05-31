import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from typing import Optional # Ensure Optional is imported

from formation_ia_backend.core.config import settings

class BrevoEmailAdapter:
    def __init__(self):
        if not settings.BREVO_API_KEY or settings.BREVO_API_KEY == "YOUR_BREVO_API_KEY":
            raise ValueError("BREVO_API_KEY is not properly set or is a placeholder in environment variables.")

        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key['api-key'] = settings.BREVO_API_KEY
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(self.configuration))

        # Define default sender from settings or use placeholders
        self.default_sender_email = getattr(settings, "DEFAULT_SENDER_EMAIL", "noreply@formation-ia.com")
        self.default_sender_name = getattr(settings, "DEFAULT_SENDER_NAME", "Formation IA Platform")
        if "yourdomain.com" in self.default_sender_email or "example.com" in self.default_sender_email :
             print(f"Warning: DEFAULT_SENDER_EMAIL ('{self.default_sender_email}') should be configured properly in settings.")


    async def send_transactional_email(
        self,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        html_content: str,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None
    ) -> bool:
        effective_sender_email = sender_email if sender_email else self.default_sender_email
        effective_sender_name = sender_name if sender_name else self.default_sender_name

        # Ensure 'to_name' is not None for the API call, use to_email if it's None
        api_to_name = to_name if to_name else to_email

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email, "name": api_to_name}],
            sender={"email": effective_sender_email, "name": effective_sender_name},
            subject=subject,
            html_content=html_content
        )
        try:
            # print(f"Attempting to send email: To={to_email}, Subject='{subject}'") # For debugging
            api_response = self.api_instance.send_transac_email(send_smtp_email)
            # print(f"Brevo API response: {api_response}") # For detailed logging if needed
            return True
        except ApiException as e:
            print(f"Exception when calling Brevo TransactionalEmailsApi->send_transac_email: {e}\nBody: {e.body if hasattr(e, 'body') else 'N/A'}")
            return False

    async def send_verification_email(
        self,
        to_email: str,
        user_name: Optional[str],
        verification_link: str
    ):
        subject = "Verify your email address for Formation IA"
        html_content = f"""
        <html><body>
            <h1>Hello {user_name if user_name else 'there'},</h1>
            <p>Please verify your email address by clicking the link below:</p>
            <p><a href="{verification_link}">Verify Email</a></p>
            <p>If you did not request this, please ignore this email.</p>
            <p>Thanks,<br>The Formation IA Team</p>
        </body></html>
        """
        return await self.send_transactional_email(
            to_email=to_email, to_name=user_name, subject=subject, html_content=html_content
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: Optional[str],
        reset_link: str
    ):
        subject = "Reset Your Password for Formation IA"
        html_content = f"""
        <html><body>
            <h1>Hello {user_name if user_name else 'there'},</h1>
            <p>You requested a password reset. Click the link below to set a new password:</p>
            <p><a href="{reset_link}">Reset Password</a></p>
            <p>If you did not request this, please ignore this email.</p>
            <p>This link is valid for a limited time.</p>
            <p>Thanks,<br>The Formation IA Team</p>
        </body></html>
        """
        return await self.send_transactional_email(
            to_email=to_email, to_name=user_name, subject=subject, html_content=html_content
        )

    async def send_payment_confirmation_email(
        self,
        to_email: str,
        user_name: Optional[str],
        plan_name: str
    ):
        subject = f"Your Subscription to {plan_name} is Confirmed!"
        html_content = f"""
        <html><body>
            <h1>Hello {user_name if user_name else 'there'},</h1>
            <p>Thank you for subscribing to the {plan_name} plan on Formation IA!</p>
            <p>Your access has been activated. You can now enjoy all the premium content.</p>
            <p>If you have any questions, feel free to contact our support.</p>
            <p>Happy learning!,<br>The Formation IA Team</p>
        </body></html>
        """
        return await self.send_transactional_email(
            to_email=to_email, to_name=user_name, subject=subject, html_content=html_content
        )
