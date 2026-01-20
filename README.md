## Trovesuite ERP Core Platform

A comprehensive multi-tenant Enterprise Resource Planning (ERP) platform built with FastAPI, PostgreSQL, and Docker. This platform provides core functionality for user management, role-based access control, group management, authentication, and more.

## 🏗️ Project Architecture

```plaintext
core-platform/
├── app/                    # Main FastAPI application
├── sql/                    # Database schema and migrations
├── func/                   # Azure Functions for serverless operations
├── tests/                  # Unit and integration tests
├── docker-compose.yml      # Local development environment
└── azure-pipelines.yml     # CI/CD pipeline configuration
```

## 🚀 Features

### Core Functionality

*   **Multi-tenant Architecture**: Isolated data per tenant with schema-based separation
*   **Role-Based Access Control (RBAC)**: Fine-grained permission management
*   **Soft Delete**: Data retention with soft delete functionality
*   **Audit Logging**: Comprehensive logging for security and debugging
*   **Health Monitoring**: Application and database health checks
*   **RESTful API**: Clean, documented API endpoints with OpenAPI/Swagger

### Entity Management

The platform provides comprehensive management for the following entities:

*   **👥 Users**: Complete user lifecycle management with authentication
*   **👥 Groups**: Organize users into groups with role assignments
*   **🔐 Auth**: JWT-based authentication and authorization
*   **🏢 Organizations**: Multi-tenant organization management
*   **🎭 Roles**: Role definitions and hierarchy management
*   **🔑 Permissions**: Fine-grained permission system
*   **⚙️ Settings**: System and tenant configuration
*   **📊 Subscriptions**: Subscription and billing management
*   **📅 Attendance**: Time and attendance tracking
*   **📈 Reports**: Analytics and reporting capabilities
*   **📱 Apps**: Application marketplace and integration
*   **🏠 Landing Page**: Public-facing authentication pages

## 📋 Prerequisites

### Required Software

*   **Python 3.12+** (3.13 recommended)
*   **PostgreSQL 17+** (managed via Docker)
*   **Docker & Docker Compose** - For containerized services
*   **Poetry** - Python dependency management (auto-installed by script)
*   **Git** - Version control

### Optional (for advanced features)

*   **Azure CLI** - For ACR push (Option 2 in setup script)
*   **Azure Functions Core Tools** - For serverless functions
*   **Make** - For running makefile commands

### System Requirements

*   **Operating System**: macOS, Linux, or Windows (WSL2 recommended)
*   **RAM**: Minimum 4GB, recommended 8GB+
*   **Disk Space**: Minimum 5GB for Docker images and dependencies
*   **Network**: Internet connection for downloading dependencies

## 🛠️ Quick Start

### 1\. Clone the Repository

```plaintext
git clone <repository-url>
cd core-platform
```

### 2\. Set Up Environment Variables

Create a `.env` file in the `app/` directory:

```plaintext
# Database Configuration
DB_HOST=localhost
DB_PORT=5431
DB_NAME=erpdb
DB_USER=user
DB_PASSWORD=password

# Application Configuration
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=your-secret-key-here

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Queue Configuration (for Azure Functions)
SIGNUP_CREATE_SCHEMA_AND_TABLE=on-signup-create-schema-and-tables
```

### 3\. Setup Application (Recommended)

We provide an automated setup script that handles everything for you:

```plaintext
# Make the script executable
chmod +x script_app_setup.sh

# Run the setup script
./script_app_setup.sh
```

The script provides an interactive menu with the following options:

**Option 1: Setup local resources (without running app)**

*   Starts Docker services (PostgreSQL, Redis)
*   Sets up Poetry environment
*   Executes SQL initialization scripts
*   Does NOT start the application

**Option 2: Dockerize Backend and push to ACR**

*   Builds Docker image for the application
*   Pushes to Azure Container Registry
*   Supports multi-platform builds (ARM64 and AMD64)

**Option 3: Start app locally (full setup)**

*   Performs full environment setup
*   Starts all dependencies
*   Starts the FastAPI application with auto-reload

**Option 4: Start app with Poetry (development)**

*   Quick start for daily development
*   Assumes dependencies are already running
*   Starts only the FastAPI application

**Option 5: Destroy local resources**

