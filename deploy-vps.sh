#!/bin/bash

# =============================================================================
# OpenAI to Gemini Adapter - VPS Deployment Script
# =============================================================================

set -e

echo "🚀 Starting OpenAI to Gemini Adapter deployment to VPS..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker and Docker Compose are installed
check_dependencies() {
    print_status "Checking dependencies..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    print_success "Dependencies check passed."
}

# Setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_warning "Created .env file from .env.example"
            print_warning "Please edit .env file with your actual credentials before running the service"
        else
            print_error "No .env.example file found. Creating basic .env file."
            cat > .env << EOF
API_KEY=your_secure_api_key_here
VERTEX_EXPRESS_API_KEY=
GOOGLE_CREDENTIALS_JSON=
GCP_PROJECT_ID=
GCP_LOCATION=us-central1
ROUNDROBIN=false
FAKE_STREAMING=false
FAKE_STREAMING_INTERVAL=1.0
WORKERS=1
EOF
        fi
    else
        print_status "Environment file .env already exists."
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."

    mkdir -p credentials
    mkdir -p logs
    mkdir -p nginx

    print_success "Directories created."
}

# Setup Nginx configuration (optional)
setup_nginx() {
    print_status "Setting up Nginx configuration..."

    if [ ! -f nginx/nginx.conf ]; then
        cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream vertex2openai {
        server openai-to-gemini:7860;
    }

    server {
        listen 80;
        server_name your-domain.com;

        # Redirect HTTP to HTTPS (uncomment if you have SSL)
        # return 301 https://$server_name$request_uri;

        location / {
            proxy_pass http://vertex2openai;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }

    # HTTPS server (uncomment if you have SSL certificates)
    # server {
    #     listen 443 ssl http2;
    #     server_name your-domain.com;
    #
    #     ssl_certificate /etc/nginx/ssl/cert.pem;
    #     ssl_certificate_key /etc/nginx/ssl/key.pem;
    #
    #     location / {
    #         proxy_pass http://vertex2openai;
    #         proxy_set_header Host $host;
    #         proxy_set_header X-Real-IP $remote_addr;
    #         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    #         proxy_set_header X-Forwarded-Proto $scheme;
    #
    #         proxy_http_version 1.1;
    #         proxy_set_header Upgrade $http_upgrade;
    #         proxy_set_header Connection "upgrade";
    #     }
    # }
}
EOF
        print_warning "Created nginx.conf. Please update server_name and SSL settings."
    fi
}

# Deploy the application
deploy() {
    print_status "Building and starting the application..."

    # Use the VPS-optimized docker-compose file
    docker-compose -f docker-compose.vps.yml down
    docker-compose -f docker-compose.vps.yml build --no-cache
    docker-compose -f docker-compose.vps.yml up -d

    print_success "Application deployed successfully!"
}

# Check deployment status
check_deployment() {
    print_status "Checking deployment status..."

    sleep 10

    if docker-compose -f docker-compose.vps.yml ps | grep -q "Up"; then
        print_success "Service is running!"

        # Check if the service responds to health check
        if curl -f http://localhost:8050/ &> /dev/null; then
            print_success "Service health check passed!"
        else
            print_warning "Service is running but health check failed. Check logs for details."
        fi
    else
        print_error "Service failed to start. Check logs with: docker-compose -f docker-compose.vps.yml logs"
        exit 1
    fi
}

# Show usage information
show_usage() {
    echo ""
    print_success "Deployment completed! 🎉"
    echo ""
    echo "Service Information:"
    echo "  - Main API endpoint: http://localhost:8050"
    echo "  - Models endpoint: http://localhost:8050/v1/models"
    echo "  - Chat endpoint: http://localhost:8050/v1/chat/completions"
    echo ""
    echo "Management Commands:"
    echo "  - View logs: docker-compose -f docker-compose.vps.yml logs -f"
    echo "  - Stop service: docker-compose -f docker-compose.vps.yml down"
    echo "  - Restart service: docker-compose -f docker-compose.vps.yml restart"
    echo "  - Update service: docker-compose -f docker-compose.vps.yml pull && docker-compose -f docker-compose.vps.yml up -d"
    echo ""
    echo "Optional Components:"
    echo "  - Enable Nginx: docker-compose -f docker-compose.vps.yml --profile with-nginx up -d"
    echo "  - Enable auto-updates: docker-compose -f docker-compose.vps.yml --profile with-watchtower up -d"
    echo ""
    print_warning "Remember to:"
    echo "  1. Edit .env file with your actual credentials"
    echo "  2. Place your Google Cloud service account JSON files in ./credentials/"
    echo "  3. Configure firewall rules to allow traffic on port 8050"
    echo "  4. Set up SSL certificates for production use"
}

# Main execution
main() {
    echo "OpenAI to Gemini Adapter - VPS Deployment Script"
    echo "================================================="

    check_dependencies
    setup_environment
    create_directories
    setup_nginx
    deploy
    check_deployment
    show_usage
}

# Run the script
main "$@"