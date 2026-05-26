# FastAPI Boiler Plate

A production-ready FastAPI application with clean architecture, dependency injection, and comprehensive infrastructure support.

## 🚀 Features

- **Clean Architecture** with layered design (Controllers → Mediators → Services → Repositories)
- **Dependency Injection** using `dependency-injector` library
- **Multiple Database Support** with master-replica PostgreSQL setup
- **Redis Caching** with cluster support
- **Message Queuing** with RabbitMQ and Kafka integration
- **Prometheus Monitoring** with comprehensive metrics
- **Health Checks** for all infrastructure components
- **Async Support** throughout the application
- **Production Ready** with proper error handling and logging
- **Docker Support** with full infrastructure stack
- **Development Tools** with Adminer, Redis Commander, and more

## 📋 Prerequisites

- Python 3.9+
- Docker & Docker Compose
- PostgreSQL (Primary + Replica)
- Redis Cluster
- RabbitMQ
- Kafka
- Prometheus

## 🛠️ Installation

### Quick Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd FastAPI-Boiler-Plate
   ```

2. **Run the setup script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

   The setup script will:
   - Check Docker and Docker Compose
   - Create environment configuration
   - Start infrastructure services
   - Setup Python environment
   - Run basic tests

### Manual Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Start infrastructure services**
   ```bash
   # Full setup (all services)
   docker-compose up -d
   
   # Light setup (essential services only)
   docker-compose -f docker-compose.light.yml up -d
   ```

## 🏃‍♂️ Running the Application

### Development Mode
```bash
python -m app.main
```

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### With Docker (Development)
```bash
docker-compose -f docker-compose.override.yml up
```

### With Docker (Production)
```bash
docker build -t fastapi-app .
docker run -p 8000:8000 --env-file .env fastapi-app
```

## 🏗️ Architecture

### Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Controllers                       │
│         (HTTP endpoints with request/response)           │
├─────────────────────────────────────────────────────────┤
│                     Mediators                           │
│         (Request orchestration & validation)            │
├─────────────────────────────────────────────────────────┤
│                     Services                            │
│            (Business logic & rules)                     │
├─────────────────────────────────────────────────────────┤
│                   Repositories                          │
│        (Data access with caching layer)                 │
├─────────────────────────────────────────────────────────┤
│                     Models                              │
│            (Database schema definitions)                │
├─────────────────────────────────────────────────────────┤
│                  Infrastructure                         │
│     ✅ Database, Cache, Message Queues, Monitoring     │
└─────────────────────────────────────────┘
```

### Project Structure

```
app/
├── api/                    # API endpoints
│   └── v1/               # API version 1
│       ├── api.py        # Main API router
│       └── endpoints/    # Endpoint modules
├── core/                  # Core application
│   ├── config.py         # Configuration management
│   ├── container.py      # Dependency injection container
│   └── events.py         # Application events
├── infrastructure/        # Infrastructure components
│   ├── database.py       # Database connections
│   ├── cache.py          # Redis cache manager
│   ├── messaging.py      # RabbitMQ & Kafka clients
│   └── monitoring.py     # Prometheus metrics
├── models/                # Database models (to be implemented)
├── repositories/          # Data access layer (to be implemented)
├── services/              # Business logic (to be implemented)
├── mediators/             # Request orchestration (to be implemented)
├── schemas/               # Pydantic schemas (to be implemented)
└── main.py               # Application entry point

# Docker & Infrastructure
docker-compose.yml         # Full infrastructure stack
docker-compose.light.yml   # Light infrastructure (dev)
docker-compose.override.yml # Development overrides
Dockerfile                 # Main application container
Dockerfile.mqtt-publisher  # MQTT metrics publisher
setup.sh                   # Automated setup script
```

## 🐳 Docker Infrastructure

### Service Ports (Avoiding Conflicts)

| Service | Internal Port | External Port | Description |
|---------|---------------|---------------|-------------|
| FastAPI App | 8000 | 8000 | Main application |
| PostgreSQL Primary | 5432 | 5433 | Master database |
| PostgreSQL Replica | 5432 | 5434 | Read replica |
| Redis | 6379/7000-7002 | 7004 | Cache cluster |
| RabbitMQ | 5672 | 5673 | Message queue |
| RabbitMQ Management | 15672 | 15673 | Web interface |
| Kafka | 9092 | 9093 | Event streaming |
| Prometheus | 9090 | 9091 | Metrics collection |
| Grafana | 3000 | 3002 | Monitoring dashboard |
| Adminer | 8080 | 8080 | Database management |
| Redis Commander | 8081 | 8081 | Redis management |