*   Stops and removes all Docker containers
*   Removes Docker volumes
*   Cleans up Poetry virtual environment

**Option 6: Reset database and restart**

*   Stops database container
*   Removes database volumes
*   Restarts with fresh database
*   Re-initializes schema and data

**Option 7: Test environment variables**

*   Displays all loaded environment variables
*   Useful for debugging configuration issues

**Option 8: Show help and usage information**

*   Displays detailed help message

### 4\. Manual Setup (Alternative)

If you prefer to set up manually:

```plaintext
# Start services with Docker Compose
docker-compose up -d

# Install dependencies
cd app
poetry install

# Run the application
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

This will start:

*   PostgreSQL database (port 5431)
*   Redis server (port 6380)
*   FastAPI application (port 8000)

### 5\. Access the Application

*   **API Documentation**: http://localhost:8000/docs
*   **ReDoc Documentation**: http://localhost:8000/redoc
*   **Health Check**: http://localhost:8000/health
*   **Database Health**: http://localhost:8000/health/db

## 📁 Project Structure

### Application (`app/`)

Contains the main FastAPI application with:

*   **Entities**: Domain models and business logic (users, groups, roles, etc.)
*   **Controllers**: API endpoints and request handling
*   **Services**: Business logic and data processing
*   **DTOs**: Data Transfer Objects for request/response
*   **Middleware**: Logging, security, and exception handling
*   **Configurations**: Database, logging, and settings

### Database (`sql/`)

Contains SQL scripts for:

*   **Schema Creation**: Tables, indexes, and constraints
*   **Triggers**: Automated database operations
*   **Seed Data**: Initial data for development
*   **Multi-tenant Setup**: Tenant schema creation

### Azure Functions (`func/`)

Serverless functions for:

*   Background job processing
*   Event-driven operations
*   Scheduled tasks

### Tests (`tests/`)

Comprehensive test suite with:

*   **Unit Tests**: Individual component testing
*   **Integration Tests**: End-to-end API testing
*   **Test Fixtures**: Shared test data and mocks

## 🔧 Development

### Install Dependencies

```plaintext
cd app
poetry install
```

### Run Application Locally

```plaintext
cd app
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests

```plaintext
cd app
poetry run pytest ../tests/ -v
```

### Run Tests with Coverage

```plaintext
cd app
poetry run pytest ../tests/ --cov=src --cov-report=html
```

### Code Formatting

```plaintext
cd app
poetry run black src/
```

## 🗄️ Database Management

### Initialize Database

```plaintext
# Using Docker Compose (automatic)
docker-compose up -d db

# Or manually
psql -h localhost -p 5431 -U user -d erpdb -f sql/main/tables.sql
psql -h localhost -p 5431 -U user -d erpdb -f sql/main/index.sql
psql -h localhost -p 5431 -U user -d erpdb -f sql/main/triggers.sql
psql -h localhost -p 5431 -U user -d erpdb -f sql/main/insert.sql
```

### Create New Tenant

```plaintext
psql -h localhost -p 5431 -U user -d erpdb -f sql/tenant/tables.sql
```

## 🚢 Deployment

### Docker Build

```plaintext
cd app
docker build -t core-platform:latest .
```

### Azure DevOps Pipeline

The project includes automated CI/CD pipeline configuration:

*   **Build Stage**: Docker image build and push to ACR
*   **Deploy Stage**: Application deployment to Azure App Service
*   **Environment-based**: Separate configurations for dev and prod

### Manual Deployment

```plaintext
# Build production image
docker build -f app/Dockerfile.nonprod -t core-platform:prod ./app

# Run container
docker run -d -p 8000:8000 --env-file app/.env core-platform:prod
```

## 🔐 Security Features

*   **JWT Authentication**: Secure token-based authentication
*   **Password Hashing**: bcrypt with salt rounds
*   **CORS Protection**: Configurable cross-origin resource sharing
*   **Input Validation**: Pydantic models for request validation
*   **SQL Injection Prevention**: Parameterized queries
*   **Security Logging**: Comprehensive audit trails
*   **Soft Delete**: Data retention for compliance

## 📊 API Endpoints

The platform provides comprehensive REST API endpoints organized by entity. All endpoints (except health checks) are prefixed with `/api/v1`.

