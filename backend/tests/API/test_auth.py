
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

import backend.crud_db as crud
from backend.core.app_config import settings
from backend.models.models_API import UserCreate
from backend.models.models_db import User
from backend.tests.utils.utils import random_lower_string
from backend.utils.email_utils import generate_email_token


def test_login_get_access_token(
        client:TestClient,
        crud_test_user:User,
        user_create:UserCreate)->None:
    login_data={
        "username":crud_test_user.email,
        "password":user_create.password
    }

    r =client.post(f"{settings.API_HOST}/auth/login/access-token",
                   data=login_data)
    tokens=r.json()

    assert r.status_code==200
    assert "access_token" in tokens
    assert tokens["access_token"]

def test_login_get_access_token_incorrect_password(
        client:TestClient,
        crud_test_user:User)->None:
    login_data={
        "username":crud_test_user.email,
        "password":"incorrect_password"
    }
    r=client.post(f"{settings.API_HOST}/auth/login/access-token",
                  data=login_data)
    assert r.status_code==400
    assert r.json()["detail"] == "Incorrect email or password"

def test_recover_password(client:TestClient,
    crud_test_user:User)->None:

    email=crud_test_user.email
    with patch(
            "backend.API.auth.send_email",
    ) as mock_send_email:
        r = client.post(
            f"{settings.API_HOST}/auth/password-recovery/{email}"
        )
        args, kwargs = mock_send_email.call_args
        assert r.status_code == 200
        assert kwargs["email_receptor"] == email
        mock_send_email.assert_called_once()
        assert r.json()=={"message":"If provided email is registered, a password recovery link was sent."}

def test_recover_password_user_does_not_exist(client:TestClient)->None:
    email="ijYnv@example.com"
    r = client.post(f"{settings.API_HOST}/auth/password-recovery/{email}")
    assert r.status_code==200
    assert r.json()=={"message":"If provided email is registered, a password recovery link was sent."}

def test_reset_password(client:TestClient,db:Session,crud_test_user:User)->None:
    new_password=random_lower_string()
    payload={"sub":crud_test_user.email}
    token=generate_email_token(
        payload,
        settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    data={"new_password":new_password,
          "confirm_password":new_password,
          "token":token}
    r=client.post(f"{settings.API_HOST}/auth/reset-password",data=data)
    assert r.status_code==200
    assert r.json()=={"message":f"{crud_test_user.username}, your password was successfully changed."}

def test_reset_password_incorrect_confirmation_error(
        client:TestClient,
        crud_test_user:User)->None:

    new_password=random_lower_string()
    payload={"sub":crud_test_user.email}
    token=generate_email_token(
        payload,
        settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    data={"new_password":new_password,
          "confirm_password":"other_password",
          "token":token}
    r=client.post(f"{settings.API_HOST}/auth/reset-password",
                  data=data)
    assert r.status_code==400
    assert r.json()["detail"]=="Passwords do not match."

def test_reset_password_invalid_token(client:TestClient)->None:
    new_password=random_lower_string()
    data={"new_password":new_password,
          "confirm_password":new_password,
          "token":"invalid_token"}
    r=client.post(f"{settings.API_HOST}/auth/reset-password",
                  data=data)
    assert r.status_code==401
    assert r.json()["detail"] == "Invalid token"

def test_reset_password_non_existent_user_email(
        db:Session,
        client:TestClient,crud_test_user:User,
        user_create:UserCreate)->None:

    new_password = random_lower_string()
    payload = {"sub": crud_test_user.email}
    token = generate_email_token(
        payload,
        settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    data = {"new_password": new_password,
            "confirm_password": new_password,
            "token": token}
    crud.delete_user(db_session=db,
                     user_in=crud_test_user)
    r=client.post(f"{settings.API_HOST}/auth/reset-password",data=data)
    assert r.status_code==401
    assert r.json()["detail"] == "Invalid token"











