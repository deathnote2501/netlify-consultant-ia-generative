from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from formation_ia_backend.core.config import settings
from formation_ia_backend.infrastructure.api.routers import slides as slides_router
# Import auth routers
from formation_ia_backend.infrastructure.api.routers.auth import (
    auth_router,
    register_router,
    verify_router,
    reset_password_router,
    users_management_router
)
# Import chat router
from formation_ia_backend.infrastructure.api.routers import chat as chat_router

from formation_ia_backend.infrastructure.database.session import AsyncSessionLocal
from formation_ia_backend.application.services.slide_service import SlideService

async def on_startup():
    print("Application starting up...")
    slide_service = SlideService()
    async with AsyncSessionLocal() as session:
        try:
            await slide_service.create_initial_slides(session)
            print("Initial slides check/creation complete.")
        except Exception as e:
            print(f"Error during startup slide creation: {e}")
    print("Startup event finished.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_event_handler("startup", on_startup)

if settings.FRONTEND_URL:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(settings.FRONTEND_URL)],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://localhost:8080", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}

# Mount Slide API router
app.include_router(slides_router.router, prefix=settings.API_V1_STR + "/slides", tags=["Slides"])

# Mount Auth and User Management routers
app.include_router(auth_router, prefix=settings.API_V1_STR + "/auth", tags=["Auth"]) # for /jwt/login, /jwt/logout
app.include_router(register_router, prefix=settings.API_V1_STR + "/auth", tags=["Auth"]) # for /register
app.include_router(verify_router, prefix=settings.API_V1_STR + "/auth", tags=["Auth"]) # for /verify, /request-verify-token
app.include_router(reset_password_router, prefix=settings.API_V1_STR + "/auth", tags=["Auth"]) # for /forgot-password, /reset-password
app.include_router(users_management_router, prefix=settings.API_V1_STR + "/users", tags=["Users"]) # for /me, /{id}

# Mount Chat API router
app.include_router(chat_router.router, prefix=settings.API_V1_STR + "/chat", tags=["Chat"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
