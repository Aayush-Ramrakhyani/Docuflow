# DocuFlow Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in DocuFlow, please report it privately at:

**Email:** security@docuflow.app (replace with real contact)

Do **not** open a public GitHub issue for security vulnerabilities.

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

We aim to respond within 48 hours and release a fix within 7 days for critical issues.

## Security Architecture

### Authentication
- JWT access tokens (15-minute lifetime) + refresh tokens (7 days, httpOnly cookie)
- Argon2id password hashing (OWASP-recommended parameters)
- Timing-safe password verification
- Automatic Argon2 parameter upgrade on login

### Multi-Tenancy
- PostgreSQL Row-Level Security on all tenant-scoped tables
- Application-level ownership checks (defense in depth)
- UUID primary keys (prevents enumeration attacks)

### File Upload Security
- Magic byte validation (not client-supplied MIME types)
- Server-side UUID-based storage keys (prevents path traversal)
- Files stored in private S3 buckets
- Short-lived signed URLs (1 hour) for document access
- File size limits enforced

### AI Security
- Document content structurally isolated from instructions using XML delimiters
- AI output validated against Pydantic schemas before storage
- Adversarial document content treated as untrusted data

### Transport Security
- HTTPS required in production (HSTS enforced)
- Security headers on every response (CSP, X-Frame-Options, etc.)
- Restrictive CORS configuration

### Audit Trail
- Immutable audit logs for all sensitive actions
- Actors, timestamps, resources, and outcomes recorded

## Known Limitations

- Email verification flow is stubbed (tokens generated but emails not sent)
- CAPTCHA for registration not yet implemented
- Webhook signature verification not fully implemented
- Malware scanning of uploaded documents not implemented

These are tracked in `docs/SECURITY_CHECKLIST.md`.
