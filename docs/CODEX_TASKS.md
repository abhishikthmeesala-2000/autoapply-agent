# Codex Implementation Tasks

## Working Principles

- Implement one phase at a time
- Do not start the next phase until tests pass
- Keep business logic out of routes
- Add tests for every critical path
- Preserve profile isolation at every layer
- Prefer local, deterministic, and truthful behavior

## Phase 0

Deliverables:

- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/CODEX_TASKS.md`
- `docs/API_CONTRACTS.md`
- `docs/TESTING.md`

Success criteria:

- Planning documents exist and are internally consistent
- No application code is introduced

## Phase 1

Goal:

- Create monorepo foundation

Tasks:

- Scaffold `apps/web`
- Scaffold `apps/api`
- Scaffold `apps/extension`
- Add `packages/shared`
- Add Docker Compose services for PostgreSQL and Qdrant
- Add Makefile commands
- Add README with local setup

## Phase 2

Goal:

- Implement database and multi-profile model

Tasks:

- Add SQLAlchemy models
- Add Alembic migrations
- Add schema tests
- Add profile isolation tests

## Phase 3

Goal:

- Build resume ingestion and evidence mapping

Tasks:

- Upload PDF/DOCX
- Extract text
- Parse sections
- Create evidence IDs
- Store structured JSON
- Store embeddings in Qdrant

## Phase 4

Goal:

- Build local AI engine

Tasks:

- Wrap Ollama
- Support Qwen3, DeepSeek-R1, and BGE-M3
- Add strict JSON helper
- Add retry and timeout handling

## Phase 5

Goal:

- Implement job discovery engine

Tasks:

- Add connectors for Greenhouse, Lever, Ashby, and generic pages
- Normalize job records
- Deduplicate jobs
- Respect blocked pages and robots constraints

## Phase 6

Goal:

- Build universal job extractor extension

Tasks:

- Detect supported job page types
- Extract visible job details
- Send extracted job to backend
- Show side panel feedback

## Phase 7

Goal:

- Build job analyzer

Tasks:

- Parse job descriptions into strict JSON
- Validate AI output
- Save job requirements

## Phase 8

Goal:

- Build match scoring engine

Tasks:

- Apply weighted scoring
- Add hard reject rules
- Add profile-specific matching tests

## Phase 9

Goal:

- Build resume tailoring engine

Tasks:

- Use evidence-backed generation
- Reject unsupported claims
- Preserve traceability

## Phase 10

Goal:

- Build ATS validator

Tasks:

- Validate structure
- Validate keyword coverage
- Validate readability and extractability

## Phase 11

Goal:

- Build document generator

Tasks:

- Generate DOCX
- Export PDF
- Ensure ATS-safe layout

## Phase 12

Goal:

- Build interactive web dashboard

Tasks:

- Create core pages
- Add profile switcher
- Add mock data
- Connect APIs

## Phase 13

Goal:

- Build autofill engine

Tasks:

- Detect fields
- Fill trusted profile data
- Mark uncertain answers for review
- Stop before submit

## Phase 14

Goal:

- Build continuous agent mode

Tasks:

- Add start/pause/stop controls
- Schedule discovery and scoring
- Respect daily limits
- Require approval before submission

## Phase 15

Goal:

- Security, QA, and polish

Tasks:

- Add audit logs
- Add encrypted backup
- Add deletion tools
- Finalize docs and diagrams
- Harden validation and error handling
