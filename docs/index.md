# Documentation Index — AI Sales Agent

All project documentation in one place. Start here.

---

## Product

Business-facing documents. No technical jargon — what we're building and why.

| Document | Description |
|----------|-------------|
| [Product Overview](product/product-overview.md) | Problem, solution, phases, business model — the full pitch |

---

## Architecture

Technical design decisions and system-level documentation.

| Document | Description |
|----------|-------------|
| [RAG Pipeline](architecture/rag-pipeline.md) | How document upload → chunking → embedding → retrieval works end-to-end |
| [LangGraph Migration Analysis](architecture/langgraph-migration.md) | Should we use LangGraph? Analysis and recommendation (decision: not yet) |

---

## Testing

How to test the system manually and verify features work.

| Document | Description |
|----------|-------------|
| [API Testing with Postman](testing/api-testing-postman.md) | Step-by-step Postman guide for all API endpoints |

---

## Development

Implementation guides for specific engineering tasks.

| Document | Description |
|----------|-------------|
| [Channel Abstraction](development/channel-abstraction-implementation.md) | End-to-end guide: how every layer changed to support WhatsApp, Instagram, Telegram, and web chat |

---

## Roadmap

What needs to change and in what order.

| Document | Description |
|----------|-------------|
| [Improvement Roadmap](roadmap/improvement-roadmap.md) | 7 prioritised improvements with implementation steps — **start here** |
| [Production Architecture Review](roadmap/production-architecture-review.md) | Full production readiness review (score 4/10), long-term gaps |

---

## Where to Start Based on Your Goal

| Goal | Read This |
|------|-----------|
| Understand the product vision | [Product Overview](product/product-overview.md) |
| Understand how RAG works end-to-end | [RAG Pipeline](architecture/rag-pipeline.md) |
| Know what to improve next | [Improvement Roadmap](roadmap/improvement-roadmap.md) |
| Test the current API | [API Testing with Postman](testing/api-testing-postman.md) |
| Plan long-term production work | [Production Architecture Review](roadmap/production-architecture-review.md) |
