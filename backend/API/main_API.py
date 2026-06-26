from fastapi import APIRouter
from backend.API import auth,projects,users,documents
from backend.core.app_config import settings

main_api_router = APIRouter()
main_api_router.include_router(auth.router)
main_api_router.include_router(projects.router)
main_api_router.include_router(users.router)
main_api_router.include_router(documents.router)
