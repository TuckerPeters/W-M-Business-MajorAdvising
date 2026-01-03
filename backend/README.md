# W&M Business Major Advising - Backend

Python backend for fetching and managing W&M course catalog data from the FOSE API.

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `CONTACT_EMAIL` | Email for API User-Agent header |
| `FIREBASE_PROJECT_ID` | Firebase project ID |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to service account JSON |
| `REDIS_URL` | Redis connection URL (optional) |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `GET /api/term` | Current semester info |
| `GET /api/courses` | List courses (paginated) |
| `GET /api/courses/{code}` | Get single course |
| `GET /api/courses/search?q=` | Search courses |
| `GET /api/subjects` | List all subjects |

## Project Structure

```
backend/
├── api/          # FOSE API client & course fetcher
├── core/         # Config, semester logic, shared utils
├── services/     # Firebase, Redis cache, enrollment
├── scrapers/     # Curriculum PDF parser
├── tasks/        # Scheduler & database scripts
└── tests/        # Unit, E2E, integration tests
```

## Scripts

```bash
python server.py                    # Run server
python -m tasks.populate            # Populate database
python -m tasks.scheduler           # Run background scheduler
pytest tests/unit tests/e2e -v      # Run tests
```
