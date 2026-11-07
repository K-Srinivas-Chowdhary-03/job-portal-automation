from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.companies import router as companies_router
from app.api.v1.categories import router as categories_router
from app.api.v1.users import router as users_router
from app.api.v1.admin import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs (Public)"])
api_router.include_router(companies_router, prefix="/companies", tags=["Companies"])
api_router.include_router(categories_router, prefix="/categories", tags=["Categories"])
api_router.include_router(users_router, tags=["User Activity"])
api_router.include_router(admin_router, prefix="/admin", tags=["Administration"])
