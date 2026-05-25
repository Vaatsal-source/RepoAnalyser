# 🧠 CodeIntel Core: Distributed Codebase Intelligence Platform

CodeIntel Core is an enterprise-grade, multi-service monorepo application designed to ingest, clean, index, and query public software repositories. Utilizing a dual-engine architecture composed of a **Next.js 16 (Turbopack)** web client and a **FastAPI** AI streaming backend, the platform builds high-fidelity repository context networks by linking dense vector representations with structural Abstract Syntax Tree (AST) entity relationships across cloud databases.

---

## 🗺️ System Architecture Overview

The system abstracts repository analysis into decoupled pipelines, running asynchronously via an orchestrated monorepo topology:
