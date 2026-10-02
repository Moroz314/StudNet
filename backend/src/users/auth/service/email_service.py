import os
import logging
from dotenv import load_dotenv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

load_dotenv()
logger = logging.getLogger(__name__)

DISABLE_EMAIL = os.getenv("DISABLE_EMAIL", "true").lower() in ("true", "1", "yes")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
VERIFICATION_CODE_EXPIRE_MINUTES = os.getenv("VERIFICATION_CODE_EXPIRE_MINUTES", "15")

fm = None
if not DISABLE_EMAIL and MAIL_USERNAME and MAIL_PASSWORD:
    try:
        conf = ConnectionConfig(
            MAIL_USERNAME=MAIL_USERNAME,
            MAIL_PASSWORD=MAIL_PASSWORD,
            MAIL_FROM=MAIL_USERNAME,
            MAIL_PORT=MAIL_PORT,
            MAIL_SERVER=MAIL_SERVER,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            TEMPLATE_FOLDER='src/users/auth/service/templates/email'
        )
        fm = FastMail(conf)
    except Exception as e:
        logger.warning(f"Could not configure FastMail: {e}. Email sending will be skipped.")
        fm = None


class EmailService:
    @staticmethod
    async def send_verification_email(email: str, code: str):
        # Если email отключен или не настроен - логируем код в консоль
        if DISABLE_EMAIL or not fm:
            logger.info(f"===> [EMAIL VERIFICATION CODE] To: {email} | Code: {code} <===")
            print(f"\n=======================================================")
            print(f" [EMAIL VERIFICATION CODE] To: {email}")
            print(f" CODE: {code}")
            print(f" (DISABLE_EMAIL={DISABLE_EMAIL}, SMTP configured={bool(fm)})")
            print(f"=======================================================\n")
            return

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
            logger.info(f"Verification email sent to {email}")

        except Exception as e:
            logger.error(f"Failed to send email to {email}: {str(e)}")
            # Не роняем регистрацию, выводим код в логи как fallback
            print(f"\n=======================================================")
            print(f" [FALLBACK EMAIL VERIFICATION CODE] To: {email}")
            print(f" CODE: {code}")
            print(f" Error sending via SMTP: {e}")
            print(f"=======================================================\n")
