# AGENTS.md — Engineering Specification

This file defines architecture, technical phases, schema rules, and coding guardrails.  
It must remain aligned with the product roadmap in **PRODUCT.md**.

---

## Overview
The Crypto Market Intelligence Dashboard processes multi-layered crypto signals using modular ingestion, transformation, sentiment pipelines, and AI reasoning.

Phases:
1. Data Ingestion & Transformation
2. Market Metrics & Derivatives
3. NLP Sentiment Pipeline
4. Dashboarding (WIP)
5. AI Reasoning & Decision Agents (planned)

---

# Completed Core Functionality

## Phase 1 — Data Ingestion Layer (✓)
**Files:** `src/connectors/*`, `src/storage/*`, `src/pipeline.py`  
**Signals:** OHLC, volatility, fear/greed, ETF flows  
**Features:** daily sync, backfill mode, retries, CSV backups  
**Output:** `daily_market_snapshot`

## Phase 2 — Market Metrics & Derivatives (✓)
**Signals:** volume, dominance, market cap, funding rate, open interest  
**Source:** CoinGecko, Binance Futures  
**Schema:** updated in storage migrations

## Phase 3 — NLP + Sentiment Pipeline (✓)
**Sources:** Reddit (RSS/API), Twitter/X, NewsAPI, Google Trends  
**Sentiment:** VADER for social, FinBERT for news  
**Tables:** `social_posts_raw`, `news_articles_raw`, `search_trends_raw` + aggregated daily tables  
**Behavior:** raw → aggregated model for flexible reprocessing

---

# Work in Progress

## Phase 4 — Dashboarding (⏳)
Streamlit: multi-tab charts for price, volatility, ETF flows, sentiment, KPIs.

## Phase 5 — Analytics Layer (planned)
Correlation, lag, regime detection, signal scoring.

---

# Code Quality & Design Guardrails (DO NOT REMOVE)

### Architecture & Modularity
- All code must be modular, testable, and reusable.
- Prefer configs/env variables over hardcoding.

### Design & Sign-off
- All schema or connector changes must be added to AGENTS.md before coding.

### File Discipline
- Only two docs allowed: PRODUCT.md + AGENTS.md.  
- No extra `.md` documents.

### Testing
- Every connector requires unit/integration tests.
- Validate idempotent ingestion before merge.

### Readability
- Follow PEP8, consistent naming, clear docstrings.

### Deployment Workflow
`Design → Sign-off → Implement → Review → Test → Deploy`

### Performance
- Minimize API calls, handle rate limits gracefully.

### Change Management
- New signals enter “Work in Progress” → then move to “Completed” after validation.

---
