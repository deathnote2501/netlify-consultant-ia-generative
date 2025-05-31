from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from formation_ia_backend.core.config import settings
# Import routers here later
# from formation_ia_backend.infrastructure.api.routers import slides_router # Example

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
if settings.FRONTEND_URL:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(settings.FRONTEND_URL)], # Can be a list of origins
        allow_credentials=True,
        allow_methods=["*"], # Allows all methods
        allow_headers=["*"], # Allows all headers
    )
else:
    # Fallback for local development if FRONTEND_URL is not set
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://localhost:8080", "http://localhost:5173"], # Common local dev ports
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}

# Mount API routers
# app.include_router(slides_router, prefix=settings.API_V1_STR, tags=["Slides"]) # Example

# Add startup event for initial data seeding (e.g. slides) later
# @app.on_event("startup")
# async def startup_event():
#     pass

if __name__ == "__main__":
    import uvicorn
    # This is for local development running `python src/formation_ia_backend/main.py`
    # For production, use a proper ASGI server like Uvicorn or Hypercorn directly
    # Example: uvicorn formation_ia_backend.main:app --host 0.0.0.0 --port 8000 --reload
    uvicorn.run(app, host="0.0.0.0", port=8000)
