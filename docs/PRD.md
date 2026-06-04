# 📘 Product Requirements Document (PRD)
## EduIG-Pipeline: Educational Instagram Data Acquisition System

**Version:** 1.0  
**Date:** 2026-05-31  
**Authors:** [Student Team]  
**Status:** Draft — Ready for Development  

---

## 1. Product Overview

### 1.1 What EduIG-Pipeline IS
- A **local-first, zero-cost data acquisition system** for academic research on Instagram public data
- A **student-friendly Python application** combining official Meta Graph API and lightweight browser automation
- A **compliance-first tool** with built-in rate limiting, audit trails, and data minimization
- An **educational framework** teaching data engineering, web scraping ethics, and research methodology
- A **modular pipeline** supporting SQLite/JSON/CSV storage with configurable extraction schemas

### 1.2 What EduIG-Pipeline IS NOT
- **NOT** a commercial scraping tool or bulk data harvester
- **NOT** a system for bypassing authentication or accessing private content
- **NOT** a distributed/cloud-scale architecture (intentionally single-machine)
- **NOT** a real-time monitoring dashboard or SaaS product
- **NOT** a tool for storing credentials, PII, or redistributing raw user data
- **NOT** an enterprise-grade solution (throughput capped at ~25 profiles/hour)

---

## 2. Problem Statement & Goals

### 2.1 Problem Statement
Students and academic researchers face three critical barriers when studying social media:

| Barrier | Current Pain Point | Impact |
|---------|-------------------|--------|
| **Cost** | Commercial APIs (Apify, Bright Data) cost $50–$500+/month | Prohibitive for students |
| **Complexity** | Building scrapers from scratch requires deep web dev knowledge | High barrier to entry |
| **Compliance** | Most scraping tools ignore ToS, ethics, and data privacy laws | Risk of academic misconduct |

### 2.2 Goals

| Goal ID | Goal | Priority | Success Metric |
|---------|------|----------|----------------|
| G1 | Extract public Instagram profile metadata (bio, followers, posts) without paid APIs | P0 | 95%+ extraction success on public profiles |
| G2 | Implement conservative rate limiting to avoid IP bans | P0 | 0 hard bans over 100-profile test set |
| G3 | Store data in academic-friendly formats (CSV, SQLite, JSON) | P0 | Support all 3 formats with schema validation |
| G4 | Maintain full audit trail for IRB/ethics compliance | P1 | Every request logged with timestamp, target, status |
| G5 | Auto-delete raw PII after 7 days per compliance config | P1 | 100% automated deletion with verification log |
| G6 | Provide modular architecture for custom research questions | P2 | New extraction field added in <30 min |

---

## 3. Feature Specifications

### 3.1 Core Features (P0 — Must Have)

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| **F1: Target Management** | CSV/JSON-based list of usernames/URLs to scrape | Load 100+ targets; validate username format; skip duplicates |
| **F2: Dual Router** | Automatically route to Graph API (if OAuth token) or Browser Worker | Detect auth status; fallback seamlessly; log routing decision |
| **F3: Browser Extraction** | Playwright-based public profile scraping | Extract: username, bio, follower count, following count, post count; handle DOM changes gracefully |
| **F4: Rate Limiting** | Leaky bucket + exponential backoff | 20 req/hour default; jitter 0.5–1.5x; 3 retries with backoff |
| **F5: Data Normalization** | Parse and validate raw responses | Pydantic models; deduplication; schema mapping to standard fields |
| **F6: Multi-Format Storage** | Write to SQLite, JSON, CSV | Atomic writes; WAL mode for SQLite; UTF-8 encoding; daily rotation |
| **F7: Audit Logging** | Structured logs with structlog | Timestamp, target, status, bytes collected, compliance note, IP (optional) |
| **F8: Configuration System** | YAML-based settings | Rate limits, paths, compliance flags, max profiles per run |

### 3.2 Secondary Features (P1 — Should Have)

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| **F9: Post Metadata Extraction** | Extract public post data (likes, comments, captions) | 10 most recent posts per profile; handle pagination truncation |
| **F10: Hashtag Analysis** | Extract hashtag usage from public posts | Count frequency; store normalized hashtag list |
| **F11: Engagement Metrics** | Calculate engagement rate from public data | (likes + comments) / followers; store per post and average |
| **F12: Data Retention Scheduler** | Auto-delete raw JSON after N days | Configurable days; dry-run mode; deletion log |
| **F13: Jupyter Notebook Templates** | Pre-built analysis notebooks | Pandas/Polars examples; matplotlib/seaborn charts; anonymization helper |

