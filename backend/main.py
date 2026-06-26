from fastapi import FastAPI
from fastapi.routing import APIRoute
from backend.API.main_API import main_api_router
from backend.core.app_config import settings

def generate_custom_ids_routes(route:APIRoute)->str:
    return f'{route.tags[0]}-{route.name}'

app=FastAPI(
    title=settings.PROJECT_NAME,
    generate_unique_id_function=generate_custom_ids_routes,
)

app.include_router(main_api_router)




