from fastapi.testclient import TestClient
from sqlmodel import Session
import pytest

import backend.crud_db as crud
from backend.core.app_config import settings
from backend.core.security import verify_password
from backend.models.models_db import User,Project
from backend.models.models_API import UserCreate,ProjectAccess,PublicUser
from backend.tests.utils.users import user_authentication_headers
from backend.tests.utils.utils import random_email, random_lower_string
from backend.tests.utils.projects import create_random_project

def test_register_user(client: TestClient,db:Session)->None:
    username=random_lower_string()
    email=random_email()
    password=random_lower_string()
    data={
        "username":username,
        "email":email,
        "password":password,
        "repeat_password":password,
    }
    r=client.post(f"{settings.API_HOST}/users/signup",json=data)
    assert r.status_code==200
    created_user= PublicUser.model_validate(r.json())
    assert created_user.username==username
    assert created_user.user_id

    user_from_email=crud.get_user_by_email(db_session=db,email=email)
    assert user_from_email
    assert user_from_email.email==email
    assert user_from_email.username==username
    verified=verify_password(password,user_from_email.hash_password)
    assert verified

def test_register_user_already_exists_error(client: TestClient,crud_test_user:User,user_create:UserCreate)->None:
    password=user_create.password
    username=user_create.username
    email=user_create.email

    data={
        "username":username,
        "email":email,
        "password":password,
        "repeat_password":password,
    }
    r=client.post(f"{settings.API_HOST}/users/signup",json=data)
    assert r.status_code==400
    assert r.json()["detail"]=="User with this email already exists."

def test_register_user_wrong_input_passwords_error(client: TestClient,user_create:UserCreate)->None:
        password = user_create.password
        username = user_create.username
        email = user_create.email

        data = {
            "username": username,
            "email": email,
            "password": password,
            "repeat_password": random_lower_string(),
        }
        r = client.post(f"{settings.API_HOST}/users/signup", json=data)
        assert r.status_code == 400
        assert r.json()["detail"] == "Passwords don't match."

def test_update_me (client:TestClient,owner_user_token_headers:dict[str,str],db:Session)->None:
    data={"username":"Updated_username",
          "email": random_email(),
    }
    r=client.patch(f"{settings.API_HOST}/users/me", headers=owner_user_token_headers, json=data)
    assert r.status_code == 200
    user_updated_r= PublicUser.model_validate(r.json())
    assert user_updated_r.username==data["username"]
    assert user_updated_r.user_id

    user_updated=crud.get_user_by_email(db_session=db,email=data["email"])
    assert user_updated
    assert user_updated.username==data["username"]
    assert user_updated.email==data["email"]

def test_update_me_with_email_already_registered_error(client:TestClient,owner_user_token_headers:dict[str,str],crud_test_user:User,db:Session)->None:
    data={"email":crud_test_user.email}
    r = client.patch(f"{settings.API_HOST}/users/me", headers=owner_user_token_headers, json=data)
    assert r.status_code==409
    assert r.json()["detail"]=="Email already registered."

def test_update_me_requires_authentication(client:TestClient):
    response = client.patch(f"{settings.API_HOST}/users/me")
    assert response.status_code == 401

def test_update_password_me(client:TestClient,owner_user_auth_data:dict[str,str],db:Session)->None:
    data={"current_password":owner_user_auth_data["password"],
          "new_password":random_lower_string()}
    r=client.patch(f"{settings.API_HOST}/users/me/password", headers=owner_user_auth_data["headers"], json=data)
    updated_user = crud.get_user_by_email(db_session=db, email=owner_user_auth_data["email"])
    verified=verify_password(data["new_password"],updated_user.hash_password)

    assert r.status_code == 200
    assert updated_user
    assert verified
    assert r.json()["message"]=="Password was successfully updated."

def test_update_password_me_wrong_password(client:TestClient,owner_user_auth_data:dict[str,str])->None:
    data={"current_password":"Wrong Password",
          "new_password":random_lower_string()}
    r = client.patch(f"{settings.API_HOST}/users/me/password", headers=owner_user_auth_data["headers"], json=data)
    assert r.status_code == 400
    assert r.json()["detail"]=="Incorrect password."

def test_update_password_me_same_passwords_error(client:TestClient,owner_user_auth_data:dict[str,str])->None:
    data={"current_password":owner_user_auth_data["password"],
          "new_password":owner_user_auth_data["password"]}
    r = client.patch(f"{settings.API_HOST}/users/me/password", headers=owner_user_auth_data["headers"], json=data)
    assert r.status_code == 400
    assert r.json()["detail"]=="New password cannot be the same as current one."

def test_update_password_me_requires_authentication(client:TestClient)->None:
    r = client.patch(f"{settings.API_HOST}/users/me/password")
    assert r.status_code == 401

def test_delete_me_requires_authentication(client:TestClient)->None:
    r = client.delete(f"{settings.API_HOST}/users/me")
    assert r.status_code == 401

def test_delete_me_as_no_member(client:TestClient,crud_test_user:User,user_create:UserCreate)->None:
    headers=user_authentication_headers(client=client,email=crud_test_user.email,password=user_create.password)
    r=client.delete(f"{settings.API_HOST}/users/me", headers=headers)
    assert r.status_code == 204


@pytest.mark.parametrize(
    "role",
    [r for r in ProjectAccess if r != ProjectAccess.owner]
)
def test_delete_member_removes_project_memberships(db:Session,client:TestClient,crud_test_user:User,role:ProjectAccess,user_create:UserCreate)->None:
    project=create_random_project(db)
    crud.create_project_member(db_session=db,
                               project_id=project.project_id,
                               user_id=crud_test_user.user_id,
                               member_type=role)
    headers=user_authentication_headers(client=client,email=crud_test_user.email,password=user_create.password)
    r=client.delete(f"{settings.API_HOST}/users/me", headers=headers)
    membership=crud.authenticate_project_member(db_session=db,project_id=project.project_id,user_id=crud_test_user.user_id)

    assert r.status_code == 204
    assert membership is None


def test_delete_me_invalid_for_owner(client:TestClient,owner_user_auth_data:dict[str,str],test_user_project:Project)->None:
    r=client.delete(f"{settings.API_HOST}/users/me", headers=owner_user_auth_data["headers"])
    assert r.status_code == 409
    assert r.json()["detail"]=="User cannot be deleted because they own one or more projects."











