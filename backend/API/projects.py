import uuid
from typing import Annotated
from pydantic import EmailStr
from fastapi.responses import HTMLResponse
from fastapi import (
    UploadFile,
    File,
    Request,
    APIRouter,
    HTTPException,
    status,
    Depends,
    Form,
    Query)
from backend.core.app_config import templates,settings
import backend.crud_db as  crud_db
from backend.core.control_db import (
CurrentUser,
SessionDep,
ActiveProject,
ActiveMember,
is_member,
is_owner,
ProjectOwner)

from backend.models.models_API import (
ProjectAccess,
CreateProject,
UpdateProject,
ProjectPublic,
ProjectPublicInfo,
ProjectsPublic,
BaseDocument,
UploadDocuments,
DocumentPublicByProject,
DocumentsPublic,
Message
)
from backend.utils.email_utils import (
generate_email_token,
generate_invitation_email,
send_email,
verify_email_token
)
import backend.utils.s3_utils as s3_utils


router=APIRouter(tags=["projects"])

@router.post("/projects",
             response_model=ProjectPublicInfo,
             status_code=status.HTTP_201_CREATED)
def generate_project(
        *,session:SessionDep,
        current_user:CurrentUser,
        project_in:CreateProject
        )->ProjectPublicInfo:

    new_project=crud_db.create_project(
        db_session=session,
        new_project=project_in,
        owner_id=current_user.user_id
    )
    return new_project

@router.get(
    "/projects",
    status_code=status.HTTP_200_OK,
)
def get_projects(
    *,session: SessionDep,
    current_user: CurrentUser,
    role: Annotated[
        ProjectAccess | None,
        Query(
            description="Filter projects by user role",
        ),
    ] = None,
)->ProjectsPublic:
    projects = crud_db.get_available_projects_user_role(
        db_session=session,
        user_id=current_user.user_id,
        role=role,
    )

    count = len(projects)

    return ProjectsPublic(
        projects=projects,
        count_projects=count,
    )

@router.get("/project/{project_id}/info",
            response_model=ProjectPublicInfo,
            status_code=status.HTTP_200_OK,
            dependencies=[Depends(is_member)])
def get_project_info(*,project:ActiveProject)->ProjectPublicInfo:
    return project


@router.put("/project/{project_id}/info",
            status_code=status.HTTP_200_OK,
            response_model=ProjectPublicInfo,
            dependencies=[Depends(is_member)])
def update_project_info(
        *,session:SessionDep,
        project:ActiveProject,
        project_in:UpdateProject
        )->ProjectPublicInfo:

    updated_project=crud_db.update_project_details(
        db_session=session,
        original_project=project,
        info_to_update=project_in
    )
    return updated_project


@router.post("/project/{project_id}/documents",
             status_code=status.HTTP_201_CREATED,
             response_model=ProjectPublic)
def upload_new_docs_for_project(
        *,session:SessionDep,
        project:ActiveProject,
        user:ActiveMember,
        files: Annotated[list[UploadFile], File(...)]
        )->ProjectPublic:
    docs=[]
    for file in files:
       s3_key=s3_utils.upload_s3_file_object(
           settings.S3_BUCKET_NAME,
           file,
           project.project_id)
       docs.append(BaseDocument(
           filename=file.filename,
           s3_key=s3_key))

    upload_docs=UploadDocuments(documents=docs)

    crud_db.upload_documents_for_project(
        db_session=session,
        user_id=user.user_id,
        project_id=project.project_id,
        upload_docs=upload_docs
    )
    return project


@router.get("/project/{project_id}/documents",
             response_model=DocumentsPublic,
             status_code=status.HTTP_200_OK,
             dependencies=[Depends(is_member)])
def get_project_docs(project:ActiveProject)->DocumentsPublic:
    public_docs=DocumentsPublic(documents=[DocumentPublicByProject.model_validate(doc) for doc in project.documents])
    return public_docs


