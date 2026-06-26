
from datetime import datetime,timezone,timedelta
from sqlmodel import SQLModel
from pwdlib import PasswordHash
import jwt
from backend.core.app_config import settings
from typing import Any
from pwdlib.hashers.argon2 import Argon2Hasher

password_hash= PasswordHash((Argon2Hasher(),))
ALGORITHM = "HS256"

def create_access_token(
        subject:str|Any,
        expires_token_delta:timedelta)->str:
    expire_time=datetime.now(timezone.utc) + expires_token_delta
    encode_content={"exp":expire_time,"sub":str(subject)}
    encoded_jwt=jwt.encode(
        encode_content,
        settings.SECRET_KEY,
        algorithm=ALGORITHM)
    return encoded_jwt

def get_hash_password(password:str)->str:
    return password_hash.hash(password)

def verify_password(plain_password:str, hashed_password:str)->bool:
    return password_hash.verify(plain_password, hashed_password)

class Token(SQLModel):
    access_token: str
    token_type: str="bearer"

class TokenPayload(SQLModel):
    sub: str|None=None




