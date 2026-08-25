# 🏦 Mutual Fund FAQ Assistant

A **facts-only** chatbot that answers factual questions about HDFC mutual fund schemes using Retrieval-Augmented Generation (RAG). It retrieves sourced data from official pages, provides concise answers (≤ 3 sentences), and includes citation links — while strictly refusing investment advice.

---

## ✨ Scope & Features

- **Facts-Only Responses** — Concise, source-cited answers with no opinions or recommendations.
- **Corpus (15 URLs)** — Scrapes 5 HDFC schemes (Mid-Cap Opportunities, Small Cap, Gold ETF FoF, Top 100, ELSS Tax Saver) and 10 Groww Mutual Fund Help Center articles (covering taxation, statements, and core concepts). See `sources.csv`.
- **Guardrails** — Detects and refuses advisory queries, PII, and prompt injection attempts.
- **Source Transparency** — Every response includes a citation link and "Last updated" date.
- **Modern Chat UI** — Dark-themed glassmorphism interface with example questions and a strict disclaimer snippet.

---

## 🏗️ Architecture

| Layer | Technology |
|---|---|
| **Frontend** | HTML / CSS / Vanilla JS |
| **API** | FastAPI + Uvicorn |
| **LLM** | Groq API (LLaMA 3.3 70B) |
| **Embeddings** | sentence-transformers (`all-MiniLM-L6-v2`) |
| **Vector Store** | ChromaDB (local persistence) |
| **Data Source** | Groww.in (web scraping) |

> See [`docs/architecture.md`](docs/architecture.md) for the full system design.

---

## 📁 Project Structure

```
chatbot/
├── backend/
│   ├── api/               # FastAPI app, routes, schemas
│   ├── core/              # Guardrails, query preprocessing, response generator
│   ├── ingestion/         # Scraper, chunker, embedder
│   ├── vectorstore/       # ChromaDB client wrapper
│   ├── config/            # Settings (pydantic-settings) & prompt templates
│   ├── data/              # Raw JSON + ChromaDB persistence
│   ├── tests/             # Unit & integration tests
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py             # Uvicorn startup
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── scripts/
│   └── ingest.py          # One-shot data ingestion
├── docs/                  # Architecture, implementation plan, etc.
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com/)

### 1. Clone & Setup

```bash
git clone <repo-url>
cd chatbot
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows
```

### 3. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure Environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and add your GROQ_API_KEY
```

### 5. Ingest Data

```bash
python scripts/ingest.py
```

### 6. Start the Backend

```bash
python backend/run.py
# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### 7. Start the Frontend

Open `frontend/index.html` with a local server (e.g., VS Code Live Server on port 5500).

---

## 📚 Documentation

| Document | Description |
|---|---|
| [`docs/problemStatement.md`](docs/problemStatement.md) | Project requirements & constraints |
| [`docs/architecture.md`](docs/architecture.md) | Full system architecture |
| [`docs/implementation-plan.md`](docs/implementation-plan.md) | Phased implementation plan |
| [`docs/edge-cases.md`](docs/edge-cases.md) | Edge case handling |
| [`docs/eval.md`](docs/eval.md) | Evaluation methodology |

---

## ⚠️ Known Limits

- **Limited Scope:** The bot only knows about 5 HDFC schemes. Asking about a Nippon India or Tata fund will result in a graceful fallback.
- **No Predictive Capabilities:** The bot cannot calculate expected returns, compare historical performance to future projections, or advise on portfolio allocation.
- **Static Ingestion:** The ChromaDB vector store is populated at container start time via scraping. Real-time intraday NAV updates are not continuously polled.

---

## ⚖️ UI Disclaimer Snippet

The following facts-only disclaimer is permanently affixed to the bottom of the chat interface as per the project requirements:
> *"Facts-only. No investment advice. Verify details with official AMC documents before investing."*

Additionally, the assistant strictly refuses advisory queries and directs users to SEBI/AMFI.
---

## 📄 License

This project is for educational purposes.