@router.delete("/project/{project_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(is_owner)])
def delete_project(*,session:SessionDep,project:ActiveProject)->None:
    crud_db.delete_project(db_session=session, project_in=project)

@router.post("/project/{project_id}/invite",
             status_code=status.HTTP_201_CREATED)
def invite_user_as_participant(
        *,owner:ProjectOwner,
        email:EmailStr=Query(...),
        session:SessionDep,
        project:ActiveProject
        )->Message:

    user_email=crud_db.get_user_by_email(
        db_session=session,
        email=email
    )

    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with provided email does not exist."
        )

    owner_email= crud_db.get_user_by_id(
        db_session=session,
        user_id=owner.user_id
    ).email
    if email==owner_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't invite yourself to a project."
        )

    member=crud_db.authenticate_project_member(
        db_session=session,
        project_id=project.project_id,
        user_id=user_email.user_id
    )
    if member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with provided email is already member of this project: {project.name}."
        )

    crud_db.create_project_member(
        db_session=session,
        project_id=project.project_id,
        user_id=user_email.user_id,
        member_type=ProjectAccess.participant
    )

    return Message(message=f"User {user_email.username} was successfully invited to the project: {project.name}.")


@router.post("/project/{project_id}/share",
             status_code=status.HTTP_201_CREATED,)
def share_project_by_email(
        *,
        email:EmailStr =Query(...),
        session:SessionDep,
        owner:ProjectOwner,
        project:ActiveProject)->Message:

    user_invited=crud_db.get_user_by_email(db_session=session, email=email)
    if not user_invited:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with provided email to share does not exist."
        )

    owner_user = crud_db.get_user_by_id(
        db_session=session,
        user_id=owner.user_id
    )

    owner_email= owner_user.email
    if email==owner_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't share a project with yourself."
        )

    member=crud_db.authenticate_project_member(
        db_session=session,
        project_id=project.project_id,
        user_id=user_invited.user_id
    )
    if member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with provided email is already member of this project: {project.name}."
        )

    payload = {
        "user_invited_id": str(user_invited.user_id),
        "project_id": str(project.project_id),
    }

    invitation_token=generate_email_token(
        payload,
        settings.EMAIL_INVITATION_TOKEN_EXPIRE_HOURS
    )
    email_info=generate_invitation_email(
        owner_user.username,
        user_invited.username,
        invitation_token,
        project
    )
    send_email(
        email_receptor=email,
        subject=email_info.subject,
        html_content=email_info.html_content,
    )
    return Message(message=f"Invitation has been sent to {email}.")


@router.get("/join-project",
            response_class=HTMLResponse)
def get_join_project_form(request:Request,session:SessionDep,token:str):

    payload = verify_email_token(token)
    if not payload:
        raise HTTPException(
            status_code=400,
            detail="Invitation token is invalid."
        )

    user_to_join= crud_db.get_user_by_id(
        db_session=session,
        user_id=uuid.UUID(payload["user_invited_id"])
    )

    owner_user=crud_db.get_project_owner(
        db_session=session,
        project_id=uuid.UUID(payload["project_id"]))

    project=crud_db.get_project_by_id(
        db_session=session,
        project_id=uuid.UUID(payload["project_id"]))

    return templates.TemplateResponse(
         request=request,
         name="forms/invitation_page.html",
         context={
             "app_name":settings.PROJECT_NAME,
             "project_name": project.name,
             "owner_name": owner_user.username,
             "recipient_name": user_to_join.username,
             "token":token
         }
    )


@router.post("/join-project",status_code=status.HTTP_201_CREATED)
def validate_invitation_project(
        session:SessionDep,
        token:str = Form(...),
        email:str = Form(...),
        password:str = Form(...),
        )->Message:

    payload= verify_email_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invitation token is invalid.")

    user_invited= crud_db.get_user_by_id(
        db_session=session,
        user_id=uuid.UUID(payload["user_invited_id"])
    )

    if not user_invited:
        raise HTTPException(
            status_code=401,
            detail="Invitation token is invalid."
        )

    current_user=crud_db.authenticate_user(
        db_session=session,
        email=email,
        password=password
    )

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    if current_user.user_id != user_invited.user_id:
        raise HTTPException(
            status_code=403,
            detail="This invitation is being validated by a different user."
        )

    actual_project= crud_db.get_project_by_id(
        db_session=session,
        project_id=uuid.UUID(payload["project_id"])
    )

    if not actual_project:
        raise HTTPException(status_code=404,
                            detail="Project does not exist."
                            )

    member=crud_db.authenticate_project_member(
        db_session=session,
        project_id=uuid.UUID(payload["project_id"]),
        user_id=user_invited.user_id
    )

    if member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The user is already a participant of the project."
        )

    crud_db.create_project_member(
        db_session=session,
        project_id=uuid.UUID(payload["project_id"]),
        user_id=current_user.user_id,
        member_type=ProjectAccess.participant
    )

    return Message(
        message=f"Welcome {user_invited.username}! You have successfully joined to"
                f" this project as a participant.")






























