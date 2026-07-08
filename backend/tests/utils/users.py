from fastapi.testclient import TestClient
from sqlmodel import Session

import backend.crud_db as crud
from backend.core.app_config import settings
from backend.models.models_API import UserCreate, UserUpdatesAPI
from backend.models.models_db import User
from backend.tests.utils.utils import random_email, random_lower_string


def user_authentication_headers(
    *, client: TestClient, email: str, password: str
) -> dict[str, str]:
    data = {"username": email, "password": password}

    r = client.post(f"{settings.API_HOST}/auth/login/access-token", data=data)
    response = r.json()
    auth_token = response["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    return headers

def authentication_data_from_email(
    *,
    client: TestClient,
    email: str,
    db: Session,
) -> dict[str, str]:
    password = random_lower_string()

    user = crud.get_user_by_email(
        db_session=db,
        email=email,
    )

    if not user:
        user_in_create = UserCreate(
            username="TestClient",
            email=email,
            password=password,
        )
        user = crud.create_user(
            db_session=db,
            user_create=user_in_create,
        )
    else:
        user_in_update = UserUpdatesAPI(
            password=password,
        )

        if not user.user_id:
            raise Exception("User id not set")

        crud.update_user_password(
            db_session=db,
            user=user,
            user_new_info=user_in_update,
        )

    headers = user_authentication_headers(
        client=client,
        email=email,
        password=password,
    )

    return {
        "headers": headers,
        "password": password,
        "email": email,
    }


def authentication_token_from_email(
    *,
    client: TestClient,
    email: str,
    db: Session,
) -> dict[str, str]:
    auth_data = authentication_data_from_email(
        client=client,
        email=email,
        db=db,
    )
    return auth_data["headers"]


def create_random_user(db:Session) -> User:
    new_user = UserCreate(
        username=random_lower_string(),
        email=random_email(),
        password=random_lower_string(),
    )
    return crud.create_user(
        db_session=db,
        user_create=new_user,

    )






