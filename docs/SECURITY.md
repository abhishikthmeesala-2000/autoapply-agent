# CareerOS AI Security and Privacy Model

## Security Goals

- Protect user profile data from cross-profile leakage
- Prevent unauthorized application submission
- Prevent invention of resume claims or sensitive answers
- Reduce exposure of personal data to only local systems
- Make automation observable and reviewable

## Threat Model

### Data exposure risks

- Resume content contains highly sensitive personal and employment history
- Answer bank values may contain protected or private data
- Application history can reveal job search activity and intent

### Automation risks

- Incorrect autofill of legal or demographic answers
- Accidental auto-submission
- Action on the wrong profile
- Duplicate applications

### AI risks

- Hallucinated resume claims
- Hallucinated job requirements
- Invalid JSON or malformed structured output
- Prompt injection from scraped job descriptions or page content

### Browser risks

- Malicious job pages may contain hostile text or DOM tricks
- Unsupported sites may attempt to trap automation in login or CAPTCHA flows
- Extension content scripts can be exposed to untrusted page content

## Privacy Model

- All user-owned records are scoped by `profile_id` where applicable
- No cross-profile reuse of applications, answers, resume versions, or generated outputs
- Sensitive fields must come from saved answers or require review
- No external paid API should be required for normal operation
- Local models and local databases minimize third-party data exposure

## Data Classification

### Public or low sensitivity

- Job titles
- Company names
- Public job descriptions

### Sensitive

- Resume contents
- Application history
- Work authorization details
- Salary expectations
- Contact information
- Personal identifiers

### Highly sensitive

- Demographic answers
- Disability and veteran status
- Visa status
- Government identifiers if ever added

## Security Controls

### Input validation

- Validate all API payloads with typed schemas
- Reject invalid file types and empty uploads
- Validate AI output before persistence

### Output validation

- Reject unsupported claims in resume tailoring
- Reject unapproved sensitive answers
- Reject malformed job parsing output

### Access control

- Enforce user ownership and profile ownership checks
- Scope every query by profile where relevant
- Avoid implicit cross-profile joins

### File handling

- Limit file sizes
- Sanitize filenames
- Extract text safely from PDF/DOCX
- Avoid executing embedded content

### Browser extension safety

- Detect fields conservatively
- Do not auto-submit
- Do not bypass CAPTCHA or login flows
- Require confirmation for uncertain mappings

### AI safety

- Use strict JSON prompts
- Retry once on invalid JSON only
- Apply timeouts
- Treat prompt injection as untrusted data

### Auditability

- Log key actions
- Log profile-aware operations
- Log agent decisions and approval events

## Explicit Non-Goals

- CAPTCHA bypass
- Credential harvesting
- Login bypass
- Anti-bot evasion
- Hidden auto-submission
- Third-party data resale or sharing

## Failure Handling Requirements

- Fail closed when validation fails
- Fail closed when profile ownership is unclear
- Fail closed when AI output is invalid
- Fail closed when a page is unsupported or protected
- Fail closed when a sensitive answer is not in the answer bank

## Secure Development Rules

- Use parameterized queries and ORM safeguards
- Keep secrets out of source control
- Do not hardcode user-specific data
- Use fixtures and mocks in tests
- Write tests for security-sensitive behavior

## Incident Response Considerations

If a bug causes profile leakage, wrong-profile application prep, or unsafe autofill:

- Stop automation
- Preserve logs
- Reproduce with tests
- Patch at the policy and code level
- Add regression coverage before proceeding
