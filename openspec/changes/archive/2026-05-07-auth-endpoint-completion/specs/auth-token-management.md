# Spec: auth-token-management

## ADDED Requirements

### Requirement: Token Refresh Mechanism
The system SHALL provide JWT token refresh capability via a new `/auth/refresh` endpoint. When a client sends a valid refresh token, the system MUST issue a new access token without requiring re-authentication.

#### Scenario: Valid refresh token returns new access token
- **WHEN** POST `/auth/refresh` is called with valid refresh token
- **THEN** the system returns new access token with fresh expiration time (15 minutes from now)

#### Scenario: Expired refresh token rejected
- **WHEN** POST `/auth/refresh` is called with expired refresh token
- **THEN** the system returns HTTP 401 with error `REFRESH_TOKEN_EXPIRED`

#### Scenario: Blacklisted refresh token rejected
- **WHEN** POST `/auth/refresh` is called with revoked refresh token
- **THEN** the system returns HTTP 401 with error `TOKEN_REVOKED`

### Requirement: Token Refresh Response Includes New Refresh Token
The system SHALL issue a new refresh token with each successful token refresh (sliding window). The response MUST include both access_token and refresh_token.

#### Scenario: Refresh response includes both tokens
- **WHEN** POST `/auth/refresh` succeeds
- **THEN** response contains `access_token` (15 min expiry), `refresh_token` (7 day expiry), and `token_type: "bearer"`

### Requirement: Token Blacklist/Revocation
The system SHALL maintain a token blacklist to prevent use of revoked tokens. When a token is added to blacklist, it MUST not be accepted for authentication until its natural expiration time.

#### Scenario: Add token to blacklist on logout
- **WHEN** POST `/auth/logout` is called with valid token
- **THEN** the token is added to blacklist and subsequent requests with same token return HTTP 401

#### Scenario: Blacklist entries auto-expire
- **WHEN** a token's expiration time passes
- **THEN** the blacklist entry is automatically cleaned up (or TTL expires)

#### Scenario: Blacklist stored in cache with optional persistence
- **WHEN** server restarts
- **THEN** if Redis is configured, blacklist is restored; if in-memory only, blacklist is lost (acceptable for dev/staging)

### Requirement: Logout Endpoint
The system SHALL provide `/auth/logout` endpoint that revokes the current token and clears client-side session state.

#### Scenario: Valid logout clears authentication
- **WHEN** POST `/auth/logout` is called by authenticated user
- **THEN** the token is blacklisted and user is logged out

#### Scenario: Logout without token returns error
- **WHEN** POST `/auth/logout` is called without Authorization header
- **THEN** the system returns HTTP 401

### Requirement: Token Type Differentiation
The system SHALL issue two distinct token types: `access_token` (short-lived) and `refresh_token` (long-lived). Each token type MUST have different expiration times and purpose claims.

#### Scenario: Access token has 15 minute expiry
- **WHEN** login or token refresh succeeds
- **THEN** access_token contains claim `type: "access"` and `exp` 15 minutes in future

#### Scenario: Refresh token has 7 day expiry
- **WHEN** login or token refresh succeeds
- **THEN** refresh_token contains claim `type: "refresh"` and `exp` 7 days in future

#### Scenario: Access token rejected if used as refresh token
- **WHEN** POST `/auth/refresh` is called with access_token instead of refresh_token
- **THEN** system returns HTTP 400 with error `INVALID_TOKEN_TYPE`

