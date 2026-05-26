# Rate Limiting System Documentation

## Overview

This FastAPI application implements a production-ready, feature-rich rate limiting system that combines the best of both worlds: Redis-backed distributed rate limiting from Enterprise-FastAPI with SlowAPI's mature library features and developer experience.

## Architecture

### Core Components

1. **SlowAPI Limiter** (`app/core/slowapi_limiter.py`)
   - Configurable Redis or in-memory storage
   - Sliding window or fixed window strategies
   - Comprehensive IP detection with proxy support

2. **Rate Limit Middleware** (`app/middlewares/rate_limit_middleware.py`)
   - Global rate limiting with exempt routes
   - Structured error responses
   - Rate limit headers on all responses

3. **Decorators** (`app/api/decorators/rate_limit.py`)
   - Route-specific rate limits
   - Shared limits across multiple endpoints

## Configuration

### Environment Variables

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/0
RATE_LIMIT_EXEMPT_ROUTES=/health,/metrics,/docs,/redoc,/openapi.json
RATE_LIMIT_STRATEGY=moving-window
RATE_LIMIT_HEADER_ENABLED=true
RATE_LIMIT_TRUST_PROXY=true
RATE_LIMIT_KEY_PREFIX=rate_limit

# Redis (if using Redis storage)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

### Default Limits

- **Global**: 100 requests per 60 seconds
- **Authentication routes**: 5 requests per 15 minutes (configurable)

## Usage

### Global Rate Limiting

Rate limiting is automatically applied to all routes except configured exempt routes. No additional code required.

### Route-Specific Limits

```python
from app.api.decorators.rate_limit import rate_limit

@app.get("/api/sensitive-data")
@rate_limit(requests=10, window=60)
async def get_sensitive_data():
    return {"data": "sensitive"}
```

### Shared Limits

```python
from app.api.decorators.rate_limit import shared_limit

@shared_limit(requests=1000, window=3600, scope="user_uploads")
@app.post("/upload/file")
async def upload_file():
    pass

@shared_limit(requests=1000, window=3600, scope="user_uploads")
@app.post("/upload/image")
async def upload_image():
    pass
```

## IP Detection

The system extracts client IP addresses with comprehensive proxy support:

1. **X-Forwarded-For** (handles comma-separated chains)
2. **X-Real-IP**
3. **CF-Connecting-IP** (Cloudflare)
4. **client.host** (fallback)

Invalid IPs are filtered out, ensuring only valid IPv4/IPv6 addresses are used.

## Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1708617600
```

## Error Responses

When rate limit is exceeded:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please retry after 45 seconds.",
    "details": {
      "limit": 100,
      "window": "60 seconds",
      "retry_after": 45,
      "reset_at": "2024-02-22T15:30:00Z"
    }
  }
}
```

HTTP headers:
```
HTTP/1.1 429 Too Many Requests
Retry-After: 45
```

## Storage Options

### Redis (Recommended for Production)

```bash
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/0
```

- Distributed across multiple instances
- Persistent storage
- High performance

### In-Memory (Development/Testing)

```bash
RATE_LIMIT_STORAGE_URL=memory://
```

- Single instance only
- Fast, no external dependencies
- Data lost on restart

## Strategies

### Moving Window (Sliding Window)

```bash
RATE_LIMIT_STRATEGY=moving-window
```

- More accurate rate limiting
- No burst issues at window boundaries
- Slightly higher memory usage

### Fixed Window

```bash
RATE_LIMIT_STRATEGY=fixed-window
```

- Simpler implementation
- Allows bursts at window boundaries
- Lower memory usage

## Monitoring

### Logging

All rate limit events are logged with structured logging:

- Rate limit exceeded events (WARNING level)
- Client IP, endpoint, retry time
- Errors in rate limiting logic

### Metrics

Rate limiting metrics are available at `/metrics` (if Prometheus enabled):

- `rate_limit_requests_total`: Total requests
- `rate_limit_exceeded_total`: Rate limit violations
- `rate_limit_remaining`: Current remaining requests per client

## Exempt Routes

Configure routes that bypass rate limiting:

```python
RATE_LIMIT_EXEMPT_ROUTES=/health,/metrics,/docs,/redoc,/openapi.json,/static
```

## Testing

Run the test suite:

```bash
pytest tests/test_rate_limit.py -v
```

Tests cover:
- IP extraction logic
- Rate limiting middleware
- Error handling and fallbacks
- Header injection

## Deployment

### Redis Setup

1. Install Redis server
2. Configure connection in environment variables
3. Ensure Redis is accessible from all application instances

### Environment Configuration

Create `.env` file:

```bash
# Rate Limiting
RATE_LIMIT_STORAGE_URL=redis://redis-host:6379/0
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=60

# Redis
REDIS_HOST=redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
```

### Health Checks

Rate limiting includes built-in health checks. If Redis is unavailable, the system gracefully degrades by allowing all requests while logging errors.

## Best Practices

1. **Use Redis in production** for distributed rate limiting
2. **Configure appropriate limits** based on your API usage patterns
3. **Monitor rate limit metrics** to adjust limits as needed
4. **Use shared limits** for related endpoints
5. **Exempt health check endpoints** to ensure monitoring works
6. **Test thoroughly** in staging environment before production

## Troubleshooting

### Common Issues

1. **Rate limiting not working**
   - Check `RATE_LIMIT_ENABLED=true`
   - Verify Redis connection if using Redis storage
   - Check logs for middleware registration

2. **Incorrect IP detection**
   - Ensure proxy headers are properly configured
   - Check `RATE_LIMIT_TRUST_PROXY=true` for proxy environments

3. **Headers not appearing**
   - Verify `RATE_LIMIT_HEADER_ENABLED=true`
   - Check middleware registration order

### Debug Mode

Enable debug logging to see detailed rate limiting information:

```bash
LOG_LEVEL=DEBUG
```

## Performance

- **Latency**: <10ms per request (Redis), <1ms (in-memory)
- **Memory**: Minimal overhead, scales with concurrent users
- **Throughput**: Handles thousands of requests per second

## Security Considerations

- Rate limiting helps prevent DoS attacks
- IP-based limiting may not work behind CDNs (consider user-based limits)
- Monitor for rate limit bypass attempts
- Use HTTPS to prevent header spoofing
