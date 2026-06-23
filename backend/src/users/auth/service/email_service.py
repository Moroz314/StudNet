import os
from dotenv import load_dotenv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_USERNAME"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER='src/users/auth/service/templates/email'
)

fm = FastMail(conf)

VERIFICATION_CODE_EXPIRE_MINUTES = os.getenv("VERIFICATION_CODE_EXPIRE_MINUTES")

class EmailService:
    @staticmethod
    async def send_verification_email(email: str, code: str):
        try:
            message = MessageSchema(
                subject="Подтверждение email",
                recipients=[email],
                template_body={
                    "code": code,
                    "email": email,
                    "expires_minutes": VERIFICATION_CODE_EXPIRE_MINUTES
                },
                subtype="html"
            )

            await fm.send_message(message, template_name="verification_email.html")
            print(f"Verification email sent to {email}")

        except Exception as e:
            print(f"Failed to send email to {email}: {str(e)}")
            raise
