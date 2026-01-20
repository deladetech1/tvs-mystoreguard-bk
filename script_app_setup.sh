#!/bin/bash

# =============================================================================
# 🚀 Core Platform Development Script (v2.1.0)
# =============================================================================
# Author: Core Platform Team
# Description: Dev & deployment automation for FastAPI Core Platform app.
# =============================================================================

set -e  # Exit immediately on failure

# -----------------------------------------------------------------------------
# 📂 DIRECTORY SETUP
# -----------------------------------------------------------------------------
ORIGINAL_DIR="$(cd "$(dirname "$0")" && pwd)"
MAIN_APP_DIR="app"
FUNC_APP_DIR="func"

# -----------------------------------------------------------------------------
# 🎨 PRINT FUNCTIONS
# -----------------------------------------------------------------------------
print_header() { echo -e "\n==============================================================================\n🚀 $1\n==============================================================================\n"; }
print_success() { echo "✅ $1"; }
print_error() { echo "❌ $1"; }
print_warning() { echo "⚠️  $1"; }
print_info() { echo "ℹ️  $1"; }

# ----------------------------------------------------------------------------
# ⚙️ LOAD ENV VARIABLES
# ----------------------------------------------------------------------------
load_env_variables() {
  local env_file="${MAIN_APP_DIR}/.env"
  if [ -f "$env_file" ]; then
    print_info "Loading environment variables from ${env_file}..."
    set -a
    . "$env_file" 2>/dev/null || true
    set +a
    print_success "Environment variables loaded successfully"
  else
    print_warning "No environment file found at ${env_file}. Using defaults."
  fi
}

# -----------------------------------------------------------------------------
# 🧩 HELPER FUNCTIONS
# -----------------------------------------------------------------------------
check_poetry_installation() {
  if ! command -v poetry &>/dev/null; then
    print_info "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
    print_success "Poetry installed successfully"
  else
    print_success "Poetry already installed"
  fi
}

ensure_correct_directory() {
  if [ ! -f "script_app_setup.sh" ]; then
    print_error "Please run this script from the core-platform directory."
    exit 1
  fi
}

check_app_directory() {
  if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found in app directory!"
    exit 1
  fi
}

# -----------------------------------------------------------------------------
# 🧱 DATABASE UTILITIES
# -----------------------------------------------------------------------------
get_db_container() {
  docker ps --filter "name=db" --format "{{.Names}}" | head -n 1
}

wait_for_db() {
  print_info "Checking database readiness..."
  local db_container
  db_container=$(get_db_container)
  if [ -z "$db_container" ]; then
    print_error "Database container not found. Ensure docker-compose is running."
    return 1
  fi

  local max_attempts=30
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    local status
    status=$(docker inspect -f '{{.State.Health.Status}}' "$db_container" 2>/dev/null || echo "starting")
    if [ "$status" = "healthy" ]; then
      print_success "Database is healthy and ready"
      return 0
    fi

    if docker exec "$db_container" psql -U "${DB_USER:-user}" -d "${DB_NAME:-erpdb}" -c "SELECT 1;" >/dev/null 2>&1; then
      print_success "Database connection established"
      return 0
    fi

    print_info "Waiting for database... (attempt $attempt/$max_attempts)"
    sleep 2
    ((attempt++))
  done

  print_error "Database failed to start within expected time"
  docker logs "$db_container" || true
  return 1
}

