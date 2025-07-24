#!/bin/bash

# MintFlow Personal Finance System Deployment Script
# This script sets up and deploys the complete MintFlow system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="mintflow"
ENVIRONMENT=${1:-development}
DOMAIN=${2:-localhost}

echo -e "${GREEN}🚀 Starting MintFlow deployment (Environment: $ENVIRONMENT)${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    echo -e "${YELLOW}➤ $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
fi

if ! command_exists docker-compose; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
fi

print_success "Prerequisites check passed"

# Create required directories
print_status "Creating required directories..."
mkdir -p logs
mkdir -p data/postgres
mkdir -p data/redis
mkdir -p data/elasticsearch
mkdir -p data/prometheus
mkdir -p data/grafana
mkdir -p services/models
mkdir -p monitoring/rules
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/datasources

print_success "Directories created"

# Set up environment file
print_status "Setting up environment configuration..."

if [ ! -f .env ]; then
    cp .env.example .env
    print_status "Created .env file from template. Please update with your configuration."
    
    # Generate secure JWT secret
    JWT_SECRET=$(openssl rand -base64 32)
    sed -i "s/your-super-secret-jwt-key-change-this-in-production/$JWT_SECRET/" .env
    
    # Generate encryption key
    ENCRYPTION_KEY=$(openssl rand -base64 32)
    sed -i "s/your-encryption-key-for-sensitive-data/$ENCRYPTION_KEY/" .env
    
    print_success "Generated secure keys"
else
    print_status ".env file already exists, skipping..."
fi

# Set up Grafana datasources
print_status "Setting up Grafana configuration..."

cat > monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

cat > monitoring/grafana/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'MintFlow Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

print_success "Grafana configuration created"

# Build Docker images
print_status "Building Docker images..."

# Build API Gateway
print_status "Building API Gateway..."
cd services/api-gateway
docker build -t $PROJECT_NAME/api-gateway:latest .
cd ../..

# Build Auth Service
print_status "Building Auth Service..."
cd services/auth
docker build -t $PROJECT_NAME/auth-service:latest .
cd ../..

# Build Banking Service
print_status "Building Banking Service..."
cd services/banking
docker build -t $PROJECT_NAME/banking-service:latest .
cd ../..

# Build Transaction Service
print_status "Building Transaction Service..."
cd services/transaction
docker build -t $PROJECT_NAME/transaction-service:latest .
cd ../..

print_success "Docker images built successfully"

# Start infrastructure services first
print_status "Starting infrastructure services..."

docker-compose up -d postgres redis kafka zookeeper elasticsearch

# Wait for services to be ready
print_status "Waiting for infrastructure services to be ready..."

# Wait for PostgreSQL
until docker-compose exec -T postgres pg_isready -U mintflow; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

# Wait for Redis
until docker-compose exec -T redis redis-cli ping; do
    echo "Waiting for Redis..."
    sleep 2
done

# Wait for Elasticsearch
until curl -s http://localhost:9200/_cluster/health; do
    echo "Waiting for Elasticsearch..."
    sleep 5
done

print_success "Infrastructure services are ready"

# Run database migrations
print_status "Running database migrations..."

# Initialize database
docker-compose exec -T postgres psql -U mintflow -d mintflow -f /docker-entrypoint-initdb.d/init.sql || true

print_success "Database initialized"

# Start application services
print_status "Starting application services..."

docker-compose up -d api-gateway auth-service banking-service transaction-service

# Wait for application services
print_status "Waiting for application services..."
sleep 30

# Start monitoring services
print_status "Starting monitoring services..."

docker-compose up -d prometheus grafana

# Start worker services
print_status "Starting worker services..."

docker-compose up -d celery-worker celery-beat

print_success "All services started"

# Health checks
print_status "Performing health checks..."

services=(
    "http://localhost:8000/health"     # API Gateway
    "http://localhost:8001/health"     # Auth Service
    "http://localhost:8004/health"     # Banking Service
    "http://localhost:8003/health"     # Transaction Service
)

for service in "${services[@]}"; do
    for i in {1..30}; do
        if curl -sf "$service" > /dev/null; then
            print_success "✓ Service $service is healthy"
            break
        else
            if [ $i -eq 30 ]; then
                print_error "✗ Service $service failed health check"
            fi
            echo "Waiting for $service... (attempt $i/30)"
            sleep 10
        fi
    done
