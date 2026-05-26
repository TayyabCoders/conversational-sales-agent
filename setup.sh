#!/bin/bash
# FastAPI Boiler Plate Setup Script

set -e

echo "🚀 FastAPI Boiler Plate Setup"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker is running
check_docker() {
    print_info "Checking Docker..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_status "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_info "Checking Docker Compose..."
    if ! docker-compose --version > /dev/null 2>&1; then
        print_error "Docker Compose is not available. Please install Docker Compose and try again."
        exit 1
    fi
    print_status "Docker Compose is available"
}

# Create environment file
setup_environment() {
    print_info "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        if [ -f env.example ]; then
            cp env.example .env
            print_status "Created .env file from env.example"
        else
            print_warning "env.example not found, creating basic .env file"
            cat > .env << EOF
# Application Configuration
DEBUG=true
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["*"]

# Database - Primary (Master)
DB_MASTER_HOST=localhost
DB_MASTER_PORT=5433
DB_MASTER_USERNAME=user
DB_MASTER_PASSWORD=1234
DB_MASTER_DATABASE=app_db

# Database - Secondary (Replica)
DB_REPLICA_HOST=localhost
DB_REPLICA_PORT=5434
DB_REPLICA_USERNAME=user
DB_REPLICA_PASSWORD=1234
DB_REPLICA_DATABASE=app_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=7004
REDIS_PASSWORD=
REDIS_DB=0
REDIS_CLUSTER_MODE=false

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5673
RABBITMQ_USERNAME=admin
RABBITMQ_PASSWORD=admin
RABBITMQ_VIRTUAL_HOST=/

# Kafka
KAFKA_BOOTSTRAP_SERVERS=["localhost:9093"]
KAFKA_CLIENT_ID=fastapi-app
KAFKA_GROUP_ID=fastapi-group

# Prometheus
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9091

# Enable Metrics
ENABLE_METRICS=true
EOF
            print_status "Created basic .env file"
        fi
    else
        print_info ".env file already exists"
    fi
}

# Start infrastructure services
start_infrastructure() {
    print_info "Starting infrastructure services..."
    
    # Ask user which compose file to use
    echo "Choose infrastructure setup:"
    echo "1) Full setup (all services)"
    echo "2) Light setup (essential services only)"
    echo "3) Skip infrastructure setup"
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            print_info "Starting full infrastructure setup..."
            docker-compose up -d
            print_status "Full infrastructure started"
            ;;
        2)
            print_info "Starting light infrastructure setup..."
            docker-compose -f docker-compose.light.yml up -d
            print_status "Light infrastructure started"
            ;;
        3)
            print_warning "Skipping infrastructure setup"
            ;;
        *)
            print_error "Invalid choice, skipping infrastructure setup"
            ;;
    esac
}

# Wait for services to be ready
wait_for_services() {
    print_info "Waiting for services to be ready..."
    
    # Wait for PostgreSQL
    print_info "Waiting for PostgreSQL..."
    until docker exec fastapi-postgres-primary pg_isready -U user > /dev/null 2>&1; do
        echo -n "."
        sleep 2
    done
    echo
    print_status "PostgreSQL is ready"
    
    # Wait for Redis
    print_info "Waiting for Redis..."
    until docker exec fastapi-redis redis-cli ping > /dev/null 2>&1; do
        echo -n "."
        sleep 2
    done
    echo
    print_status "Redis is ready"
    
    # Wait for RabbitMQ
    print_info "Waiting for RabbitMQ..."
    until curl -s http://localhost:15673/api/overview > /dev/null 2>&1; do
        echo -n "."
        sleep 2
    done
    echo
    print_status "RabbitMQ is ready"
}

# Setup Python environment
setup_python() {
    print_info "Setting up Python environment..."
    
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv venv
        print_status "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi
    
    print_info "Activating virtual environment and installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    print_status "Python dependencies installed"
}

# Run tests
run_tests() {
    print_info "Running setup tests..."
    
    if python test_setup.py; then
        print_status "Setup tests passed"
    else
        print_warning "Setup tests failed, but continuing..."
    fi
}

# Show service URLs
show_service_urls() {
    echo
    echo "🌐 Service URLs:"
    echo "================"
    echo "FastAPI App:        http://localhost:8000"
    echo "FastAPI Docs:       http://localhost:8000/docs"
    echo "Health Check:       http://localhost:8000/health"
    echo "Prometheus:         http://localhost:9091"
    echo "Grafana:            http://localhost:3002 (admin/admin)"
    echo "RabbitMQ Mgmt:      http://localhost:15673 (admin/admin)"
    echo "Adminer (DB):       http://localhost:8080"
    echo "Redis Commander:    http://localhost:8081"
    echo
    echo "🔌 Database Ports:"
    echo "=================="
    echo "PostgreSQL Primary: localhost:5433"
    echo "PostgreSQL Replica: localhost:5434"
    echo "Redis:              localhost:7004"
    echo "RabbitMQ:           localhost:5673"
    echo "Kafka:              localhost:9093"
    echo
}

# Main setup function
main() {
    echo "Starting FastAPI Boiler Plate setup..."
    
    check_docker
    check_docker_compose
    setup_environment
    start_infrastructure
    
    if [ "$choice" != "3" ]; then
        wait_for_services
    fi
    
    setup_python
    run_tests
    show_service_urls
    
    echo
    print_status "Setup completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Copy .env.example to .env and configure your environment"
    echo "2. Start your FastAPI application: python -m app.main"
    echo "3. Visit http://localhost:8000/docs for API documentation"
    echo
    echo "For development with Docker:"
    echo "docker-compose -f docker-compose.override.yml up"
}

# Run main function
main "$@"