### 3.3 Future Features (P2 — Nice to Have)

| Feature | Description | Notes |
|---------|-------------|-------|
| **F14: Sentiment Analysis** | Basic sentiment on captions | Use VADER or TextBlob; store sentiment score |
| **F15: Network Graph Export** | Follower/following relationship mapping | Limited to ~1k entries without auth; GEXF/GraphML export |
| **F16: Web Dashboard** | Simple Flask/Streamlit UI for configuration | Only for local use; no authentication needed |
| **F17: Synthetic Data Generator** | Generate fake Instagram data for testing | Faker-based; match schema for testing without scraping |

---

## 4. Success Metrics

### 4.1 Technical Metrics

| Metric | Target | Measurement Method |
|--------|--------|---------------------|
| Extraction Success Rate | ≥95% | Success count / total targets over 100-profile test |
| System Uptime | 99% (local runs) | Run completion rate without crashes |
| Rate Limit Compliance | 100% | Zero 429 errors caused by our request pattern |
| Data Integrity | 100% | Pydantic validation pass rate |
| Storage Efficiency | <10MB per 100 profiles | Average raw + processed size |

### 4.2 Academic/Compliance Metrics

| Metric | Target | Measurement Method |
|--------|--------|---------------------|
| IRB Audit Pass | 100% | All logs present; consent documented; PII stripped |
| Data Retention Compliance | 100% | Automated deletion verified via log inspection |
| Reproducibility | 100% | Another student can replicate results with README only |
| Code Documentation | ≥80% coverage | Docstrings on all public methods |

### 4.3 Learning Outcomes

| Metric | Target |
|--------|--------|
| Student can explain rate limiting | Post-project interview |
| Student can modify extraction schema | Timed modification test |
| Student can justify compliance decisions | Written reflection |

---

## 5. Constraints & Limitations

### 5.1 Technical Constraints

| Constraint | Description | Mitigation |
|------------|-------------|------------|
| **Throughput Cap** | ~10–25 profiles/hour per IP | Accept as design constraint; focus on analysis quality |
| **No Auth Bypass** | Cannot access private accounts or stories | Scope research to public data only; document limitation |
| **DOM Fragility** | Instagram changes selectors frequently | Use `page.evaluate()` JSON extraction; manual fallback |
| **IP Soft-Block** | ~50 requests/day may trigger blocks | University network rotation; 24h cooldown; reduce frequency |
| **Pagination Limits** | Follower/following lists truncated at ~1k–3k | Document in methodology; use official API for full graphs |
| **No Real-Time** | Data freshness depends on execution schedule | Schedule daily/weekly runs; document timestamp |

### 5.2 Compliance Constraints

| Constraint | Description | Mitigation |
|------------|-------------|------------|
| **ToS Prohibition** | Instagram ToS bans automated collection | Academic framing; no commercial use; IRB approval; public data only |
| **Data Minimization** | Collect only necessary fields | Configurable field whitelist; default minimal schema |
| **PII Handling** | Cannot store or distribute raw PII | Auto-anonymization; username hashing; 7-day raw deletion |
| **Consent Requirement** | Specific user studies need consent | Consent flag in config; separate consent tracking CSV |
| **No Credential Storage** | Never store Instagram passwords/tokens | OAuth only; token in env vars; never commit to git |

### 5.3 Resource Constraints

| Resource | Limitation |
|----------|------------|
| Budget | $0 — only free tiers and open-source tools |
| Infrastructure | Single laptop or university lab machine |
| Team Size | 2 students (part-time) |
| Timeline | 4–6 weeks for MVP |
| Maintenance | Post-project, minimal maintenance expected |

---

## 6. Out of Scope

The following are explicitly out of scope for this project:

- Paid proxy services or CAPTCHA-solving services
- Distributed scraping across multiple IPs/machines
- Real-time streaming or webhook-based data collection
- Machine learning model training (analysis only, not model building)
- Mobile app or cloud-hosted SaaS deployment
- Automated posting, liking, or interaction with Instagram
- Storage of images or video content (metadata only)

---

**End of PRD**
