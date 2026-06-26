from pydantic import EmailStr
from fastapi import HTTPException,Depends,Form,Request,APIRouter,status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Annotated
from backend.core.security import Token,create_access_token
import backend.crud_db as crud_db
from backend.email_utils import (
send_email,
generate_reset_password_email,
generate_email_token,
verify_email_token
)
from backend.models.models_API import (
    UserNewRegister,
    UserCreate,
    PublicUser,
    Message,
    UserUpdatesAPI)
from backend.core.app_config import settings,templates
from backend.core.control_db import SessionDep,TokenDep

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post("/login/access-token",status_code=200)
def get_login_access_token(session:SessionDep,
                           form_data:Annotated[OAuth2PasswordRequestForm,Depends()])->Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user=crud_db.authenticate_user(db_session=session,email=form_data.username,password=form_data.password)
    if not user:
        raise HTTPException(status_code=400,detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(access_token=create_access_token(user.user_id,access_token_expires))

@router.post("/password-recovery/{email}",status_code=200)
def recover_password(email:EmailStr,session:SessionDep)->Message:
    """Password recovery endpoint"""
    user=crud_db.get_user_by_email(db_session=session,email=email)
    if user:
        payload={"sub":email}
        password_reset_token=generate_email_token(payload,settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
        email_info=generate_reset_password_email(user.username,password_reset_token)
        send_email(
            email_receptor=user.email,
            subject=email_info.subject,
            html_content=email_info.html_content,
        )
    return Message(message="If provided email is registered, a password recovery link was sent.")

@router.get(
    "/reset-password",
    response_class=HTMLResponse
)
def reset_password_form(
        request:Request,
        token:str):
    return templates.TemplateResponse(
        request=request,
        name="forms/reset_password_form.html",
        context={
            "request":request,
            "token":token
        },
    )

@router.post("/reset-password",status_code=status.HTTP_200_OK)
def validate_reset_password(
        session:SessionDep,
        token:str =Form(...),
        new_password:str = Form(...),
        confirm_password:str = Form(...),
):
    if new_password != confirm_password:
        raise HTTPException(status_code=400,detail="Passwords do not match.")

    payload= verify_email_token(token)
    if not payload:
        raise HTTPException(status_code=401,detail="Invalid token")

    email_recovered=payload["sub"]
    user=crud_db.get_user_by_email(db_session=session,email=email_recovered)
    if not user:
        raise HTTPException(status_code=401,detail="Invalid token") #Do not reveal user does not exist. Same error as invalid token is issued#

    user_in_update=UserUpdatesAPI(password=new_password)
    crud_db.update_user_password(db_session=session,user=user,user_new_info=user_in_update)
    return Message(message=f"{user.username}, your password was successfully changed.")























