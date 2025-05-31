# Formation IA Backend

Backend for the Online Training Application with AI Chat.

## Project Setup

1.  **Prerequisites:**
    *   Python 3.10+
    *   Poetry ([Installation Guide](https://python-poetry.org/docs/#installation))
    *   PostgreSQL server running

2.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd formation_ia_backend
    ```

3.  **Create and configure the environment:**
    *   Copy `.env.example` to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Edit `.env` and fill in your actual database credentials, API keys, and other settings.
        **Important:** Ensure `DATABASE_URL` points to your PostgreSQL database. For example:
        `DATABASE_URL="postgresql+asyncpg://youruser:yourpassword@localhost:5432/formation_ia_db"`

4.  **Install dependencies:**
    ```bash
    poetry install
    ```

5.  **Database Migrations:**
    *   Ensure your PostgreSQL database (specified in `.env`) exists.
    *   Run Alembic migrations:
        ```bash
        poetry run alembic upgrade head
        ```

6.  **Running the application (development):**
    ```bash
    poetry run uvicorn formation_ia_backend.main:app --reload --host 0.0.0.0 --port 8000
    ```
    Alternatively, you can run `python src/formation_ia_backend/main.py` if you prefer, but uvicorn directly is more common for FastAPI.

    The API will be available at `http://localhost:8000`.
    The OpenAPI documentation will be at `http://localhost:8000/api/v1/openapi.json` (or `/docs` if you add the UI).

## API Endpoints

*   `GET /health`: Health check.
*   (More endpoints will be listed here as they are developed)

## Technologies

*   FastAPI
*   SQLAlchemy 2.0 (async) with AsyncPG
*   Alembic for database migrations
*   Pydantic for data validation
*   FastAPI Users for authentication
*   Google Gemini for AI chat
*   Brevo (Sendinblue) for email
*   Stripe for payments
*   Poetry for dependency management
*   Pytest for testing

## Project Structure (Hexagonal Architecture)

*   `src/formation_ia_backend/`: Main application code.
    *   `core/`: Core settings, global exceptions.
    *   `domain/`: Business logic entities, models (SQLAlchemy), schemas (Pydantic).
    *   `application/`: Use cases, application services.
    *   `infrastructure/`: Adapters for external services (DB, AI, email, payment), API routers.
    *   `main.py`: FastAPI application entry point.
*   `tests/`: Unit and integration tests.
*   `alembic.ini`, `src/formation_ia_backend/infrastructure/database/alembic_setup/`: Alembic configuration and migration scripts.