### Health Check

*   `GET /health` - Application and database health status
*   `GET /health/db` - Database-specific health check

### 🏠 Landing Page & Authentication (`/api/v1`)

#### User Registration & Login

*   `POST /api/v1/signup` - User registration with email and password
*   `POST /api/v1/login` - User login with credentials

### 👥 Users Management (`/api/v1/users`)

#### User CRUD Operations

*   `POST /api/v1/users/add_user` - Create new user
*   `GET /api/v1/users/get_user` - Get user by ID
*   `GET /api/v1/users/get_users` - List all users with pagination
*   `PUT /api/v1/users/update_user` - Update user information
*   `DELETE /api/v1/users/delete_user` - Soft delete user

#### User Access & Permissions

*   `POST /api/v1/users/assign_roles_to_user` - Assign roles to a user
*   `POST /api/v1/users/grant_user_access` - Grant user access to resources
*   `POST /api/v1/users/groups/add_user_to_groups` - Add user to groups
*   `POST /api/v1/users/groups/remove_user_from_groups` - Remove user from groups
*   `POST /api/v1/users/roles/remove_roles_from_user` - Remove roles from user

### 👥 Groups Management (`/api/v1/groups`)

#### Group CRUD Operations

*   `POST /api/v1/groups/create_group` - Create new group
*   `GET /api/v1/groups/get_group_by_id` - Get group by ID
*   `GET /api/v1/groups/get_all_groups` - List all groups with pagination
*   `PUT /api/v1/groups/update_group` - Update group information
*   `DELETE /api/v1/groups/delete_group` - Soft delete group

#### Group Permissions

*   `POST /api/v1/groups/assign_roles_to_group` - Assign roles to a group

### 🔐 Authorization (`/api/v1/auth`)

#### Permission Checking

*   `POST /api/v1/auth/authorize` - Check user permissions for actions

### 🏢 Entities Available (Future Endpoints)

The platform includes the following entities that can be extended with additional endpoints:

#### Organizations (`/api/v1/organizations`)

*   Organization management and multi-tenancy support
*   Tenant configuration and settings

#### Roles (`/api/v1/roles`)

*   Role definitions and management
*   Role hierarchy and inheritance

#### Permissions (`/api/v1/permissions`)

*   Permission definitions
*   Permission-resource mapping

#### Settings (`/api/v1/settings`)

*   System-wide configuration
*   Tenant-specific settings

#### Subscriptions (`/api/v1/subscriptions`)

*   Subscription management
*   Plan and billing integration

#### Attendance (`/api/v1/attendance`)

*   Attendance tracking
*   Time and attendance records

#### Reports (`/api/v1/reports`)

*   Report generation
*   Analytics and insights

#### Apps (`/api/v1/apps`)

*   Application management
*   App marketplace integration

### 📝 API Documentation

For detailed API documentation with request/response schemas, visit:

*   **Swagger UI**: http://localhost:8000/docs
*   **ReDoc**: http://localhost:8000/redoc

### 🔑 Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```plaintext
Authorization: Bearer <your-jwt-token>
```

### 📋 Common Response Format

All API responses follow a consistent format:

```plaintext
{
  "detail": "Success message",
  "data": [...],
  "success": true,
  "status_code": 200,
  "error": null,
  "pagination": {
    "page": 1,
    "size": 10,
    "total": 100,
    "has_next": true
  }
}
```

## 📝 Logging

Application logs are stored in `app/logs/`:

*   `app.log` - General application logs
*   `debug.log` - Debug level logs
*   `error.log` - Error and exception logs

Log levels are configurable via environment variables.

## 🤝 Contributing

1.  Create a feature branch from `dev`
2.  Make your changes
3.  Write/update tests
4.  Ensure all tests pass
5.  Submit a pull request

## 📄 License

Proprietary - Trovesuite ERP Platform

## 👥 Authors

*   **Bright Debrah Owusu** - owusu.debrah@deladetech.com

## 📞 Support

For issues and questions:

*   Check the API documentation at `/docs`
*   Review test cases for usage examples
*   Contact the development team

## 🔄 Version History

*   **v1.0.0** - Initial release
    *   Multi-tenant architecture
    *   User and group management
    *   Role-based access control
    *   Authentication system
    *   Health monitoring