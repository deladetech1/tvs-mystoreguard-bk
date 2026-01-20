# Core Platform Application

FastAPI-based REST API application for the Trovesuite ERP Core Platform. This application provides comprehensive backend services for multi-tenant enterprise resource planning.

## 📁 Directory Structure

```
app/
├── src/
│   ├── configs/           # Configuration modules
│   │   ├── database.py    # Database connection and management
│   │   ├── logging.py     # Logging configuration
│   │   └── settings.py    # Application settings
│   │
│   ├── entities/          # Domain entities and business logic
│   │   ├── auth/         # Authentication & authorization
│   │   ├── users/        # User management
│   │   ├── groups/       # Group management
│   │   ├── roles/        # Role management
│   │   ├── permissions/  # Permission management
│   │   ├── organizations/# Organization management
│   │   ├── subscriptions/# Subscription management
│   │   ├── attendance/   # Attendance tracking
│   │   ├── settings/     # System settings
│   │   ├── reports/      # Reporting functionality
│   │   ├── apps/         # Application management
│   │   ├── landingpage/  # Public landing page features
│   │   └── shared/       # Shared utilities and health checks
│   │
│   ├── middleware/        # Request/response middleware
│   │   ├── logging_middleware.py    # Request logging
│   │   └── exception_handler.py     # Global exception handling
│   │
│   └── utils/             # Utility functions
│       ├── auth.py        # Authentication utilities
│       ├── helper.py      # General helper functions
│       └── logging_utils.py # Logging utilities
│
├── logs/                  # Application logs
├── main.py               # FastAPI application entry point
├── pyproject.toml        # Poetry dependencies
├── Dockerfile            # Production Docker image
├── Dockerfile.nonprod    # Non-production Docker image
└── script.sh             # Deployment scripts
```

## 🏗️ Architecture Pattern

The application follows a **layered architecture** pattern:

```
Controller Layer (API Endpoints)
    ↓
Service Layer (Business Logic)
    ↓
Data Access Layer (Database Operations)
```

### Entity Structure

Each entity follows a consistent structure:

- **`*_base.py`**: Base Pydantic models with common fields
- **`*_controller.py`**: FastAPI route handlers and endpoints
- **`*_service.py`**: Business logic and data processing
- **`*_write_dto.py`**: Data Transfer Objects for requests
- **`*_read_dto.py`**: Data Transfer Objects for responses

## 🚀 Getting Started

### Prerequisites

- Python 3.12+ (3.13 recommended)
- Poetry for dependency management
- PostgreSQL 17+
- Redis (optional, for caching)

### Installation

1. **Install Poetry** (if not already installed):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. **Install Dependencies**:
```bash
cd app
poetry install
```

3. **Set Up Environment Variables**:
Create a `.env` file in the `app/` directory:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5431
DB_NAME=erpdb
DB_USER=user
DB_PASSWORD=password

# Application Settings
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS Settings
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log
```

### Running the Application

#### Development Mode (with hot reload):
```bash
cd app
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Mode (with Gunicorn):
```bash
cd app
poetry run gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### Using Docker:
```bash
# Build image
docker build -t core-platform-app .

# Run container
docker run -d -p 8000:8000 --env-file .env core-platform-app
```

## 📊 API Documentation

Once the application is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔧 Configuration

### Database Configuration (`src/configs/database.py`)

The `DatabaseManager` class handles all database operations:

```python
from src.configs.database import DatabaseManager

# Execute a query
result = DatabaseManager.execute_query(
    "SELECT * FROM users WHERE id = %s",
    (user_id,)
)

# Execute an update
rows_affected = DatabaseManager.execute_update(
    "UPDATE users SET email = %s WHERE id = %s",
    (new_email, user_id)
)

# Execute a scalar query
count = DatabaseManager.execute_scalar(
    "SELECT COUNT(*) FROM users"
)
```

### Logging Configuration (`src/configs/logging.py`)

Centralized logging with multiple log levels:

```python
from src.configs.logging import get_logger

logger = get_logger(__name__)
logger.info("Application started")
logger.error("An error occurred", exc_info=True)
```

Log files are stored in `logs/`:
- `app.log` - General logs
- `debug.log` - Debug information
- `error.log` - Errors and exceptions

### Settings (`src/configs/settings.py`)

Application settings loaded from environment variables:

```python
from src.configs.settings import settings

print(settings.db_host)
print(settings.secret_key)
print(settings.environment)
```

## 🧪 Testing

### Run All Tests

```bash
cd app
poetry run pytest ../tests/ -v
```

### Run Specific Test Suite

```bash
# Unit tests only
poetry run pytest ../tests/*/unittest/ -v

# Integration tests only
poetry run pytest ../tests/*/integration/ -v

# Specific entity tests
poetry run pytest ../tests/groups/ -v
poetry run pytest ../tests/users/ -v
```

### Run Tests with Coverage

```bash
poetry run pytest ../tests/ --cov=src --cov-report=html
```

Coverage report will be generated in `htmlcov/index.html`

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures and configuration
├── groups/
│   ├── unittest/        # Unit tests for groups
│   └── integration/     # Integration tests for groups
├── users/
│   ├── unittest/        # Unit tests for users
│   └── integration/     # Integration tests for users
└── shared/
    ├── unittest/        # Unit tests for shared utilities
    └── integration/     # Integration tests
```

