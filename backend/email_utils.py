
import jwt
import logging
from dataclasses import dataclass
from backend.core.app_config import settings
from datetime import timedelta,timezone,datetime
import emails
from backend.models.models_API import ProjectAccess
from jinja2 import Template
from pathlib import Path
import backend.core.security as security
from typing import Any
from backend.models.models_db import Project

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmailData:
    html_content: str
    subject: str

def render_templates_emails(
        *,email_template_name:str,
        context: dict[str, Any],)->str:

    template_route=(
        Path(__file__).parent / "templates" / "email_templates"/email_template_name).read_text()
    html_content=Template(template_route).render(**context)
    return html_content

def send_email(
        *,
        email_receptor:str,
        subject:str="",
        html_content:str="",
)->None:
    if not settings.emails_enabled:
        logger.warning(
            "Email sending attempted but emails are disabled"
        )
        return
    message=emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME,settings.EMAILS_FROM_EMAIL),
    )
    smtp_options={"host":settings.SMTP_HOST,"port":settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    try:
        response = message.send(
            to=email_receptor,
            smtp=smtp_options
        )
        logger.info(response)
    except Exception:
        # Intentionally broad:
        # email delivery failures should not break the request flow.
        logger.exception(
            "Failed to send password recovery email "
            f"to {email_receptor}"
        )
    #logger.info(f"send email result: {response}")

def generate_reset_password_email(
        username:str,
        token:str)->EmailData:
    project_name=settings.PROJECT_NAME
    subject=f"{project_name} - Password recovery for user: {username}"
    link=f"{settings.API_HOST}/auth/reset-password?token={token}"
    html_content=render_templates_emails(
        email_template_name="reset_password_email.html",
        context={
        "app_name":settings.PROJECT_NAME,
        "username":username,
        "valid_hours":settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
        "link":link,
        },
    )
    return EmailData(html_content=html_content,subject=subject)



def generate_invitation_email(
        invited_by_username:str,
        username_invited:str,
        token:str,
        project:Project)->EmailData:

    subject=f"{settings.PROJECT_NAME} - Invitation for {username_invited} to join {project.name}"
    link=f"{settings.API_HOST}/join-project?token={token}"
    html_content=render_templates_emails(
        email_template_name="invitation_project_email.html",
        context={
            "app_name":settings.PROJECT_NAME,
            "username":username_invited,
            "invited_by":invited_by_username,
            "assigned_role": ProjectAccess.participant.value,
            "project_name":project.name,
            "project_description":project.description,
            "valid_hours":settings.EMAIL_INVITATION_TOKEN_EXPIRE_HOURS,
            "invitation_link":link,
        }
    )
    return EmailData(html_content=html_content,subject=subject)

def generate_email_token(payload:dict,duration:int)->str:
    delta = timedelta(hours=duration)
    now = datetime.now(timezone.utc)
    expires = now + delta
    payload["exp"]=expires
    encoded_jwt=jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt

def verify_email_token(token: str) -> str|Any:
    try:
        decoded_token=jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[security.ALGORITHM]
        )
        return decoded_token
    except jwt.InvalidTokenError:
        return None