done

# Set up SSL certificates for production
if [ "$ENVIRONMENT" = "production" ]; then
    print_status "Setting up SSL certificates..."
    
    if command_exists certbot; then
        # Generate SSL certificates with Let's Encrypt
        certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
        print_success "SSL certificates generated"
    else
        print_status "Certbot not found. Please install SSL certificates manually."
    fi
fi

# Set up log rotation
print_status "Setting up log rotation..."

cat > /etc/logrotate.d/mintflow << EOF
/var/log/mintflow/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose restart api-gateway auth-service banking-service transaction-service
    endscript
}
EOF

print_success "Log rotation configured"

# Performance optimization
print_status "Applying performance optimizations..."

# PostgreSQL optimizations
docker-compose exec -T postgres psql -U mintflow -d mintflow -c "
    ALTER SYSTEM SET shared_buffers = '256MB';
    ALTER SYSTEM SET effective_cache_size = '1GB';
    ALTER SYSTEM SET maintenance_work_mem = '64MB';
    ALTER SYSTEM SET checkpoint_completion_target = 0.9;
    ALTER SYSTEM SET wal_buffers = '16MB';
    ALTER SYSTEM SET default_statistics_target = 100;
    ALTER SYSTEM SET random_page_cost = 1.1;
    SELECT pg_reload_conf();
"

print_success "Performance optimizations applied"

# Create backup script
print_status "Creating backup script..."

cat > backup.sh << 'EOF'
#!/bin/bash

# MintFlow Backup Script
BACKUP_DIR="/backup/mintflow"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker-compose exec -T postgres pg_dump -U mintflow mintflow | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Backup Redis
docker-compose exec -T redis redis-cli --rdb /data/dump.rdb
docker cp $(docker-compose ps -q redis):/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x backup.sh

print_success "Backup script created"

# Setup monitoring alerts
print_status "Setting up monitoring alerts..."

cat > monitoring/rules/mintflow.yml << EOF
groups:
  - name: mintflow
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: High error rate detected
          
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        annotations:
          summary: High response time detected
          
      - alert: DatabaseConnectionsHigh
        expr: pg_stat_activity_count > 80
        for: 5m
        annotations:
          summary: High database connections
EOF

print_success "Monitoring alerts configured"

# Create systemd service for production
if [ "$ENVIRONMENT" = "production" ]; then
    print_status "Creating systemd service..."
    
    cat > /etc/systemd/system/mintflow.service << EOF
[Unit]
Description=MintFlow Personal Finance System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable mintflow
    
    print_success "Systemd service created"
fi

# Display final status
echo ""
echo -e "${GREEN}🎉 MintFlow deployment completed successfully!${NC}"
echo ""
echo "📊 Service URLs:"
echo "  • API Gateway:    http://localhost:8000"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Grafana Dashboard: http://localhost:3001 (admin/admin)"
echo "  • Prometheus:     http://localhost:9090"
echo ""
echo "🔧 Management Commands:"
echo "  • View logs:      docker-compose logs -f [service]"
echo "  • Stop services:  docker-compose down"
echo "  • Restart:        docker-compose restart [service]"
echo "  • Scale:          docker-compose up -d --scale [service]=3"
echo "  • Backup:         ./backup.sh"
echo ""
echo "📚 Next Steps:"
echo "  1. Configure your .env file with actual API keys"
echo "  2. Set up your banking provider credentials (Plaid, Yodlee)"
echo "  3. Configure email settings for notifications"
echo "  4. Set up domain and SSL certificates for production"
echo "  5. Configure monitoring alerts"
echo ""

if [ "$ENVIRONMENT" = "development" ]; then
    echo -e "${YELLOW}⚠️  Development Environment Notes:${NC}"
    echo "  • Using sandbox banking APIs"
    echo "  • Debug mode is enabled"
    echo "  • SSL is disabled"
    echo "  • Default credentials are being used"
    echo ""
fi

# Show resource usage
echo "💾 Resource Usage:"
docker system df
echo ""

print_success "Deployment script completed!"