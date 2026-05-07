# Spec: auth-rate-limiting

## ADDED Requirements

### Requirement: Rate Limit Login Endpoint
The system SHALL enforce rate limiting on POST `/auth/login` endpoint: maximum 5 attempts per 15 minutes per IP address.

#### Scenario: Login allowed within rate limit
- **WHEN** admin calls POST `/auth/login` for the 3rd time in 15 minutes from same IP
- **THEN** request succeeds with HTTP 200 and token response

#### Scenario: Login rejected when rate limit exceeded
- **WHEN** admin calls POST `/auth/login` for the 6th time in 15 minutes from same IP
- **THEN** request fails with HTTP 429 (Too Many Requests) and error message "Too many login attempts. Try again in 15 minutes."

#### Scenario: Rate limit resets after time window
- **WHEN** 15 minutes pass after first login attempt from an IP
- **THEN** counter resets and next login from that IP is allowed

### Requirement: Rate Limit Register Endpoint
The system SHALL enforce rate limiting on POST `/auth/register` endpoint: maximum 3 attempts per 1 hour per IP address.

#### Scenario: Register allowed within rate limit
- **WHEN** user calls POST `/auth/register` for the 2nd time in 1 hour from same IP
- **THEN** request succeeds with HTTP 201

#### Scenario: Register rejected when rate limit exceeded
- **WHEN** user calls POST `/auth/register` for the 4th time in 1 hour from same IP
- **THEN** request fails with HTTP 429 and error message "Too many registration attempts. Try again in 1 hour."

### Requirement: Rate Limit Password Change Endpoint
The system SHALL enforce rate limiting on POST `/auth/change-password` endpoint: maximum 10 attempts per 1 hour per authenticated user.

#### Scenario: Password change allowed within limit
- **WHEN** authenticated user calls POST `/auth/change-password` for the 5th time in 1 hour
- **THEN** request succeeds with HTTP 200

#### Scenario: Password change rejected when limit exceeded
- **WHEN** authenticated user calls POST `/auth/change-password` for the 11th time in 1 hour
- **THEN** request fails with HTTP 429 and error message "Too many password change attempts. Try again in 1 hour."

### Requirement: Rate Limit Uses Client IP
The system SHALL identify client IP from request, handling proxy headers correctly (X-Forwarded-For, X-Real-IP).

#### Scenario: Rate limit key uses real client IP
- **WHEN** request arrives behind reverse proxy with X-Forwarded-For header
- **THEN** rate limiting uses actual client IP (rightmost valid IP from X-Forwarded-For chain)

#### Scenario: Rate limit key uses request IP if no proxy headers
- **WHEN** request arrives without proxy headers
- **THEN** rate limiting uses request.client.host

### Requirement: Rate Limit Response Headers
The system SHALL include rate limit information in HTTP response headers for client awareness.

#### Scenario: Response includes rate limit headers
- **WHEN** POST `/auth/login` succeeds
- **THEN** response includes headers:
  - `RateLimit-Limit: 5`
  - `RateLimit-Remaining: 4` (remaining attempts)
  - `RateLimit-Reset: <unix-timestamp>`

#### Scenario: Rate limit headers provided on 429 response
- **WHEN** rate limit is exceeded
- **THEN** HTTP 429 response includes retry-after headers with wait time in seconds

