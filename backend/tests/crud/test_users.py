import uuid

from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

import backend.crud_db as crud
from backend.core.security import verify_password
from backend.models.models_API import UserCreate, UserUpdatesAPI
from backend.models.models_db import User
from backend.tests.utils.utils import random_email, random_lower_string


def test_create_user(
        db:Session,
        user_create:UserCreate
)->None:
    user=crud.create_user(
        db_session=db,
        user_create=user_create
    )
    assert isinstance(user.user_id,uuid.UUID)
    assert user.email==user_create.email
    assert hasattr(user,"hash_password")

def test_authenticate_valid_user(
        db:Session,
        crud_test_user:User,
        user_create:UserCreate
)->None:
    user_auth=crud.authenticate_user(
        db_session=db,
        email=user_create.email,
        password=user_create.password
    )
    assert user_auth
    assert user_create.email==user_auth.email
    assert user_create.username==user_auth.username

def test_not_authenticate_non_existent_user(db:Session)->None:
    email=random_email()
    password=random_lower_string()
    user= crud.authenticate_user(
        db_session=db,
        email=email,
        password=password
    )
    assert user is None

def test_not_authenticate_wrong_password(db:Session,user_create:UserCreate)->None:
    wrong_password=random_lower_string()
    user_auth=crud.authenticate_user(
        db_session=db,
        email=user_create.email,
        password=wrong_password
    )
    assert user_auth is None

def test_get_user_by_id(db:Session,user_create:UserCreate)->None:
    user=crud.create_user(
        db_session=db,
        user_create=user_create
    )
    user_2= crud.get_user_by_id(
        db_session=db,
        user_id=user.user_id
    )
    assert user_2
    assert user.email==user_2.email
    assert user.username==user_2.username
    assert jsonable_encoder(user) == jsonable_encoder(user_2)

def test_get_user_by_email(db:Session,user_create:UserCreate)->None:
    user=crud.create_user(
        db_session=db,
        user_create=user_create
    )
    user_2=crud.get_user_by_email(
        db_session=db,
        email=user.email
    )
    assert user_2
    assert user.email == user_2.email
    assert user.username == user_2.username
    assert jsonable_encoder(user) == jsonable_encoder(user_2)

def test_update_user_password(db:Session,user_create:UserCreate)->None:
    user=crud.create_user(
        db_session=db,
        user_create=user_create
    )
    new_password=random_lower_string()
    user_in_update=UserUpdatesAPI(password=new_password)
    if user.user_id is not None:
        crud.update_user_password(
            db_session=db,
            user=user,
            user_new_info=user_in_update
        )
    user_2=db.get(User,user.user_id)
    assert user_2
    assert user.email==user_2.email
    verified=verify_password(new_password,user_2.hash_password)
    assert verified






