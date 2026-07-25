# API Testing Guide — Postman

This guide walks through every API endpoint in the correct **operational order**: authenticate first, configure your channel, upload knowledge, then test the live message flow.

---

## Table of Contents

1. [Prerequisites & Setup](#1-prerequisites--setup)
2. [Authentication](#2-authentication)
3. [Channel Management](#3-channel-management)
4. [Knowledge Base](#4-knowledge-base)
5. [Webhook — Verify & Test](#5-webhook--verify--test)
6. [Conversations](#6-conversations)
7. [Lead Management](#7-lead-management)
8. [Quick Reference](#quick-reference)
9. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites & Setup

**Required services running:**
- API server (default: `http://localhost:8000`)
- PostgreSQL + RabbitMQ + Redis

**Start the server:**
```bash
python -m app.main
```

**Interactive API docs:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Postman Environment

Create an environment named `Sales Agent API` with these variables:

| Variable | Initial Value | Description |
|---|---|---|
| `base_url` | `http://localhost:8000` | API base URL |
| `access_token` | *(empty)* | Set after login |
| `refresh_token` | *(empty)* | Set after login |
| `channel_id` | *(empty)* | Set after listing channels |

Set the collection-level **Authorization** to:
- Type: `Bearer Token`
- Token: `{{access_token}}`

---

## 2. Authentication

> **Do this first.** All subsequent requests need `{{access_token}}` in the Authorization header.

### 2.1 Register

**`POST /api/v1/auth/register`**

```json
{
  "username": "admin",
  "email": "admin@example.com",
  "password": "SecurePassword123!"
}
```

Expected response `201 Created`:
```json
{
  "id": "uuid-here",
  "username": "admin",
  "email": "admin@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### 2.2 Login ← **Save the tokens**

**`POST /api/v1/auth/login`**

```json
{
  "email": "admin@example.com",
  "password": "SecurePassword123!"
}
```

Expected response `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Action:** Copy both values into the Postman environment variables `access_token` and `refresh_token`.

---

### 2.3 Refresh Access Token

**`POST /api/v1/auth/refresh`**

Use this when the access token expires (default TTL: 30 min).

```json
{
  "refresh_token": "{{refresh_token}}"
}
```

Expected response `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### 2.4 Logout

**`POST /api/v1/auth/logout`**

```json
{
  "refresh_token": "{{refresh_token}}"
}
```

Expected response `200 OK`:
```json
{
  "message": "Successfully logged out"
}
```

---

### 2.5 Request Password Reset

**`POST /api/v1/auth/password-reset/request`**

```json
{
  "email": "admin@example.com"
}
```

Expected response `200 OK`:
```json
{
  "message": "Password reset requested successfully",
  "reset_token": "token-here"
}
```

---

### 2.6 Confirm Password Reset

**`POST /api/v1/auth/password-reset/confirm`**

```json
{
  "token": "reset-token-here",
  "new_password": "NewSecurePassword123!"
}
```

Expected response `200 OK`:
```json
{
  "message": "Password reset successfully"
}
```

---

## 3. Channel Management

> **Do this second.** A channel record must exist in the database before webhooks can receive messages. A default WhatsApp channel is seeded by the migration, but you must set its credentials.

**Header required:** `Authorization: Bearer {{access_token}}`

### 3.1 List Channels ← **Save the channel ID**

**`GET /api/v1/channel/channels`**

Expected response `200 OK`:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "whatsapp",
    "name": "Default WhatsApp",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Action:** Copy the `id` value into the Postman environment variable `channel_id`.

> **Note:** The `config` field (which contains credentials) is intentionally excluded from all responses for security.

---

### 3.2 Get Your WhatsApp Credentials from Meta

Before you can configure the channel, you need four values from Meta. Here is the full step-by-step process to get them.

---

#### Step A — Create a Facebook Business Account

1. Go to **[business.facebook.com](https://business.facebook.com)**
2. Click **Create Account**
3. Fill in your business name, your name, and your business email
4. Verify your email

> If you already have a Facebook personal account, you can use it to create a Business account — they are separate things.

---

#### Step B — Create a Meta Developer Account

1. Go to **[developers.facebook.com](https://developers.facebook.com)**
2. Click **Get Started** (top right)
3. Log in with your Facebook account
4. Accept the Meta Platform Policies
5. You are now a Meta developer

---

#### Step C — Create a Meta App

1. From the Meta Developer dashboard, click **My Apps → Create App**
2. For **Use case**, select **Other** → click **Next**
3. For **App type**, select **Business** → click **Next**
4. Fill in:
   - **App name**: e.g., `Sales Agent`
   - **App contact email**: your email
   - **Business account**: select the one you created in Step A
5. Click **Create App**

---

#### Step D — Add WhatsApp to Your App

1. Inside your new app dashboard, scroll down to find **WhatsApp**
2. Click **Set up** on the WhatsApp card
3. You are now in the **WhatsApp Getting Started** section

---

#### Step E — Get `phone_number_id` and Temporary `access_token`

1. In the left sidebar: **WhatsApp → API Setup**
2. Under **Step 1 — Select phone numbers**, you will see a test phone number already provided by Meta (free, no SIM required for testing)
3. From this page, note down:

   - **Phone Number ID** → shown just below the "From" dropdown (looks like: `102938475612345`)
   - **Temporary access token** → shown in the box under "Step 1". Click the copy button.

> **Important:** The temporary token expires in **24 hours**. It is fine for testing, but you need a permanent token for production (see Step F below).

---

#### Step F — Create a Permanent `access_token` (for Production)

1. Go to **[business.facebook.com/settings](https://business.facebook.com/settings)**
2. In the left sidebar: **Users → System Users**
3. Click **Add** → name it `sales-agent-bot` → Role: **Admin** → **Create System User**
4. Click **Generate New Token**:
   - Select your app from the dropdown
   - Permissions to enable: `whatsapp_business_messaging`, `whatsapp_business_management`
   - Click **Generate Token**
5. **Copy and save this token immediately** — Meta only shows it once

This token does not expire.

---

#### Step G — Get `app_secret`

1. In your app dashboard, go to **Settings → Basic** (left sidebar)
2. Find the **App Secret** field → click **Show**
3. Enter your Facebook password to reveal it
4. Copy the value (looks like: `abc123def456...`)

---

#### Step H — Choose Your `verify_token`

The `verify_token` is **not given by Meta — you create it yourself**. It is any string you choose. Meta sends it back to your server when verifying the webhook, and your server checks that it matches.

Pick any string, for example:
```
my-sales-agent-webhook-2024
```

Write it down — you will enter the same string in both Meta's dashboard and your channel config.

---

#### Step I — Expose Your Local Server (for Testing)

Meta's webhook verification requires a **public HTTPS URL**. For local development, use **ngrok**:

1. Install ngrok: [ngrok.com/download](https://ngrok.com/download)
2. Run:
   ```bash
   ngrok http 8000
   ```
3. Copy the generated HTTPS URL, e.g.: `https://abc123.ngrok-free.app`
4. Your webhook URL will be:
   ```
   https://abc123.ngrok-free.app/api/v1/webhook/webhooks/whatsapp
   ```

> For production, use your real domain with a valid SSL certificate.

---

#### Step J — Register the Webhook URL in Meta Dashboard

1. In your app dashboard: **WhatsApp → Configuration** (left sidebar)
2. Under **Webhook**, click **Edit**
3. Fill in:
   - **Callback URL**: `https://your-ngrok-url.ngrok-free.app/api/v1/webhook/webhooks/whatsapp`
   - **Verify token**: the string you chose in Step H
4. Click **Verify and save** — Meta will call your server's GET endpoint to verify
5. After saving, click **Manage** next to Webhook fields
6. Enable the **`messages`** subscription checkbox → click **Done**

---

#### Summary — Your Credentials

You now have everything needed:

| Config Key | Where it comes from |
|---|---|
| `phone_number_id` | WhatsApp → API Setup → shown under "From" dropdown |
| `access_token` | Temp: WhatsApp → API Setup. Permanent: Business Settings → System Users |
| `app_secret` | App Dashboard → Settings → Basic → App Secret |
| `verify_token` | You chose this in Step H |
| `api_version` | Use `v20.0` (or check [developers.facebook.com/docs/whatsapp](https://developers.facebook.com/docs/whatsapp) for latest) |

---

### 3.2 Configure Channel Credentials

**`PATCH /api/v1/channel/channels/{{channel_id}}`**

Now paste the credentials you collected above into the request body:

```json
{
  "config": {
    "phone_number_id": "102938475612345",
    "access_token": "EAABsbCS...",
    "app_secret": "abc123def456...",
    "verify_token": "my-sales-agent-webhook-2024",
    "api_version": "v20.0"
  }
}
```

Expected response `200 OK`:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "whatsapp",
  "name": "Default WhatsApp",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

> The config is stored in the database and excluded from all API responses for security. Only the server can read it internally.

---

### 3.3 Get Specific Channel

**`GET /api/v1/channel/channels/{{channel_id}}`**

Expected response `200 OK`:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "whatsapp",
  "name": "Default WhatsApp",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### 3.4 Create a New Channel

**`POST /api/v1/channel/channels`**

Use this to add additional channels (e.g., a second WhatsApp number, Instagram, Telegram).

```json
{
  "type": "whatsapp",
  "name": "Support Line",
  "config": {
    "phone_number_id": "SECOND_PHONE_NUMBER_ID",
    "access_token": "SECOND_ACCESS_TOKEN",
    "app_secret": "SECOND_APP_SECRET",
    "verify_token": "SECOND_VERIFY_TOKEN",
    "api_version": "v20.0"
  }
}
```

Valid `type` values: `whatsapp`, `instagram`, `telegram`, `web`

Expected response `201 Created`:
```json
{
  "id": "new-channel-uuid",
  "type": "whatsapp",
  "name": "Support Line",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### 3.5 Deactivate or Rename a Channel

**`PATCH /api/v1/channel/channels/{{channel_id}}`**

```json
{
  "name": "Primary WhatsApp Line",
  "is_active": false
}
```

---

### 3.6 Delete a Channel

**`DELETE /api/v1/channel/channels/{{channel_id}}`**

Expected response `200 OK`:
```json
{
  "message": "Channel deleted"
}
```

> **Warning:** Deleting a channel that has existing conversations will fail due to the foreign key constraint. Deactivate (`is_active: false`) instead of deleting in production.

---

## 4. Knowledge Base

> **Do this before testing messages.** Documents uploaded here are indexed into the vector store (Qdrant) and retrieved by the AI when answering customer questions.

**Header required:** `Authorization: Bearer {{access_token}}`

**Supported file types:** `pdf`, `docx`, `txt`, `csv`

### 4.1 Upload a Document

**`POST /api/v1/knowledge/knowledge/upload`**

In Postman, use **Body → form-data**:

| Key | Type | Value |
|---|---|---|
| `file` | File | Select your file |

Expected response `200 OK`:
```json
{
  "message": "Document uploaded and indexing started.",
  "doc_id": "doc-uuid-here"
}
```

Indexing happens asynchronously. Use List Documents (step 4.2) to check `status`.

---

### 4.2 List Documents

**`GET /api/v1/knowledge/knowledge/docs`**

Expected response `200 OK`:
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

`status` values: `pending` → `indexing` → `indexed` (or `failed`)

---

### 4.3 Reindex a Document

**`POST /api/v1/knowledge/knowledge/docs/{doc_id}/reindex`**

Use after updating the source document.

Expected response `200 OK`:
```json
{
  "message": "Reindexing started."
}
```

---

### 4.4 Delete a Document

**`DELETE /api/v1/knowledge/knowledge/docs/{doc_id}`**

Removes the DB record and all associated vector chunks from Qdrant.

Expected response `200 OK`:
```json
{
  "message": "Document deleted and removed from knowledge base."
}
```

---

## 5. Webhook — Verify & Test

> **Do this after channel credentials are configured (Step 3.2).** The webhook URL to register in the Meta dashboard is:
> `https://yourdomain.com/api/v1/webhook/webhooks/whatsapp`

No authentication header needed on webhook endpoints — they are called by Meta.

### 5.1 Verify Webhook Subscription

**`GET /api/v1/webhook/webhooks/whatsapp`**

Meta sends this GET request when you save the webhook URL in their dashboard. Test it manually in Postman to confirm your verify token is correct.

**Query parameters:**

| Param | Value |
|---|---|
| `hub.mode` | `subscribe` |
| `hub.challenge` | `CHALLENGE_CODE` |
| `hub.verify_token` | Your verify token (set in Step 3.2 config) |

Example URL:
```
http://localhost:8000/api/v1/webhook/webhooks/whatsapp?hub.mode=subscribe&hub.challenge=12345&hub.verify_token=YOUR_VERIFY_TOKEN
```

Expected response `200 OK` (plain text):
```
12345
```

---

### 5.2 Simulate an Inbound WhatsApp Message

**`POST /api/v1/webhook/webhooks/whatsapp`**

**Headers:**

| Key | Value |
|---|---|
| `X-Hub-Signature-256` | `sha256=HMAC_SIGNATURE` (computed from body + app_secret) |
| `Content-Type` | `application/json` |

**Body (raw JSON):**
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
                "id": "wamid.TEST_MESSAGE_ID",
                "timestamp": "1700000000",
                "type": "text",
                "text": {
                  "body": "Hi, I'm interested in a Dubai travel package for 2 people in December"
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

Expected response `200 OK`:
```json
{
  "status": "ok"
}
```

**What happens next (async):**
1. Webhook returns `200 ok` immediately (< 1 second)
2. RabbitMQ consumer picks up the message
3. AI pipeline runs: RAG retrieval → Gemini/OpenAI generates reply
4. Reply is sent back to the customer via WhatsApp
5. Conversation and lead records are created/updated in the DB

After sending, wait ~3–10 seconds then check Conversations (Step 6) to see the result.

> **Local testing tip:** To skip signature verification during local development, you can temporarily bypass the signature check. In production, always compute a real `X-Hub-Signature-256`.

---

## 6. Conversations

**Header required:** `Authorization: Bearer {{access_token}}`

### 6.1 List Conversations

**`GET /api/v1/conversation/conversations`**

**Optional query parameters:**

| Param | Type | Example |
|---|---|---|
| `status` | string | `active`, `escalated`, `human_handled`, `closed` |
| `channel` | string | `whatsapp`, `instagram` — filters by channel type |
| `limit` | int | `50` (default) |
| `offset` | int | `0` (default) |

Example:
```
GET /api/v1/conversation/conversations?status=active&channel=whatsapp&limit=10
```

Expected response `200 OK`:
```json
[
  {
    "id": "conv-uuid-here",
    "channel_id": "550e8400-e29b-41d4-a716-446655440000",
    "customer_identifier": "+1987654321",
    "customer_name": "John Doe",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "messages": []
  }
]
```

---

### 6.2 Get Conversation with Messages

**`GET /api/v1/conversation/conversations/{conversation_id}`**

Example URL:
```
GET /api/v1/conversation/conversations/conv-uuid-here
```

Expected response `200 OK`:
```json
{
  "id": "conv-uuid-here",
  "channel_id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_identifier": "+1987654321",
  "customer_name": "John Doe",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "messages": [
    {
      "id": "msg-uuid",
      "role": "user",
      "content": "Hi, I'm interested in a Dubai travel package for 2 people in December",
      "media_type": null,
      "media_url": null,
      "tokens_used": 18,
      "latency_ms": 0,
      "created_at": "2024-01-01T00:00:01Z"
    },
    {
      "id": "msg-uuid-2",
      "role": "assistant",
      "content": "Hello John! Dubai in December is a fantastic choice...",
      "media_type": null,
      "media_url": null,
      "tokens_used": 145,
      "latency_ms": 2340,
      "created_at": "2024-01-01T00:00:06Z"
    }
  ]
}
```

---

### 6.3 Human Takeover

**`POST /api/v1/conversation/conversations/{conversation_id}/takeover`**

Pauses AI responses and marks the conversation for human handling.

```json
{
  "agent_id": "agent-uuid-here"
}
```

Expected response `200 OK`:
```json
{
  "id": "conv-uuid-here",
  "status": "human_handled"
}
```

---

### 6.4 Release Back to AI

**`POST /api/v1/conversation/conversations/{conversation_id}/release`**

Returns control to the AI agent.

Expected response `200 OK`:
```json
{
  "id": "conv-uuid-here",
  "status": "active"
}
```

---

## 7. Lead Management

**Header required:** `Authorization: Bearer {{access_token}}`

Leads are created automatically when a new customer sends their first message. The AI scorer updates `score` and `stage` on every message based on detected signals (pricing questions, destination mentions, travel dates, etc.).

### 7.1 List Leads

**`GET /api/v1/lead/leads`**

**Optional query parameters:**

| Param | Type | Values |
|---|---|---|
| `stage` | string | `cold`, `warm`, `hot`, `qualified`, `converted` |
| `limit` | int | `50` (default) |
| `offset` | int | `0` (default) |

Example:
```
GET /api/v1/lead/leads?stage=hot&limit=20
```

Expected response `200 OK`:
```json
{
  "data": [
    {
      "id": "lead-uuid-here",
      "customer_identifier": "+1987654321",
      "customer_name": "John Doe",
      "customer_email": null,
      "score": 75,
      "stage": "hot",
      "qualification_data": {
        "budget": "high",
        "timeline": "immediate"
      },
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

**Score → Stage mapping:**

| Score | Stage |
|---|---|
| 86–100 | `qualified` |
| 61–85 | `hot` |
| 31–60 | `warm` |
| 0–30 | `cold` |

---

### 7.2 Get Specific Lead

**`GET /api/v1/lead/leads/{lead_id}`**

Expected response `200 OK`:
```json
{
  "id": "lead-uuid-here",
  "customer_identifier": "+1987654321",
  "customer_name": "John Doe",
  "customer_email": null,
  "score": 75,
  "stage": "hot",
  "qualification_data": {},
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### 7.3 Manually Update Lead Stage

**`PATCH /api/v1/lead/leads/{lead_id}/stage`**

Override the AI-computed stage (e.g., after a sales call).

```json
{
  "stage": "converted"
}
```

Valid stages: `cold`, `warm`, `hot`, `qualified`, `converted`

Expected response `200 OK`:
```json
{
  "message": "Lead stage updated to converted"
}
```

---

## Quick Reference

### Endpoint Map

| # | Endpoint | Method | Auth |
|---|---|---|---|
| 2.1 | `/api/v1/auth/register` | POST | No |
| 2.2 | `/api/v1/auth/login` | POST | No |
| 2.3 | `/api/v1/auth/refresh` | POST | No |
| 2.4 | `/api/v1/auth/logout` | POST | No |
| 2.5 | `/api/v1/auth/password-reset/request` | POST | No |
| 2.6 | `/api/v1/auth/password-reset/confirm` | POST | No |
| 3.1 | `/api/v1/channel/channels` | GET | Yes |
| 3.2 | `/api/v1/channel/channels/{id}` | PATCH | Yes |
| 3.3 | `/api/v1/channel/channels/{id}` | GET | Yes |
| 3.4 | `/api/v1/channel/channels` | POST | Yes |
| 3.5 | `/api/v1/channel/channels/{id}` | PATCH | Yes |
| 3.6 | `/api/v1/channel/channels/{id}` | DELETE | Yes |
| 4.1 | `/api/v1/knowledge/knowledge/upload` | POST | Yes |
| 4.2 | `/api/v1/knowledge/knowledge/docs` | GET | Yes |
| 4.3 | `/api/v1/knowledge/knowledge/docs/{id}/reindex` | POST | Yes |
| 4.4 | `/api/v1/knowledge/knowledge/docs/{id}` | DELETE | Yes |
| 5.1 | `/api/v1/webhook/webhooks/whatsapp` | GET | No |
| 5.2 | `/api/v1/webhook/webhooks/whatsapp` | POST | No |
| 6.1 | `/api/v1/conversation/conversations` | GET | Yes |
| 6.2 | `/api/v1/conversation/conversations/{id}` | GET | Yes |
| 6.3 | `/api/v1/conversation/conversations/{id}/takeover` | POST | Yes |
| 6.4 | `/api/v1/conversation/conversations/{id}/release` | POST | Yes |
| 7.1 | `/api/v1/lead/leads` | GET | Yes |
| 7.2 | `/api/v1/lead/leads/{id}` | GET | Yes |
| 7.3 | `/api/v1/lead/leads/{id}/stage` | PATCH | Yes |

### Recommended Testing Order

```
Login (2.2)
  → List Channels (3.1) — grab channel_id
  → Configure Channel Credentials (3.2) — set phone_number_id / access_token / etc.
  → Upload Knowledge Document (4.1) — wait for status = "indexed"
  → Verify Webhook (5.1) — confirm verify_token works
  → Simulate Inbound Message (5.2) — triggers full AI pipeline
  → List Conversations (6.1) — see conversation created
  → Get Conversation (6.2) — verify AI replied
  → List Leads (7.1) — see auto-created lead with score
```

---

## Troubleshooting

**`404 No active channel of type 'whatsapp' registered`**
- The `channels` table is empty or has no active WhatsApp channel.
- Run `alembic upgrade head` to apply migrations (which seed the default channel).
- Then call Step 3.1 to confirm the channel exists.

**`403` on webhook verification**
- The `hub.verify_token` doesn't match the `verify_token` stored in the channel's `config`.
- Update the channel via Step 3.2 and retry.

**`401 Unauthorized`**
- Access token is expired. Use Step 2.3 (refresh) to get a new one and update the environment variable.

**`422 Validation Error`**
- Check that your request body matches the schema exactly.
- Inspect the `detail` array in the response — FastAPI lists every validation failure.

**`500 Internal Server Error`**
- Check server logs for the full traceback.
- Ensure PostgreSQL, RabbitMQ, and Redis are all running.
- Verify all required environment variables are set.

**AI reply not arriving (message sends `200 ok` but no WhatsApp reply)**
- Check RabbitMQ is running and the `ai.messages.queue` is consuming.
- Check server logs for errors in the AI consumer (`ai_message_consumer`).
- Confirm the channel `config` has a valid `access_token` and `phone_number_id`.

---

*Last updated: 2026-07-26*