execute_sql_files() {
  print_info "Executing SQL files..."
  local db_container
  db_container=$(get_db_container)
  if [ -z "$db_container" ]; then
    print_error "No running database container found."
    return 1
  fi

  local sql_dir="sql/main"
  if [ ! -d "$sql_dir" ]; then
    print_warning "SQL directory not found: $sql_dir"
    return 1
  fi

  local sql_order=("tables.sql" "triggers.sql" "insert.sql")
  local sql_files=()

  for sql_file in "${sql_order[@]}"; do
    [ -f "$sql_dir/$sql_file" ] && sql_files+=("$sql_file")
  done

  local additional_files
  additional_files=$(find "$sql_dir" -name "*.sql" -type f | sed "s|^$sql_dir/||" | grep -v -E "^(tables|triggers|insert)\.sql$" || true)
  for f in $additional_files; do sql_files+=("$f"); done

  if [ ${#sql_files[@]} -eq 0 ]; then
    print_warning "No SQL files found in $sql_dir"
    return 0
  fi

  print_info "Executing SQL scripts in order:"
  for sql_file in "${sql_files[@]}"; do
    print_info "  - $sql_file"
    # Capture output to show errors if they occur
    local sql_output
    sql_output=$(docker exec -i "$db_container" psql -U "${DB_USER:-user}" -d "${DB_NAME:-erpdb}" <"$sql_dir/$sql_file" 2>&1)
    local sql_exit_code=$?
    
    if [ $sql_exit_code -eq 0 ]; then
      print_success "Executed: $sql_file"
    else
      print_error "Failed to execute: $sql_file"
      echo "$sql_output" | grep -i "error\|warning\|notice" | head -20 || echo "$sql_output"
      return 1
    fi
  done

  print_success "All SQL scripts executed successfully"
  print_info "Note: Triggers will automatically assign permissions to roles when they are inserted"
}

# -----------------------------------------------------------------------------
# 🛠️ SETUP FUNCTIONS
# -----------------------------------------------------------------------------
setup_poetry_environment() {
  print_info "Setting up Poetry environment..."
  cd "$MAIN_APP_DIR"
  check_app_directory
  poetry config virtualenvs.in-project true

  print_info "Clearing Poetry cache..."
  poetry cache clear pypi --all -n 2>/dev/null || true
  print_success "Poetry cache cleared"

  poetry install
  print_success "Poetry environment ready"
  cd "$ORIGINAL_DIR"
}

setup_local_resources() {
  print_header "Setting Up Local Resources"
  print_info "Tearing down any running containers..."
  docker-compose down

  print_info "Removing existing database volume..."
  docker volume rm core-platform_postgresql_data 2>/dev/null || true

  print_info "Starting services..."
  docker-compose up -d
  print_success "Docker services started"

  wait_for_db || exit 1

  print_info "Checking Redis connection..."
  local redis_container
  redis_container=$(docker ps --filter "name=redis" --format "{{.Names}}" | head -n 1)
  if docker exec "$redis_container" redis-cli ping >/dev/null 2>&1; then
    print_success "Redis is ready"
  else
    print_warning "Redis connection failed"
  fi

  check_poetry_installation
  setup_poetry_environment
  execute_sql_files

  print_success "✅ Local resources setup complete"
  print_info "Services running:"
  print_info "  - PostgreSQL: localhost:5431"
  print_info "  - Redis: localhost:6379"
  print_info "  - Poetry environment: Ready"
}

# -----------------------------------------------------------------------------
# 🧰 OTHER ACTIONS
# -----------------------------------------------------------------------------
destroy_local_resources() {
  print_header "Destroying Local Resources"

  # 🧱 Stop and remove containers, networks, and volumes from docker-compose
  print_info "Stopping and removing docker-compose services (including networks and volumes)..."
  docker-compose down -v --remove-orphans || true

  # 🧹 Remove any dangling (unused) Docker volumes
  print_info "Removing all unused Docker volumes..."
  docker volume prune -f || true

  # 🧹 Optionally remove specific volumes (if you want to target by name)
  print_info "Removing project-specific volumes..."
  docker volume rm core-platform_postgresql_data 2>/dev/null || true

  # 🧰 Remove Poetry virtual environment if it exists
  if [ -d "$MAIN_APP_DIR" ]; then
    cd "$MAIN_APP_DIR"
    poetry env remove --all 2>/dev/null || true
    cd "$ORIGINAL_DIR"
  fi

  print_success "✅ All local Docker containers, volumes, and environments removed successfully"
}

get_uvicorn_command() {
  cd "$MAIN_APP_DIR"
  local python_version
  python_version=$(poetry run python --version | awk '{print $2}')
  local major minor
  major=$(echo $python_version | cut -d'.' -f1)
  minor=$(echo $python_version | cut -d'.' -f2)

  if [ "$major" -eq 3 ] && [ "$minor" -ge 13 ]; then
    echo "poetry run uvicorn main:app --reload --reload-dir . --host 0.0.0.0 --port 8000 --log-level info"
  else
    echo "poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info"
  fi
  cd "$ORIGINAL_DIR"
}

start_app_development() {
  print_header "Starting App (Development Mode)"

  local port="${APP_PORT:-8000}"
  local uvicorn_cmd

  # 🔍 Check if port is in use BEFORE cd
  if lsof -i tcp:$port >/dev/null 2>&1; then
    print_warning "Port $port is currently in use."
    
    # Get all PIDs using the port
    local pids
    pids=$(lsof -ti tcp:$port)

    if [ -n "$pids" ]; then
      print_info "Killing process(es) using port $port: $pids"
      # Kill each PID safely
      for pid in $pids; do
        kill -9 "$pid" >/dev/null 2>&1 && print_success "Killed process $pid on port $port"
      done
      sleep 1  # Give OS a moment to release the port
    else
      print_warning "Could not determine process IDs for port $port"
    fi
  else
    print_info "Port $port is free. Starting app..."
  fi

  # 📂 Change to app directory safely
  if [ ! -d "$MAIN_APP_DIR" ]; then
    print_error "Directory '$MAIN_APP_DIR' not found! Please ensure your app folder exists."
    exit 1
  fi

  cd "$MAIN_APP_DIR"

  uvicorn_cmd=$(get_uvicorn_command)
  print_info "Starting FastAPI on port $port..."
  eval "$uvicorn_cmd"
}

# -----------------------------------------------------------------------------
# 🧭 MAIN MENU
# -----------------------------------------------------------------------------
show_menu() {
  print_header "Core Platform Development Menu"
  echo "1. 🚀 Setup local resources"
  echo "2. 🧹 Destroy local resources"
  echo "3. 🧱 Start app (development)"
  echo "4. ❓ Show help"
  echo ""
  read -p "Enter your choice (1-4): " CHOICE
}

show_help() {
  print_header "Help"
  echo "1. Setup local resources — Starts PostgreSQL, Redis, installs dependencies, runs SQL."
  echo "2. Destroy local resources — Stops containers, removes volumes and envs."
  echo "3. Start app (development) — Runs FastAPI with Poetry and Uvicorn."
}

# -----------------------------------------------------------------------------
# 🚀 MAIN EXECUTION
# -----------------------------------------------------------------------------
main() {
  ensure_correct_directory
  load_env_variables
  show_menu

  case "$CHOICE" in
    1) setup_local_resources ;;
    2) destroy_local_resources ;;
    3) start_app_development ;;
    4) show_help ;;
    *) print_error "Invalid choice. Please select 1–4." ;;
  esac
}

main
