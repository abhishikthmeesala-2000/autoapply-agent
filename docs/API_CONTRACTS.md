# API Contracts

## Conventions

- All profile-scoped routes must include `profile_id`
- All request and response bodies must be schema validated
- Sensitive operations must fail closed
- Errors should be explicit and human-readable

## Phase 1 Contract

### GET /health

Response:

```json
{ "status": "ok" }
```

## Phase 3 Contract

### POST /profiles/{profile_id}/resume/upload

Purpose:

- Upload PDF or DOCX resume for ingestion

Response:

```json
{
  "master_resume_id": "uuid",
  "status": "parsed"
}
```

### GET /profiles/{profile_id}/resume/master

Purpose:

- Return parsed master resume JSON for the profile

### GET /profiles/{profile_id}/resume/evidence

Purpose:

- Return evidence records linked to parsed claims

## Phase 5 Contract

### POST /profiles/{profile_id}/agent/discover-jobs

Purpose:

- Trigger public job discovery for the profile

Response:

```json
{
  "discovered": 0,
  "deduped": 0
}
```

## Phase 6 Contract

### POST /profiles/{profile_id}/jobs/extracted

Purpose:

- Receive a job extracted by the browser extension

## Phase 7 Contract

### POST /profiles/{profile_id}/jobs/{job_id}/analyze

Purpose:

- Parse job description into structured requirements

## Phase 8 Contract

### POST /profiles/{profile_id}/jobs/{job_id}/score

Purpose:

- Score a job against the active profile

### POST /profiles/{profile_id}/agent/score-new-jobs

Purpose:

- Score all newly discovered jobs for the profile

## Phase 9 Contract

### POST /profiles/{profile_id}/jobs/{job_id}/tailor-resume

Purpose:

- Generate a tailored resume JSON from evidence-backed source data

## Phase 10 Contract

### POST /profiles/{profile_id}/resume_versions/{id}/validate

Purpose:

- Validate ATS structure, keyword coverage, readability, and extractability
- Persist the ATS score for the tailored resume version

## Phase 11 Contract

### POST /profiles/{profile_id}/resume_versions/{id}/export

Purpose:

- Export DOCX and PDF for a tailored resume version

## Phase 14 Contract

### POST /profiles/{profile_id}/agent/start

Purpose:

- Start continuous agent mode

### POST /profiles/{profile_id}/agent/pause

Purpose:

- Pause continuous agent mode

### POST /profiles/{profile_id}/agent/stop

Purpose:

- Stop continuous agent mode

## Phase 15 Contract

### GET /profiles/{profile_id}/audit-logs

Purpose:

- Return the profile audit trail newest-first
- Fail closed if the profile does not exist

### POST /profiles/{profile_id}/backup

Purpose:

- Export an encrypted profile backup
- Require name confirmation and a passphrase

Response headers:

- `X-Backup-Encrypted: true`
- `Content-Disposition: attachment; filename="careeros-profile-<id>-backup.json.enc"`

### DELETE /profiles/{profile_id}/data

Purpose:

- Delete profile-scoped operational data while preserving audit logs
- Require name confirmation before deleting anything

Response:

```json
{
  "profile_id": "uuid",
  "preserved_audit_logs": 0,
  "deleted_counts": {
    "jobs": 0
  }
}
```