## 🔐 Authentication & Authorization

The application uses JWT-based authentication with the `trovesuite-auth-service` package.

### Authentication Flow

1. User logs in with credentials
2. System validates credentials
3. JWT token is generated and returned
4. Token is included in subsequent requests
5. Middleware validates token and extracts user info

### Permission Checking

```python
from src.entities.auth.auth_service import AuthService

# Check if user has permission
is_authorized = AuthService.check_permission(
    users_data=current_user.data,
    action="permission-group-create"
)

if not is_authorized:
    raise HTTPException(status_code=403, detail="Unauthorized")
```

## 🗄️ Database Operations

### Using DatabaseManager

```python
from src.configs.database import DatabaseManager
from src.configs.settings import db_settings

# Query with parameters
users = DatabaseManager.execute_query(
    f'SELECT * FROM "{tenant_id}".{db_settings.MAIN_USERS_TABLE} WHERE is_active = %s',
    (True,)
)

# Update with parameters
rows_updated = DatabaseManager.execute_update(
    f'UPDATE "{tenant_id}".{db_settings.MAIN_USERS_TABLE} SET email = %s WHERE id = %s',
    (new_email, user_id)
)

# Get scalar value
user_count = DatabaseManager.execute_scalar(
    f'SELECT COUNT(*) FROM "{tenant_id}".{db_settings.MAIN_USERS_TABLE}'
)
```

## 📝 Creating New Entities

To add a new entity to the application:

1. **Create Base Model** (`src/entities/entity_name/entity_base.py`):
```python
from pydantic import BaseModel

class EntityBase(BaseModel):
    name: str
    description: Optional[str] = None
```

2. **Create Write DTOs** (`src/entities/entity_name/entity_write_dto.py`):
```python
class CreateEntityServiceWriteDto(EntityBase):
    pass

class CreateEntityControllerWriteDto(EntityBase):
    pass
```

3. **Create Read DTOs** (`src/entities/entity_name/entity_read_dto.py`):
```python
class GetEntityServiceReadDto(EntityBase):
    id: str
    tenant_id: str
    cdatetime: str
```

4. **Create Service** (`src/entities/entity_name/entity_service.py`):
```python
class EntityService:
    @staticmethod
    def create_entity(data, tenant_id, user_id):
        # Business logic here
        pass
```

5. **Create Controller** (`src/entities/entity_name/entity_controller.py`):
```python
from fastapi import APIRouter
from fastapi import Depends

entity_router = APIRouter()

@entity_router.post("/create")
def create_entity(
    data: CreateEntityControllerWriteDto,
    current_user: dict = Depends(CustomAuthService.get_current_user)
):
    # Controller logic here
    pass
```

6. **Register Router** in `main.py`:
```python
from src.entities.entity_name.entity_controller import entity_router

app.include_router(prefix="/api/v1", router=entity_router)
```

## 🐳 Docker

### Building Docker Image

```bash
# Production build
docker build -t core-platform-app:latest .

# Non-production build
docker build -f Dockerfile.nonprod -t core-platform-app:dev .
```

### Running with Docker Compose

```bash
# From project root
docker-compose up -d app
```

### Dockerfile Features

- Multi-stage builds for optimized image size
- Python 3.13 base image
- Poetry for dependency management
- Non-root user for security
- Health checks
- Graceful shutdown handling

## 📊 Monitoring & Logging

### Health Check Endpoint

```bash
curl http://localhost:8000/health
```

Returns:
```json
{
  "success": true,
  "data": {
    "application": "healthy",
    "database": "healthy",
    "database_version": "PostgreSQL 17.5"
  }
}
```

### Logging Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical errors requiring immediate attention

### Log Rotation

Logs are automatically rotated based on size and age. Configure in `src/configs/logging.py`.

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check database credentials in `.env`
   - Ensure PostgreSQL is running
   - Verify network connectivity

2. **Import Errors**
   - Run `poetry install` to install dependencies
   - Activate virtual environment: `poetry shell`

3. **Port Already in Use**
   - Change port in uvicorn command: `--port 8001`
   - Kill process using the port: `lsof -ti:8000 | xargs kill`

4. **Module Not Found**
   - Ensure you're running from the correct directory
   - Check Python path configuration

## 📚 Dependencies

Key dependencies:
- **FastAPI**: Modern web framework
- **Pydantic**: Data validation
- **psycopg2**: PostgreSQL driver
- **python-jose**: JWT handling
- **passlib**: Password hashing
- **uvicorn**: ASGI server
- **gunicorn**: Production WSGI server

See `pyproject.toml` for complete dependency list.

## 🤝 Contributing

1. Follow the existing code structure
2. Write tests for new features
3. Update documentation
4. Ensure all tests pass
5. Follow PEP 8 style guidelines

## 📄 License

Proprietary - Trovesuite ERP Platform


