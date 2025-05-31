from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Formation IA Backend"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/db" # Changed host to localhost
    JWT_SECRET: str = "YOUR_JWT_SECRET"  # Should be a strong random string
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GEMINI_API_KEY: str = "YOUR_GEMINI_API_KEY"
    BREVO_API_KEY: str = "YOUR_BREVO_API_KEY"
    STRIPE_SECRET_KEY: str = "sk_test_YOUR_STRIPE_SECRET_KEY"
    STRIPE_PUBLISHABLE_KEY: str = "pk_test_YOUR_STRIPE_PUBLISHABLE_KEY"
    STRIPE_WEBHOOK_SECRET: str = "whsec_YOUR_STRIPE_WEBHOOK_SECRET"
    FRONTEND_URL: str = "http://localhost:5173" # Default SvelteKit port

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
