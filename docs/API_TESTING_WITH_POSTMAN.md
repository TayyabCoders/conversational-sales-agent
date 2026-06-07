# API Testing Guide with Postman

This guide provides step-by-step instructions for testing the Conversational Sales Agent APIs using Postman.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Authentication Endpoints](#authentication-endpoints)
- [Conversation Endpoints](#conversation-endpoints)
- [Knowledge Base Endpoints](#knowledge-base-endpoints)
- [Lead Management Endpoints](#lead-management-endpoints)
- [Webhook Endpoints](#webhook-endpoints)

---

## Prerequisites

- **Postman** installed (download from [https://www.postman.com/downloads/](https://www.postman.com/downloads/))
- **API Server** running locally (default: `http://localhost:8000`)
- **Database** and **RabbitMQ** services running

---

## Setup

### 1. Start the API Server

```bash
# Navigate to project directory
cd d:\360ExpertsTrainee\Project\sales agent autonomous

# Start the server (adjust command based on your setup)
python -m app.main
```

The server will start on `http://localhost:8000` (or as configured in your settings).

### 2. Access API Documentation

Open your browser and navigate to:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These provide interactive API documentation.

### 3. Configure Postman Environment (Optional)

Create an environment in Postman to store variables:

1. Click the gear icon (Manage Environments) → Add
2. Name it: `Sales Agent API`
3. Add variables:
   - `base_url`: `http://localhost:8000`
   - `access_token`: (leave empty, will be set after login)
   - `refresh_token`: (leave empty, will be set after login)

---

## Authentication Endpoints

Base URL: `{{base_url}}/api/v1/auth`

### 1. Register User

**Endpoint**: `POST /api/v1/auth/register`

**Purpose**: Create a new user account.

**Steps**:
1. Create a new request in Postman
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/auth/register`
4. Go to **Body** tab → select **raw** → **JSON**
5. Paste the following JSON:

```json
{
  "username": "testuser",
  "email": "testuser@example.com",
  "password": "SecurePassword123!"
}
```

6. Click **Send**

**Expected Response** (201 Created):
```json
{
  "id": "uuid-here",
  "username": "testuser",
  "email": "testuser@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": null
}
```

---

### 2. Login

**Endpoint**: `POST /api/v1/auth/login`

**Purpose**: Authenticate user and receive access tokens.

**Steps**:
1. Create a new request
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/auth/login`
4. Go to **Body** tab → select **raw** → **JSON**
5. Paste the following JSON:

```json
{
  "email": "testuser@example.com",
  "password": "SecurePassword123!"
}
```

6. Click **Send**
7. **Save the tokens** from the response for future requests

**Expected Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Tip**: In Postman, click the **eye icon** next to the response to extract the `access_token` and `refresh_token` values and save them to your environment variables.

---

### 3. Refresh Access Token

**Endpoint**: `POST /api/v1/auth/refresh`

**Purpose**: Get a new access token using a valid refresh token.

**Steps**:
1. Create a new request
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/auth/refresh`
4. Go to **Body** tab → select **raw** → **JSON**
5. Paste the following JSON (replace with your actual refresh token):

```json
{
  "refresh_token": "{{refresh_token}}"
}
```

6. Click **Send**

**Expected Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### 4. Logout

**Endpoint**: `POST /api/v1/auth/logout`

**Purpose**: Logout user and invalidate refresh token.

**Steps**:
1. Create a new request
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/auth/logout`
4. Go to **Body** tab → select **raw** → **JSON**
5. Paste the following JSON:

```json
{
  "refresh_token": "{{refresh_token}}"
}
```

6. Click **Send**

**Expected Response** (200 OK):
```json
{
  "message": "Successfully logged out"
}
```

---

### 5. Request Password Reset

**Endpoint**: `POST /api/v1/auth/password-reset/request`

**Purpose**: Request a password reset token via email.

**Steps**:
1. Create a new request
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/auth/password-reset/request`
4. Go to **Body** tab → select **raw** → **JSON**
5. Paste the following JSON:

```json
{
  "email": "testuser@example.com"
}
```

6. Click **Send**

**Expected Response** (200 OK):
```json
{
  "message": "Password reset requested successfully",
  "reset_token": "token-here"  // Only in development/testing
}
```

---

### 6. Reset Password

**Endpoint**: `POST /api/v1/auth/password-reset/confirm`

**Purpose**: Reset password using a valid reset token.

**Steps**:
1. Create a new request
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/auth/password-reset/confirm`
4. Go to **Body** tab → select **raw** → **JSON**
5. Paste the following JSON (replace with actual token):

```json
{
  "token": "reset-token-here",
  "new_password": "NewSecurePassword123!"
}
```

6. Click **Send**

**Expected Response** (200 OK):
```json
{
  "message": "Password reset successfully"
}
```

---

## Conversation Endpoints

Base URL: `{{base_url}}/api/v1/conversation`

**Note**: These endpoints may require authentication. Add the following header to protected requests:
- **Header**: `Authorization`
- **Value**: `Bearer {{access_token}}`

### 1. List Conversations

**Endpoint**: `GET /api/v1/conversation/conversations`

**Purpose**: Retrieve a list of conversations with optional filters.

**Steps**:
1. Create a new request
2. Set method to `GET`
3. Set URL to `{{base_url}}/api/v1/conversation/conversations`
4. Go to **Params** tab and add optional query parameters:
   - `status`: Filter by status (e.g., `active`, `closed`)
   - `channel`: Filter by channel (e.g., `whatsapp`, `web`)
   - `limit`: Number of results (default: 50, max: 100)
   - `offset`: Pagination offset (default: 0)
5. Add Authorization header if required
6. Click **Send**

**Example URL**:
```
http://localhost:8000/api/v1/conversation/conversations?status=active&channel=whatsapp&limit=10
```

**Expected Response** (200 OK):
```json
[
  {
    "id": "uuid-here",
    "channel": "whatsapp",
    "customer_phone": "+1234567890",
    "customer_name": "John Doe",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### 2. Get Specific Conversation

**Endpoint**: `GET /api/v1/conversation/conversations/{conversation_id}`

**Purpose**: Retrieve details of a specific conversation including messages.

**Steps**:
1. Create a new request
2. Set method to `GET`
3. Set URL to `{{base_url}}/api/v1/conversation/conversations/{conversation_id}`
4. Replace `{conversation_id}` with an actual UUID
5. Add Authorization header if required
6. Click **Send**

**Example URL**:
```
http://localhost:8000/api/v1/conversation/conversations/123e4567-e89b-12d3-a456-426614174000
```

**Expected Response** (200 OK):
```json
{
  "id": "uuid-here",
  "channel": "whatsapp",
  "customer_phone": "+1234567890",
  "customer_name": "John Doe",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "messages": [
    {
      "id": "message-uuid",
      "role": "user",
      "content": "Hello, I'm interested in your product",
      "media_type": null,
      "media_url": null,
      "tokens_used": 15,
      "latency_ms": 250,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### 3. Takeover Conversation

**Endpoint**: `POST /api/v1/conversation/conversations/{conversation_id}/takeover`

**Purpose**: Human agent takes over a conversation from the AI.

**Steps**:
1. Create a new request
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/conversation/conversations/{conversation_id}/takeover`
4. Replace `{conversation_id}` with an actual UUID
5. Go to **Body** tab → select **raw** → **JSON**
6. Paste the following JSON:

```json
{
  "agent_id": "agent-uuid-here"
}
```

7. Add Authorization header
8. Click **Send**

**Expected Response** (200 OK):
```json
{
  "id": "uuid-here",
  "status": "human_handled",
  ...
}
```

---

### 4. Release Conversation

**Endpoint**: `POST /api/v1/conversation/conversations/{conversation_id}/release`

**Purpose**: Return conversation control back to the AI.

**Steps**:
1. Create a new request
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/conversation/conversations/{conversation_id}/release`
4. Replace `{conversation_id}` with an actual UUID
5. Add Authorization header
6. Click **Send**

**Expected Response** (200 OK):
```json
{
  "id": "uuid-here",
  "status": "active",
  ...
}
```

---

## Knowledge Base Endpoints

Base URL: `{{base_url}}/api/v1/knowledge`

**Note**: These endpoints may require authentication.

### 1. Upload Document

**Endpoint**: `POST /api/v1/knowledge/knowledge/upload`

**Purpose**: Upload a document to the knowledge base for indexing.

**Supported File Types**: `pdf`, `docx`, `txt`, `csv`

**Steps**:
1. Create a new request
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/knowledge/knowledge/upload`
4. Go to **Body** tab → select **form-data**
5. Add a key:
   - **Key**: `file`
   - **Type**: File
   - **Value**: Select a file from your computer
6. Add Authorization header
7. Click **Send**

**Expected Response** (200 OK):
```json
{
  "message": "Document uploaded and indexing started.",
  "doc_id": "doc-uuid-here"
}
```

---

### 2. List Documents

**Endpoint**: `GET /api/v1/knowledge/knowledge/docs`

**Purpose**: Retrieve a list of all documents in the knowledge base.

**Steps**:
1. Create a new request
2. Set method to `GET`
3. Set URL to `{{base_url}}/api/v1/knowledge/knowledge/docs`
4. Add Authorization header
5. Click **Send**

**Expected Response** (200 OK):
```json
[
  {
    "id": "doc-uuid-here",
    "filename": "product_catalog.pdf",
    "file_type": "pdf",
    "status": "indexed",
    "uploaded_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### 3. Delete Document

**Endpoint**: `DELETE /api/v1/knowledge/knowledge/docs/{doc_id}`

**Purpose**: Delete a document from the knowledge base.

**Steps**:
1. Create a new request
2. Set method to `DELETE`
3. Set URL to `{{base_url}}/api/v1/knowledge/knowledge/docs/{doc_id}`
4. Replace `{doc_id}` with an actual document UUID
5. Add Authorization header
6. Click **Send**

**Expected Response** (200 OK):
```json
{
  "message": "Document deleted and removed from knowledge base."
}
```

---

### 4. Reindex Document

**Endpoint**: `POST /api/v1/knowledge/knowledge/docs/{doc_id}/reindex`

**Purpose**: Trigger re-indexing of a document.

**Steps**:
1. Create a new request
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/knowledge/knowledge/docs/{doc_id}/reindex`
4. Replace `{doc_id}` with an actual document UUID
5. Add Authorization header
6. Click **Send**

**Expected Response** (200 OK):
```json
{
  "message": "Reindexing started."
}
```

---

## Lead Management Endpoints

Base URL: `{{base_url}}/api/v1/lead`

**Note**: These endpoints may require authentication.

### 1. List Leads

**Endpoint**: `GET /api/v1/lead/leads`

**Purpose**: Retrieve a list of leads with optional filters.

**Steps**:
1. Create a new request
2. Set method to `GET`
3. Set URL to `{{base_url}}/api/v1/lead/leads`
4. Go to **Params** tab and add optional query parameters:
   - `stage`: Filter by stage (e.g., `cold`, `warm`, `hot`, `qualified`, `converted`)
   - `limit`: Number of results (default: 50, max: 100)
   - `offset`: Pagination offset (default: 0)
5. Add Authorization header
6. Click **Send**

**Example URL**:
```
http://localhost:8000/api/v1/lead/leads?stage=warm&limit=20
```

**Expected Response** (200 OK):
```json
[
  {
    "id": "lead-uuid-here",
    "customer_phone": "+1234567890",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "score": 75,
    "stage": "warm",
    "qualification_data": {
      "budget": "high",
      "timeline": "immediate"
    },
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### 2. Get Specific Lead

**Endpoint**: `GET /api/v1/lead/leads/{lead_id}`

**Purpose**: Retrieve details of a specific lead.

**Steps**:
1. Create a new request
2. Set method to `GET`
3. Set URL to `{{base_url}}/api/v1/lead/leads/{lead_id}`
4. Replace `{lead_id}` with an actual UUID
5. Add Authorization header
6. Click **Send**

**Expected Response** (200 OK):
```json
{
  "id": "lead-uuid-here",
  "customer_phone": "+1234567890",
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "score": 75,
  "stage": "warm",
  "qualification_data": {
    "budget": "high",
    "timeline": "immediate"
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### 3. Update Lead Stage

**Endpoint**: `PATCH /api/v1/lead/leads/{lead_id}/stage`

**Purpose**: Update the stage of a lead.

**Valid Stages**: `cold`, `warm`, `hot`, `qualified`, `converted`

**Steps**:
1. Create a new request
2. Set method to `PATCH`
3. Set URL to `{{base_url}}/api/v1/lead/leads/{lead_id}/stage`
4. Replace `{lead_id}` with an actual UUID
5. Go to **Body** tab → select **raw** → **JSON**
6. Paste the following JSON:

```json
{
  "stage": "hot"
}
```

7. Add Authorization header
8. Click **Send**

**Expected Response** (200 OK):
```json
{
  "id": "lead-uuid-here",
  "stage": "hot",
  ...
}
```

---

## Webhook Endpoints

Base URL: `{{base_url}}/api/v1/webhook`

### 1. Verify WhatsApp Webhook

**Endpoint**: `GET /api/v1/webhook/webhooks/whatsapp`

**Purpose**: Verify webhook with Meta (WhatsApp) platform.

**Steps**:
1. Create a new request
2. Set method to `GET`
3. Set URL to `{{base_url}}/api/v1/webhook/webhooks/whatsapp`
4. Go to **Params** tab and add query parameters:
   - `hub.mode`: `subscribe`
   - `hub.challenge`: (provided by Meta)
   - `hub.verify_token`: (configured in your environment)
5. Click **Send**

**Example URL**:
```
http://localhost:8000/api/v1/webhook/webhooks/whatsapp?hub.mode=subscribe&hub.challenge=CHALLENGE_CODE&hub.verify_token=YOUR_VERIFY_TOKEN
```

**Expected Response** (200 OK):
```
CHALLENGE_CODE
```

---

### 2. Receive WhatsApp Webhook

**Endpoint**: `POST /api/v1/webhook/webhooks/whatsapp`

**Purpose**: Receive incoming messages from WhatsApp.

**Steps**:
1. Create a new request
2. Set method to `POST`
3. Set URL to `{{base_url}}/api/v1/webhook/webhooks/whatsapp`
4. Go to **Headers** tab and add:
   - **Key**: `X-Hub-Signature-256`
   - **Value**: HMAC-SHA256 signature (computed by Meta)
5. Go to **Body** tab → select **raw** → **JSON**
6. Paste a sample WhatsApp webhook payload:

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "123456789",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "+1234567890",
              "phone_number_id": "123456789"
            },
            "contacts": [
              {
                "profile": {
                  "name": "John Doe"
                }
              }
            ],
            "messages": [
              {
                "from": "+1987654321",
                "id": "wamid.ID",
                "timestamp": "1234567890",
                "type": "text",
                "text": {
                  "body": "Hello, I'm interested in your product"
                }
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

7. Click **Send**

**Expected Response** (200 OK):
```json
{
  "status": "ok"
}
```

---

## Postman Collection Setup

To organize your API tests, create a Postman collection:

1. Click **Collections** → **Create Collection**
2. Name it: `Sales Agent API`
3. Create folders for each endpoint group:
   - Authentication
   - Conversations
   - Knowledge Base
   - Lead Management
   - Webhooks
4. Add requests to appropriate folders
5. Set collection-level variables:
   - `base_url`: `http://localhost:8000`
6. Add authentication at collection level:
   - Type: `Bearer Token`
   - Token: `{{access_token}}`

---

## Troubleshooting

### Common Issues

**1. Connection Refused**
- Ensure the API server is running
- Check that the port (default: 8000) is correct
- Verify firewall settings

**2. 401 Unauthorized**
- Ensure you have a valid access token
- Check that the Authorization header is set correctly: `Bearer {{access_token}}`
- Token may have expired - use the refresh endpoint

**3. 403 Forbidden**
- Verify your user has the required permissions
- Check that the verify token is correct for webhook verification

**4. 422 Validation Error**
- Check request body matches the expected schema
- Ensure all required fields are present
- Verify data types (e.g., email format, UUID format)

**5. 500 Internal Server Error**
- Check server logs for detailed error messages
- Ensure all dependencies (Database, RabbitMQ) are running
- Verify environment variables are configured correctly

---

## Additional Resources

- **FastAPI Documentation**: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- **Postman Learning Center**: [https://learning.postman.com/](https://learning.postman.com/)
- **Project Documentation**: Check the `docs/` directory for additional guides

---

## Quick Reference

| Endpoint | Method | Auth Required |
|----------|--------|---------------|
| `/api/v1/auth/register` | POST | No |
| `/api/v1/auth/login` | POST | No |
| `/api/v1/auth/refresh` | POST | No |
| `/api/v1/auth/logout` | POST | No |
| `/api/v1/auth/password-reset/request` | POST | No |
| `/api/v1/auth/password-reset/confirm` | POST | No |
| `/api/v1/conversation/conversations` | GET | Yes |
| `/api/v1/conversation/conversations/{id}` | GET | Yes |
| `/api/v1/conversation/conversations/{id}/takeover` | POST | Yes |
| `/api/v1/conversation/conversations/{id}/release` | POST | Yes |
| `/api/v1/knowledge/knowledge/upload` | POST | Yes |
| `/api/v1/knowledge/knowledge/docs` | GET | Yes |
| `/api/v1/knowledge/knowledge/docs/{id}` | DELETE | Yes |
| `/api/v1/knowledge/knowledge/docs/{id}/reindex` | POST | Yes |
| `/api/v1/lead/leads` | GET | Yes |
| `/api/v1/lead/leads/{id}` | GET | Yes |
| `/api/v1/lead/leads/{id}/stage` | PATCH | Yes |
| `/api/v1/webhook/webhooks/whatsapp` | GET | No |
| `/api/v1/webhook/webhooks/whatsapp` | POST | No |

---

**Last Updated**: 2024-06-07
