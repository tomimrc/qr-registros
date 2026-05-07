# Spec: auth-password-validation

## ADDED Requirements

### Requirement: Centralized Password Validation
The system SHALL provide `PasswordValidator` utility that enforces consistent password requirements across all password-related endpoints (register, change-password, password reset).

#### Scenario: Valid password passes validation
- **WHEN** `PasswordValidator.validate()` is called with password "SecureP@ss123"
- **THEN** validation passes and returns None (no error)

#### Scenario: Password less than 8 chars rejected
- **WHEN** `PasswordValidator.validate()` is called with password "Short1!"
- **THEN** validation fails with error `PASSWORD_TOO_SHORT: "Password must be at least 8 characters"`

#### Scenario: Password without uppercase rejected
- **WHEN** `PasswordValidator.validate()` is called with password "securep@ss123"
- **THEN** validation fails with error `MISSING_UPPERCASE: "Password must contain at least 1 uppercase letter"`

#### Scenario: Password without number rejected
- **WHEN** `PasswordValidator.validate()` is called with password "SecurePass@"
- **THEN** validation fails with error `MISSING_NUMBER: "Password must contain at least 1 number"`

#### Scenario: Password without special char rejected
- **WHEN** `PasswordValidator.validate()` is called with password "SecurePass123"
- **THEN** validation fails with error `MISSING_SPECIAL_CHAR: "Password must contain at least 1 special character (!@#$%^&*)"`

### Requirement: Password Cannot Be Similar to Email
The system SHALL validate that new password is sufficiently different from admin's email to prevent predictable passwords.

#### Scenario: Password similar to email rejected
- **WHEN** `PasswordValidator.validate()` is called with email "john@example.com" and password "John@example123"
- **THEN** validation fails with error `PASSWORD_TOO_SIMILAR_TO_EMAIL: "Password must differ from your email address"`

### Requirement: Password History Tracking
The system SHALL prevent password reuse by maintaining password history. Admin cannot reuse any of their last 3 passwords.

#### Scenario: Reused password rejected
- **WHEN** admin attempts to set password that matches any of last 3 used passwords
- **THEN** validation fails with error `PASSWORD_REUSED: "Cannot reuse any of your last 3 passwords"`

#### Scenario: New password not in history passes
- **WHEN** admin sets password that doesn't match any in history
- **THEN** password is accepted and stored in `admin_password_history`

#### Scenario: History entry created with metadata
- **WHEN** password changes
- **THEN** new entry is created in `admin_password_history` with fields: admin_id, tenant_id, hashed_password, changed_at, changed_by

### Requirement: Validation Used by All Auth Endpoints
The system SHALL call `PasswordValidator` from all endpoints that accept password input: `/auth/register`, `/auth/change-password`.

#### Scenario: Registration rejects invalid password
- **WHEN** POST `/auth/register` is called with weak password
- **THEN** request fails with HTTP 400 and validation error message

#### Scenario: Password change rejects invalid password
- **WHEN** POST `/auth/change-password` is called with password matching email
- **THEN** request fails with HTTP 400 and validation error message

### Requirement: Validation Error Messages are User-Friendly
The system SHALL return validation errors in consistent format with clear, actionable messages.

#### Scenario: Single error message
- **WHEN** password validation fails for one rule
- **THEN** response includes error message like "Password must contain at least 1 special character (!@#$%^&*)"

#### Scenario: Multiple error messages
- **WHEN** password validation fails for multiple rules
- **THEN** response includes all applicable error messages in array format

