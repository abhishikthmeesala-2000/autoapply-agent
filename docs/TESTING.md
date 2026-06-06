# Testing Strategy

## Test Philosophy

CareerOS AI is safety-sensitive because it handles job applications, personal data, and browser automation. Tests must verify correctness, profile isolation, output validation, and stop-before-submit behavior before adding new functionality.

## Testing Layers

### Unit tests

- Pure logic
- Validation
- Scoring
- AI output parsing
- Resume evidence mapping
- Autofill field selection

### Integration tests

- API endpoints
- Database persistence
- Job ingestion
- Resume ingestion
- Extension-to-backend communication

### Contract tests

- Schema validation for AI output
- API request and response shapes
- Public job connector normalization

### End-to-end tests

- Dashboard flows
- Job extraction from supported pages
- Autofill preparation
- Human approval gating

## Critical Test Areas

### Profile isolation

- Verify all user-owned records remain scoped to a single profile
- Verify no cross-profile resume version, application, or answer reuse

### Truthfulness

- Verify resume tailoring rejects unsupported claims
- Verify every bullet maps to source evidence
- Verify sensitive answers only come from answer bank or review

### AI robustness

- Verify invalid JSON retries once
- Verify timeout handling
- Verify unavailable model behavior is clear and safe

### Job discovery

- Verify deduplication
- Verify blocked or unsupported pages fail gracefully
- Verify normalized job shape

### Extension safety

- Verify field detection
- Verify no submit button click
- Verify sensitive fields are not guessed

### ATS safety

- Verify bad templates fail
- Verify clean templates pass
- Verify extracted PDF text remains readable

## Tooling Plan

- `pytest` for backend and package tests
- `vitest` for frontend and shared logic tests
- `playwright` for browser flows where applicable
- Fixture-based tests for resume parsing, job parsing, and extension DOM extraction

## Test Data Policy

- Use synthetic resumes and synthetic job pages
- Do not use real user credentials
- Do not use private company data unless explicitly permitted and sanitized
- Prefer small, readable fixtures

## Exit Criteria Per Phase

Before moving to the next phase:

- All targeted tests pass
- Lint passes for affected packages
- Type checking passes for affected packages
- Any new feature has regression coverage
