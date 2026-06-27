from fastapi import APIRouter,HTTPException
from typing import Any
from backend.models.models_API import (
UserCreate,
PublicUser,
UserUpdates,
Message,
UpdatePassword,
UserNewRegister,
ProjectAccess
)
import backend.crud_db as crud_db
from backend.core.dependencies import (
SessionDep,
CurrentUser
)
from backend.core.security import verify_password,get_hash_password

router=APIRouter(prefix="/users",tags=["users"])

@router.post("/signup",response_model=PublicUser,status_code=200)
def register_new_user(
        session:SessionDep,
        user_in:UserNewRegister
        )->PublicUser:
    """Create a new user"""
    user=crud_db.get_user_by_email(
        db_session=session,
        email=user_in.email
    )
    if user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists."
        )

    if user_in.password != user_in.repeat_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords don't match."
        )
    user_created=UserCreate.model_validate(user_in)
    user=crud_db.create_user(
        db_session=session,
        user_create=user_created
    )
    return user

@router.patch("/me",response_model=PublicUser,status_code=200)
def update_me(
        *,session:SessionDep,
        user_in:UserUpdates,
        current_user:CurrentUser,
        )->Any:
  if user_in.email:
      existing_user=crud_db.get_user_by_email(
          db_session=session,
          email=user_in.email
      )
      if existing_user:
          raise  HTTPException(
              status_code=409,
              detail="Email already registered."
          )

  user_info=user_in.model_dump(exclude_unset=True)
  current_user.sqlmodel_update(user_info)
  session.add(current_user)
  session.commit()
  return current_user

@router.patch ("/me/password",response_model=Message,status_code=200)
def update_password_me(
        *,session:SessionDep,
        current_user:CurrentUser,
        data_in:UpdatePassword
)->Any:
   verified= verify_password(
       data_in.current_password,
       current_user.hash_password
   )
   if not verified:
       raise HTTPException(
           status_code=400,
           detail="Incorrect password."
       )
   if data_in.new_password == data_in.current_password:
       raise HTTPException(
           status_code=400,
           detail="New password cannot be the same as current one."
       )

   new_hashed_password= get_hash_password(data_in.new_password)
   current_user.hash_password=new_hashed_password
   session.add(current_user)
   session.commit()
   return Message(message="Password was successfully updated.")

@router.delete("/me",status_code=204)
def delete_me(session:SessionDep,current_user:CurrentUser)->None:
    owned_projects= crud_db.get_available_projects_user_role(
        db_session=session,
        user_id=current_user.user_id,
        role=ProjectAccess.owner
    )
    if len(owned_projects)>0:
        raise HTTPException(
            status_code=409,
            detail="User cannot be deleted because they own one or more projects."
        )
    crud_db.delete_user(
        db_session=session,
        user_in=current_user
    )




