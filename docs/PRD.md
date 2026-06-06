# CareerOS AI / AutoApply Agent PRD

## Product Overview

CareerOS AI is a local-first career operating system that helps a user discover relevant jobs, analyze job descriptions, score fit against their profile, generate truthful ATS-safe tailored resumes, prepare applications, autofill forms, and track application progress.

The product is designed to run locally with free, open components:

- Backend API in FastAPI
- Web dashboard in Next.js
- Browser extension in Plasmo
- PostgreSQL for relational storage
- Qdrant for vector search
- Ollama for local model execution

Primary product rule:

- The system may prepare and autofill applications, but it must stop before final submission unless a human explicitly approves.
- The system must not bypass CAPTCHA, login walls, paywalls, anti-bot protections, or website security controls.

## Product Principles

- Local-first by default
- Free to run with no paid API dependency
- Truthful by construction
- Profile-isolated data model
- Human approval for sensitive or final actions
- Test-first implementation for critical paths

## Target Users

1. Active job seekers applying to many roles per week
2. Career switchers needing role-specific resume variants
3. Users managing multiple profiles, such as different personas or locations
4. Users who want automation but still require human approval before submission

## Core User Journeys

### 1. Create a profile

- User creates a profile for a specific career track, location, and application strategy.
- User adds target roles, locations, and answer bank values.
- User uploads a master resume and supporting documents.

### 2. Ingest master resume

- User uploads PDF or DOCX.
- System extracts text and structure.
- System splits content into sections and evidence-backed claims.
- System stores the structured master resume and embeddings.

### 3. Discover jobs

- System searches public ATS sources for target roles.
- Jobs are normalized and deduplicated.
- User can also extract a job from the browser extension on an open job page.

### 4. Analyze and score jobs

- System parses job descriptions into structured requirements.
- System scores the job against the active profile.
- Jobs below threshold or blocked by hard rules are rejected.

### 5. Tailor resume

- System selects evidence-backed claims only.
- System generates a tailored resume JSON that preserves truth.
- System rejects any unsupported claims.

### 6. Review and approve application

- System prepares the application packet.
- User reviews the resume, job summary, and answers.
- Human approval is required before final submission.

### 7. Autofill forms

- Extension fills supported fields from profile data and answer bank.
- Unknown or sensitive questions are flagged for review.
- The extension stops before final submit.

### 8. Track application status

- System records the application history, actions, approvals, and outcomes.
- User can inspect pipeline status and agent activity from the dashboard.

## Functional Requirements

### Profiles

- Support multiple profiles per user
- Strict data isolation by `profile_id`
- Profile-specific resume, locations, target roles, settings, answer bank, and application history

### Job Discovery

- Search public ATS sources only
- Support Greenhouse, Lever, Ashby, and generic career pages
- Avoid aggressive scraping
- Fail gracefully on blocked pages or unsupported content

### Resume Brain

- Ingest PDF and DOCX
- Extract structured sections
- Preserve source evidence for every claim
- Store searchable embeddings

### AI Engine

- Use Ollama only
- Support Qwen3, DeepSeek-R1, and BGE-M3
- Provide strict JSON helpers with retry and timeout handling

### Job Analyzer

- Convert job descriptions into structured JSON
- Validate output against schema
- Store normalized job requirements

### Match Scoring

- Score skills, experience, role fit, location, and work authorization fit
- Support hard reject rules
- Keep scoring profile-specific

### Resume Tailoring

- Generate ATS-friendly, truthful, evidence-backed resumes
- Reject unsupported claims
- Preserve traceability from output bullet to source evidence

### ATS Validation

- Enforce clean document structure
- Avoid unsupported layout patterns
- Measure keyword coverage and readability

### Document Generation

- Export DOCX first
- Export PDF after DOCX generation
- Ensure text remains extractable for ATS compatibility

### Web Dashboard

- Provide command center, profiles, resume tools, jobs, approvals, answer bank, and agent runs
- Support live updates and responsive UX

### Extension

- Extract job details from supported job pages
- Autofill application fields from user data
- Stop before final submission

## Non-Functional Requirements

- Local execution
- Low operational cost
- Testable in CI
- Secure by default
- Clear error messages
- Reliable profile isolation
- Deterministic outputs where possible

## Success Metrics

- Resume uploads parse successfully with evidence linkage
- Job parsing and scoring complete without invalid AI output leakage
- Applications can be prepared and autofilled without auto-submission
- No cross-profile data contamination
- Tests pass for every critical path

## Scope Boundaries

In scope:

- Job discovery
- Job analysis
- Resume tailoring
- Autofill assistance
- Application tracking
- Human approval workflow

Out of scope:

- CAPTCHA bypass
- Login bypass
- Paywall bypass
- Auto-submission without approval
- Paid APIs as required dependencies

## Phased Delivery Summary

### Phase 0

- Planning documents only

### Phase 1

- Monorepo foundation

### Phase 2

- Database and multi-profile model

### Phase 3

- Resume ingestion and evidence mapping

### Phase 4

- Local AI engine

### Phase 5

- Job discovery engine

### Phase 6

- Universal job extractor extension

### Phase 7

- Job analyzer

### Phase 8

- Match scoring engine

### Phase 9

- Resume tailoring engine

### Phase 10

- ATS validator

### Phase 11

- Document generator

### Phase 12

- Interactive web dashboard

### Phase 13

- Autofill engine

### Phase 14

- Continuous agent mode

### Phase 15

- Security, QA, and polish
