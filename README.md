# career-platform

Database-driven resume site: FastAPI + PostgreSQL, deployed on Railway.

## Run locally

    docker run -d --name career-pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=career_test -p 54329:5432 postgres:17
    docker exec career-pg-test createdb -U postgres career_dev
    export DATABASE_URL=postgresql://postgres:test@localhost:54329/career_dev
    uv run python -m scripts.init_db
    uv run python -m scripts.seed_resume
    uv run uvicorn app.main:app --reload

`.env.example` lists the variables the app reads; an exported variable wins
over `.env`.

## Test

    docker start career-pg-test
    uv run pytest

Tests wipe the database at `TEST_DATABASE_URL` (default: the local container
above) and refuse to run against any non-local host.
