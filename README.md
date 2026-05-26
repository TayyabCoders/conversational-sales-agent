# 🤖 Conversational Sales Agent

An enterprise-grade AI sales automation platform that enables businesses to deploy human-like AI agents across WhatsApp, Instagram, Facebook Messenger, and website chat.

The platform uses Retrieval-Augmented Generation (RAG), conversation memory, and multi-channel orchestration to automate lead qualification, appointment booking, customer engagement, and support workflows — 24/7.

**FastAPI · Multi‑Tenant · RAG‑Powered AI Sales Agent**  
Deploy human‑like AI agents on WhatsApp, Instagram, Facebook Messenger, and your website – 24/7 lead qualification, appointment booking, and customer support.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql)](https://www.postgresql.org)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.9+-purple?logo=qdrant)](https://qdrant.tech)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.13-FF6600?logo=rabbitmq)](https://www.rabbitmq.com)

---

## 🚀 Overview

The **Conversational Sales Agent** is a production‑ready, multi‑tenant SaaS platform that lets service‑based businesses deploy an AI sales agent across messaging channels. The agent learns from uploaded business documents (pricing, FAQs, policies) and holds human‑like conversations – qualifying leads, handling objections, booking appointments, and escalating to humans when needed.

Built with **FastAPI**, **PostgreSQL**, **Qdrant** (vector DB), **RabbitMQ** (async messaging), the platform scales from a single business to thousands of tenants.

---

## ✨ Core Features (Phase 1 MVP)

- 🔌 **WhatsApp Business API** – receive/send messages with typing indicators
- 🧠 **RAG Pipeline** – retrieve relevant business knowledge before generating responses
- 💬 **Conversation Memory** – Redis for hot session cache, PostgreSQL for history
- 🧑‍💼 **Human Handoff** – auto‑escalate complex queries to human agents
- 📄 **Knowledge Base** – upload PDF, DOCX, TXT, CSV; automatic chunking & embedding
- 🎭 **Human‑like Behavior** – realistic typing delays, short messages, one question at a time
- 🔐 **Multi‑Tenant** – `tenant_id` isolation at application + database (RLS ready)
- 🐳 **Docker Compose** – one‑command local development environment

---

## 🧱 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI 0.115+ (async), Uvicorn + Gunicorn |
| **ORM** | SQLAlchemy 2.0 (async) + Alembic migrations |
| **Message Queue** | RabbitMQ 3.13 (aio‑pika) – replaces Celery |
| **Cache** | Redis 7 (session cache, rate limiting) |
| **Database** | PostgreSQL 16 (asyncpg) |
| **Vector DB** | Qdrant 1.9+ (self‑hosted) |
| **LLM** | OpenAI GPT‑4o (primary) + optional Claude / Groq |
| **Embeddings** | `text‑embedding‑3‑small` (1536 dims) |
| **Frontend** | Next.js 14 (App Router) + shadcn/ui + Tailwind |
| **Infrastructure** | Docker Compose (dev) → AWS ECS/EKS (prod) |

---

## 🐳 Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose (or Podman)
- Python 3.12+ (for local development without Docker)
- OpenAI API key

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/conversational-sales-agent.git
   cd conversational-sales-agent
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env – add your OPENAI_API_KEY, Meta WhatsApp credentials, etc.
   ```

3. **Launch all services**
   ```bash
   docker-compose up -d
   ```
   This starts:
   - PostgreSQL (port 5432)
   - Redis (6379)
   - RabbitMQ (5672 – AMQP, 15672 – management UI)
   - Qdrant (6333)
   - FastAPI backend (8000)
   - RabbitMQ consumer workers (AI inference + outbound)

4. **Run database migrations**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

5. **Access the services**
   - API docs: http://localhost:8000/docs
   - RabbitMQ management: http://localhost:15672 (guest/guest)
   - Qdrant dashboard: http://localhost:6333/dashboard

6. **Stop everything**
   ```bash
   docker-compose down -v   # -v removes volumes (reset data)
   ```

---

## 🔧 Configuration (`env.example`)

```ini
# App
APP_NAME=Conversational Sales Agent
DEBUG=false
SECRET_KEY=change_this_in_production

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/sales_agent

# Redis
REDIS_URL=redis://redis:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=agent_knowledge

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# WhatsApp (Meta Cloud API)
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_VERIFY_TOKEN=...
```

---

## 🧠 How the AI Agent Works (RAG Pipeline)

1. **Customer message** arrives via webhook → published to RabbitMQ `inbound` queue.
2. **Consumer** picks up the message:
   - Loads conversation memory (last N messages from Redis)
   - Retrieves relevant knowledge chunks from Qdrant (tenant‑filtered)
   - Builds system prompt (persona, business rules, RAG context)
   - Calls model to generate response
   - Applies guardrails (hallucination check, PII filter)
3. **Response** is published to `outbound` queue.
4. **Outbound consumer** sends via WhatsApp (or WebSocket) with human‑like typing delay.
5. **Conversation & lead score** are persisted to PostgreSQL.

All steps are **async** and non‑blocking – the webhook returns `200 OK` immediately.

---

## 🤝 Human Handoff

When a customer asks for a human, the AI triggers an escalation:
- Conversation status becomes `escalated`
- Real‑time notification sent to dashboard (WebSocket) + email
- Human agent takes over from the admin UI
- AI pauses for that conversation until manually resumed

---

## 📄 License

MIT – feel free to use it for your own SaaS or contribute back.

---

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com) – the Python async web framework
- [LangChain](https://www.langchain.com) – LLM orchestration (optional, we use direct OpenAI + custom RAG)
- [Qdrant](https://qdrant.tech) – vector database
- [RabbitMQ](https://www.rabbitmq.com) – message broker
- [Meta WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)

---

**Built with ❤️ for sales teams that never sleep.**
```
