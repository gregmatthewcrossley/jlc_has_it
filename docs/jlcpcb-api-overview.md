# JLCPCB API Overview

This document summarizes the JLCPCB API based on official documentation.

## Base URL

```
https://api.jlcpcb.com
```

## Authentication

All API requests use HMAC-SHA256 signature authentication.

### Required Credentials

- **APP_ID**: Application identifier
- **ACCESS_KEY**: Public key identifier
- **SECRET_KEY**: Private key for signing (keep secure!)

### Authentication Flow

1. Build signature string (5 lines, each ending with `\n`):
   ```
   <HTTP Method>\n
   <Request Path>\n
   <Timestamp>\n
   <Nonce>\n
   <Request Body>\n
   ```

2. Sign with HMAC-SHA256 using SECRET_KEY
3. Base64 encode the signature
4. Add Authorization header:
   ```
   Authorization: JOP appid="<APP_ID>",accesskey="<ACCESS_KEY>",nonce="<NONCE>",timestamp="<TIMESTAMP>",signature="<SIGNATURE>"
   ```

## Request Format

### HTTP Method
- All requests must use **POST**
- Must use **HTTPS** (not HTTP)

### Headers

**Standard JSON requests:**
```
Content-Type: application/json
Authorization: JOP appid="...",accesskey="...",nonce="...",timestamp="...",signature="..."
```

**File upload requests:**
```
Content-Type: multipart/form-data
Authorization: JOP appid="...",accesskey="...",nonce="...",timestamp="...",signature="..."
```

### Character Encoding
- **UTF-8** for all requests and responses

### Date Format
- **China Standard Time (GMT+8)**
- Format: `yyyy-MM-dd HH:mm:ss`
- Example: `2024-03-21 10:03:20`

### Request Tracing
- Each response includes `J-Trace-ID` header
- Use this for support requests

## Response Format

### HTTP Status Codes

- **200**: Request received (check body for business-level status)
- **400**: Invalid request parameters
- **401**: Unauthorized (signature verification failed)
- **403**: Forbidden request
- **500**: Internal server error

### Error Response Body

```json
{
  "code": 1001,
  "message": "Insufficient prepaid balance"
}
```

## Component APIs

### 1. Component Information Interface (Pagination)

**Purpose**: Query all components from JLCPCB's public library with pagination

**Endpoint**: Not specified in docs (TBD during research)

**Use case**: Browse large component catalog

### 2. Query Component Detail Data Interface

**Purpose**: Get detailed information for a specific component by C-number

**Endpoint**: Not specified in docs (TBD during research)

**Parameters**:
- C-number (e.g., "C1525" for a capacitor)

**Use case**: Retrieve full specs for a selected component

### 3. Query Private Component Library Interface

**Purpose**: Query authenticated customer's private inventory

**Endpoint**: Not specified in docs (TBD during research)

**Use case**: Access user's custom component library

## Security Features

### IP Whitelist

- Configure allowed IP addresses in API Platform console
- Supported formats:
  - Single IPv4: `123.103.49.137`
  - IPv4 with subnet: `123.103.49.137/24`
  - Single IPv6: `2409:8800:8813:208a:617a:6125:d33f:79e0`
  - IPv6 with prefix: `2409:8800:8813::/64`

- Multiple IPs: one per line (no commas)

## Implementation Notes

### Signature String Construction (Python)

```python
import hmac
import hashlib
import base64
import time
import secrets

def generate_nonce(length=32):
    """Generate 32-character random nonce"""
    return ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789') for _ in range(length))

def build_signature_string(method, path, timestamp, nonce, body):
    """Build the signature string (5 lines, each ending with \n)"""
    return f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n"

def sign_request(signature_string, secret_key):
    """Sign with HMAC-SHA256 and encode with Base64"""
    signature_bytes = hmac.new(
        secret_key.encode('utf-8'),
        signature_string.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature_bytes).decode('utf-8')

def build_auth_header(app_id, access_key, secret_key, method, path, body):
    """Build complete Authorization header"""
    nonce = generate_nonce()
    timestamp = str(int(time.time()))
    signature_string = build_signature_string(method, path, timestamp, nonce, body)
    signature = sign_request(signature_string, secret_key)

    return f'JOP appid="{app_id}",accesskey="{access_key}",nonce="{nonce}",timestamp="{timestamp}",signature="{signature}"'
```

### Example Request

```python
import requests

# Load credentials
app_id = "293992070061998081"
access_key = "b6713a535d56412f805afadd7e818455"
secret_key = "z0BWlikshimuyiwBsH1i2qwnzMb3j3kA"

# Request details
method = "POST"
path = "/order/v1/createOrder"
body = '{"goodsId":100,"quantity":52,"createdTime":"2024-03-21 10:03:20"}'

# Build headers
auth_header = build_auth_header(app_id, access_key, secret_key, method, path, body)

# Make request
response = requests.post(
    f"https://api.jlcpcb.com{path}",
    headers={
        "Content-Type": "application/json",
        "Authorization": auth_header
    },
    data=body
)

print(response.status_code)
print(response.json())
```

## Next Steps for Implementation

1. **Research exact endpoint paths**:
   - Component search endpoint
   - Component detail endpoint
   - Private library endpoint

2. **Test authentication**:
   - Verify signature generation
   - Test with real API credentials
   - Handle error responses

3. **Implement client library**:
   - Create `JLCPCBClient` class
   - Handle signature generation automatically
   - Provide pythonic interface for component search

4. **Handle pagination**:
   - Component library has thousands of items
   - Implement proper pagination logic

5. **Cache considerations**:
   - API likely has rate limits
   - Consider caching component data
   - SQLite cache for frequently accessed components
