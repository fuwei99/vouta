# VPS Deployment Guide

This guide provides comprehensive instructions for deploying the OpenAI to Gemini Adapter on a Virtual Private Server (VPS).

## Quick Start

1. **Clone and Prepare:**
   ```bash
   git clone <your-repository-url>
   cd vouta
   chmod +x deploy-vps.sh
   ./deploy-vps.sh
   ```

2. **Configure Credentials:**
   ```bash
   # Edit the environment file
   nano .env

   # Add your Google Cloud service account JSON files
   cp your-service-account-key.json credentials/
   ```

3. **Start Service:**
   ```bash
   docker-compose -f docker-compose.vps.yml up -d
   ```

## Prerequisites

- **Docker & Docker Compose** installed
- **Google Cloud Project** with Vertex AI API enabled
- **Service Account** with Vertex AI permissions (or Vertex Express API Key)
- **VPS** with at least 512MB RAM, 1 CPU core
- **Domain name** (optional, for production with SSL)

## Configuration Options

### 1. Environment Variables (.env)

Copy `.env.example` to `.env` and configure:

```env
# REQUIRED
API_KEY=your_secure_api_key_here

# Choose ONE credential method:
VERTEX_EXPRESS_API_KEY=your_vertex_express_key
# OR
GOOGLE_CREDENTIALS_JSON='{"type": "service_account", ...}'
# OR place JSON files in ./credentials/ directory

# Optional
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
ROUNDROBIN=false
WORKERS=1
```

### 2. Service Account Setup

**Option A: JSON Files (Recommended)**
1. Create service accounts in Google Cloud Console
2. Download JSON key files
3. Place them in `./credentials/` directory
4. Set proper permissions: `chmod 600 credentials/*.json`

**Option B: Environment Variable**
1. Copy JSON content to `GOOGLE_CREDENTIALS_JSON` env var
2. For multiple keys, separate with commas

**Option C: Vertex Express API Key**
1. Generate Express API key in Vertex AI console
2. Set `VERTEX_EXPRESS_API_KEY` environment variable

## Deployment Methods

### Method 1: Automated Script (Recommended)

```bash
./deploy-vps.sh
```

This script will:
- Check dependencies
- Setup environment files
- Create necessary directories
- Configure Nginx (optional)
- Deploy the application

### Method 2: Manual Deployment

```bash
# Create environment file
cp .env.example .env
# Edit .env with your credentials

# Create directories
mkdir -p credentials logs nginx

# Build and start
docker-compose -f docker-compose.vps.yml build
docker-compose -f docker-compose.vps.yml up -d
```

## Production Enhancements

### 1. Enable Nginx Reverse Proxy

```bash
docker-compose -f docker-compose.vps.yml --profile with-nginx up -d
```

Configure `nginx/nginx.conf` with your domain and SSL settings.

### 2. Enable Automatic Updates

```bash
docker-compose -f docker-compose.vps.yml --profile with-watchtower up -d
```

### 3. SSL/HTTPS Setup

1. Obtain SSL certificates (Let's Encrypt recommended)
2. Place certificates in `nginx/ssl/`
3. Uncomment HTTPS section in `nginx/nginx.conf`
4. Update domain name in configuration

### 4. Firewall Configuration

```bash
# Allow HTTP/HTTPS traffic
sudo ufw allow 80
sudo ufw allow 443
# Allow API port (if not using Nginx)
sudo ufw allow 8050
```

## Monitoring and Management

### Health Checks

The service includes built-in health checks:
```bash
# Check service status
docker-compose -f docker-compose.vps.yml ps

# Check health logs
docker-compose -f docker-compose.vps.yml logs openai-to-gemini
```

### Log Management

Logs are stored in the `./logs/` directory:
```bash
# View real-time logs
docker-compose -f docker-compose.vps.yml logs -f

# View specific service logs
docker-compose -f docker-compose.vps.yml logs -f openai-to-gemini
```

### Scaling

For higher traffic, adjust resources in `docker-compose.vps.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '1.0'
```

## API Usage

Once deployed, the service is available at:

- **Base URL:** `http://your-domain.com:8050` (or via Nginx on port 80)
- **Models:** `GET /v1/models`
- **Chat:** `POST /v1/chat/completions`

Example request:
```bash
curl -X POST http://your-domain.com:8050/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "model": "gemini-1.5-flash-latest",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Security Recommendations

1. **Strong API Keys:** Use randomly generated, long API keys
2. **HTTPS:** Always use SSL in production
3. **Firewall:** Restrict access to necessary ports only
4. **Service Account Permissions:** Use principle of least privilege
5. **Regular Updates:** Keep Docker images updated
6. **Monitoring:** Monitor logs and resource usage

## Troubleshooting

### Common Issues

1. **Service won't start:**
   ```bash
   # Check logs
   docker-compose -f docker-compose.vps.yml logs

   # Verify credentials format and permissions
   ```

2. **Authentication errors:**
   - Verify API key in requests
   - Check Google Cloud credentials
   - Ensure Vertex AI API is enabled

3. **Memory issues:**
   - Increase memory limits in docker-compose.yml
   - Add swap space on VPS if needed

4. **Port conflicts:**
   - Check if ports are already in use
   - Modify port mappings in docker-compose.yml

### Debug Mode

Enable debugging:
```env
FAKE_STREAMING=true
```

And check logs for detailed information.

## Backup and Recovery

### Regular Backups

1. **Configuration:**
   ```bash
   tar -czf backup-$(date +%Y%m%d).tar.gz .env credentials/ nginx/
   ```

2. **Data:** This service is stateless, but backup any custom configurations.

### Recovery

1. Restore configuration files
2. Run deployment script
3. Verify service is working

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Verify environment configuration
3. Test credentials manually
4. Check resource usage and limits

---

**Note:** This adapter provides OpenAI-compatible endpoints for Gemini models. Ensure you comply with Google's usage policies and terms of service.