### Infrastructure Options

#### Full Setup (`docker-compose.yml`)
- Complete production-like environment
- All monitoring and export services
- Master-replica database setup
- Redis cluster mode
- Full Prometheus monitoring

#### Light Setup (`docker-compose.light.yml`)
- Essential services only
- Single PostgreSQL instance
- Single Redis instance
- Basic monitoring
- Perfect for development

#### Development Override (`docker-compose.override.yml`)
- Hot-reload for FastAPI
- Development tools (Adminer, Redis Commander)
- Volume mounts for code changes
- Debug mode enabled

## 🔧 Configuration

The application uses Pydantic settings for configuration management. Key configuration areas:

- **Database**: Master-replica PostgreSQL setup
- **Cache**: Redis cluster configuration
- **Messaging**: RabbitMQ and Kafka settings
- **Monitoring**: Prometheus metrics configuration
- **Security**: JWT and authentication settings

### Environment Variables

```bash
# Copy and customize
cp env.example .env

# Key variables to configure
SECRET_KEY=your-secret-key-here
DB_MASTER_HOST=localhost
DB_MASTER_PORT=5433
REDIS_HOST=localhost
REDIS_PORT=7004
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5673
KAFKA_BOOTSTRAP_SERVERS=["localhost:9093"]
```

## 📊 Monitoring

### Prometheus Metrics
```
http://localhost:9091/metrics
```

### Health Checks
- Basic: `/health`
- Liveness: `/health/live`
- Readiness: `/health/ready`
- Detailed: `/health/detailed`

### Available Metrics
- HTTP request counts and durations
- Database query metrics
- Cache hit/miss rates
- Message queue metrics
- Business event counters

### Service URLs
- **FastAPI App**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3002 (admin/admin)
- **RabbitMQ Mgmt**: http://localhost:15673 (admin/admin)
- **Adminer (DB)**: http://localhost:8080
- **Redis Commander**: http://localhost:8081

## 🧪 Testing

### Run all tests
```bash
pytest
```

### Run specific test suites
```bash
pytest tests/unit/        # Unit tests
pytest tests/integration/ # Integration tests
pytest tests/e2e/        # End-to-end tests
```

### Test coverage
```bash
pytest --cov=app --cov-report=html
```

### Setup verification
```bash
python test_setup.py
```

## 🚀 Next Steps

This is **Step 1** of the implementation. The following components will be added in subsequent steps:

1. **✅ Infrastructure Layer** - Database, Cache, Messaging, Monitoring
2. **🔄 Models & Schemas** - SQLAlchemy models and Pydantic schemas
3. **🔄 Repository Layer** - Data access with caching
4. **🔄 Service Layer** - Business logic implementation
5. **🔄 Mediator Layer** - Request orchestration
6. **🔄 Controller Layer** - Complete API endpoints
7. **🔄 Authentication & Security** - JWT, middleware, validation
8. **🔄 Testing Suite** - Comprehensive test coverage
9. **🔄 Deployment** - Docker, CI/CD, production setup

## 🔒 Security

- JWT authentication (to be implemented)
- Request validation using Pydantic
- CORS configuration
- Environment variable validation
- Secure database connections

## 📈 Performance

- Async/await throughout the application
- Connection pooling for databases
- Redis caching with TTL
- Message queue integration
- Prometheus metrics for monitoring

## 🐳 Docker Commands

### Start Services
```bash
# Full infrastructure
docker-compose up -d

# Light infrastructure
docker-compose -f docker-compose.light.yml up -d

# Development mode
docker-compose -f docker-compose.override.yml up
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f [service-name]
```

### Rebuild Services
```bash
docker-compose build --no-cache
```

### Clean Up
```bash
docker-compose down -v --remove-orphans
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

MIT License

## 🔗 Related Projects

This FastAPI boiler plate is designed to replicate the architecture of the [Node.js Boiler Plate](../node-boiler-plate) project, providing the same clean architecture patterns in Python.

## 🆘 Troubleshooting

### Common Issues

1. **Port conflicts**: All external ports are incremented by +1 to avoid conflicts
2. **Service not starting**: Check Docker logs with `docker-compose logs [service]`
3. **Connection refused**: Ensure services are fully started before connecting
4. **Permission denied**: Make setup script executable with `chmod +x setup.sh`

### Getting Help

- Check service logs: `docker-compose logs [service-name]`
- Verify service status: `docker-compose ps`
- Check health endpoints: `curl http://localhost:8000/health`
- Review configuration files in `infrastructure/` directory
