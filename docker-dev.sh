#!/bin/bash

# Docker helper script for QR Registros development environment
# Usage: ./docker-dev.sh [command] [service]
# Example: ./docker-dev.sh start
#          ./docker-dev.sh logs app
#          ./docker-dev.sh test

set -e

COMPOSE_FILE="docker-compose.dev.yml"
COMPOSE_CMD="docker-compose -f $COMPOSE_FILE"
COMMAND=${1:-help}
SERVICE=${2:-app}

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${CYAN}=== $1 ===${NC}"
}

function print_ok() {
    echo -e "${GREEN}[OK] $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

function print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

function start_environment() {
    print_header "Starting QR Registros Development Environment"
    echo -e "${YELLOW}Building and starting services...${NC}"
    
    $COMPOSE_CMD up --build -d
    
    echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
    sleep 5
    
    $COMPOSE_CMD ps
    
    print_ok "Services started successfully!"
    echo -e "${CYAN}- App:      http://localhost:8000"
    echo -e "- Database: localhost:5432${NC}"
}

function stop_environment() {
    print_header "Stopping QR Registros Development Environment"
    $COMPOSE_CMD down
    print_ok "Services stopped"
}

function restart_environment() {
    print_header "Restarting QR Registros Development Environment"
    $COMPOSE_CMD restart $SERVICE
    print_ok "Service restarted: $SERVICE"
}

function show_logs() {
    print_header "Docker Logs for: $SERVICE"
    $COMPOSE_CMD logs -f $SERVICE
}

function run_tests() {
    print_header "Running Auth Tests"
    $COMPOSE_CMD exec app pytest tests/test_auth_*.py -v
}

function run_migrations() {
    print_header "Running Database Migrations"
    $COMPOSE_CMD exec app python -m alembic upgrade head
    
    print_header "Migration Status"
    $COMPOSE_CMD exec app python -m alembic current
}

function open_shell() {
    print_header "Opening Python Shell"
    echo -e "${YELLOW}Run 'exit()' to quit${NC}"
    $COMPOSE_CMD exec app python
}

function open_db_shell() {
    print_header "Opening PostgreSQL Shell"
    echo -e "${YELLOW}Run '\\q' to quit${NC}"
    $COMPOSE_CMD exec db psql -U postgres -d attendance_db
}

function show_status() {
    print_header "Service Status"
    $COMPOSE_CMD ps
    
    print_header "Database Tables"
    $COMPOSE_CMD exec db psql -U postgres -d attendance_db -c "\dt"
}

function clean_environment() {
    print_header "Cleaning Environment"
    print_warning "This will remove all data!"
    read -p "Continue? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        $COMPOSE_CMD down -v
        print_ok "Environment cleaned"
    else
        echo "Cancelled"
    fi
}

function build_image() {
    print_header "Building Docker Image"
    $COMPOSE_CMD build --no-cache app
    print_ok "Image built successfully"
}

function show_help() {
    cat << 'EOF'
QR Registros Docker Helper Script

USAGE:
    ./docker-dev.sh [COMMAND] [SERVICE]

COMMANDS:
    start       - Start development environment
    stop        - Stop all services
    restart     - Restart a service (default: app)
    logs        - View logs for a service (default: app)
    test        - Run auth tests
    migrate     - Apply database migrations
    shell       - Open Python shell in app container
    db-shell    - Open PostgreSQL shell
    status      - Show service status and tables
    clean       - Remove all data and containers
    build       - Rebuild Docker image
    help        - Show this help message

SERVICES:
    app         - Application container
    db          - Database container

EXAMPLES:
    ./docker-dev.sh start              # Start environment
    ./docker-dev.sh logs app           # View app logs
    ./docker-dev.sh logs db            # View database logs
    ./docker-dev.sh restart            # Restart app
    ./docker-dev.sh test               # Run tests
    ./docker-dev.sh migrate            # Apply migrations
    ./docker-dev.sh db-shell           # Open psql
    ./docker-dev.sh clean              # Clean environment

EOF
}

# Execute command
case $COMMAND in
    start)
        start_environment
        ;;
    stop)
        stop_environment
        ;;
    restart)
        restart_environment
        ;;
    logs)
        show_logs
        ;;
    test)
        run_tests
        ;;
    migrate)
        run_migrations
        ;;
    shell)
        open_shell
        ;;
    db-shell)
        open_db_shell
        ;;
    status)
        show_status
        ;;
    clean)
        clean_environment
        ;;
    build)
        build_image
        ;;
    help|*)
        show_help
        ;;
esac
