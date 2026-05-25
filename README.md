# 🧠 CodeIntel Core: Distributed Codebase Intelligence Platform

CodeIntel Core is an enterprise-grade, multi-service monorepo application designed to ingest, clean, index, and query public software repositories. Utilizing a dual-engine architecture composed of a **Next.js 16 (Turbopack)** web client and a **FastAPI** AI streaming backend, the platform builds high-fidelity repository context networks by linking dense vector representations with structural Abstract Syntax Tree (AST) entity relationships across cloud databases.

---

## 🗺️ System Architecture Overview

The system abstracts repository analysis into decoupled pipelines, running asynchronously via an orchestrated monorepo topology:


              ┌────────────────────────────────────────┐
              │          Next.js Web Client            │
              │  (Workspace Ingestion / Chat Interface)│
              └───────────────────┬────────────────────┘
                                  │
                     REST API     │  (CORS Allowed)
                    (JSON/POST)   ▼
              ┌────────────────────────────────────────┐
              │       FastAPI Core AI Backend          │
              │ (UnifiedContextEngine / warm state memory)
              └──────┬────────────┬─────────────┬──────┘
                     │            │             │
    Vectors (768-dim)│            │Relational   │Graph Structural
                     ▼            ▼             ▼
             ┌──────────────┐┌──────────┐┌──────────────┐
             │ Qdrant Cloud ││ Neon DB  ││  Neo4j Aura  │
             │ (Similarity) ││(Postgres)││ (AST Graph)  │
             └──────────────┘└──────────┘└──────────────┘

### 🛰️ Core Infrastructure Layer
1. **Frontend App (`/apps/web`):** Built on Next.js 16 with Tailwind CSS, utilizing a dark-cyberpunk, glassmorphic UI framework. Manages streaming server-side network requests and markdown compilation for complex code responses.
2. **AI Backend Core (`/apps/ai-backend`):** Powered by FastAPI and Uvicorn. Keeps a warm memory instance of the `UnifiedContextEngine` to intercept pipeline requests instantly.
3. **Multi-Model Cloud Storage Layer:**
   * **Vector Search Engine:** Qdrant Cloud Cluster storing 768-dimensional dense code embeddings generated via the Gemini API.
   * **Knowledge Graph Matrix:** Neo4j AuraDB handling directional property graphs mapping logical source file tracking and module connections.
   * **Relational Storage:** Neon Postgres tracking workspace repository state history, metadata, and clean transactional file listings.

---

## 🛠️ Tech Stack & Dependencies

### Frontend Framework
* **Core:** Next.js 16.2.6 (Configured for Turbopack Engine Optimization)
* **Styling:** Tailwind CSS (Custom Dark Cyberpunk Palette)
* **Parsing:** ReactMarkdown (For rich code block and syntax formatting)

### Backend Engine
* **Core:** Python 3.11 / FastAPI (Asynchronous Worker Pool)
* **Server Routing:** Uvicorn (Forced UTF-8 I/O Stream Mapping)
* **AI Client:** Google GenAI SDK (`gemini-2.5-flash` for agent processing & Text Embeddings)
* **Graph Database Driver:** `neo4j` (Bolt+s Secure Protocol Routing)
* **ORM Engine:** SQLAlchemy (Relational mapping to Postgres client)

---

## 📁 Repository Directory Structure

```text
CODEINTEL/                             # Root Workspace Directory
├── .gitignore                         # Master disaster-prevention file exclude patterns
├── package.json                       # Global Monorepo config & concurrent launch automation
├── package-lock.json                  # Root tracking dependency lock state
└── codeintelligence/
    ├── apps/
    │   ├── ai-backend/                # Python FastAPI Microservice Hub
    │   │   ├── venv/                  # Localized Python execution binaries (Ignored)
    │   │   ├── main.py                # Main backend routing & CORS middleware configuration
    │   │   ├── context_engine.py      # Unified orchestration logic layer
    │   │   ├── embedding_client.py    # Google GenAI semantic embedding client
    │   │   └── requirements.txt       # Python operational package dependencies
    │   └── web/                       # Next.js Web UI Core Workspace
    │       ├── app/
    │       │   ├── globals.css        # Background auroral mesh and dark layouts
    │       │   ├── layout.js          # Root HTML frame wrapper
    │       │   └── page.js            # Client-side form management & chat messaging UI
    │       ├── src/services/
    │       │   └── codeIntelApi.js    # Unified cross-origin Fetch client methods
    │       └── next.config.mjs        # NextJS experimental compiler properties
    └── node_modules/                  # Universal node package workspace pool

🚀 Local Development Setup & Launch
This platform uses workspace pooling, meaning all JavaScript packages are handled automatically by the master root node folder. Follow these steps to spin up the entire ecosystem on Windows machines:

1. Prerequisites & Environment Check
Ensure your cloud environment credentials are populated within /apps/ai-backend/.env (masked from tracking):

Plaintext

# Qdrant Vector DB Configuration
QDRANT_URL=""
QDRANT_API_KEY=""

# Neo4j Graph DB Configuration
NEO4J_URI=""
NEO4J_USER=""
NEO4J_PASSWORD=""

# Redis Queue Configuration
REDIS_URL=""

#Gemini API Key
GEMINI_API_KEY=""

NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"


2. Multi-Service Ingestion Installation
From the absolute root directory (CODEINTEL), run the universal dependency collector:

PowerShell
npm install
3. Running the Parallel Server Stack
To initialize both servers concurrently with strict Windows command stream protection, execute:

PowerShell
npm run dev
The automation script will handle the following loops natively:

Backend: Spins up your Python environment with forced UTF-8 console output modes (-X utf8) on http://127.0.0.1:8000.

Frontend: Boots the Turbopack dev compiler on http://localhost:3000.

🛡️ Production & Git Push Safety Controls
To prevent leaking sensitive environment structures or massive dependency trees, verify the project's tracking indexes prior to staging operations:

PowerShell
git status
Disaster Prevention Layer: The absolute root .gitignore blocks .env, internal virtual environments (/venv/), file systems (__pycache__/), and build compilation directories (.next/) globally across all sub-folders.

🛰️ Deployment Topology
Frontend: Hosted via Vercel. Configure Root Directory to codeintelligence/apps/web.

Backend: Hosted via Render. Point to the root repository and isolate execution parameters via Root Directory: codeintelligence/apps/ai-backend.

<img width="1600" height="760" alt="image" src="https://github.com/user-attachments/assets/557c0f64-f678-4358-990e-1395792b4b87" />


