# Spec: auth-service

## ADDED Requirements

### Requirement: Extract Auth Business Logic to Service
The system SHALL extract all authentication business logic from the router layer into a dedicated `AuthService` class. The service MUST handle user registration, credential verification, password management, and account status checks independently of HTTP concerns.

#### Scenario: Register new admin via service
- **WHEN** `AuthService.register()` is called with valid email, password, name, and tenant_id
- **THEN** the service creates a new admin with hashed password and returns admin object with success status

#### Scenario: Register fails with duplicate email
- **WHEN** `AuthService.register()` is called with an email that already exists
- **THEN** the service raises `AuthError` with code `DUPLICATE_EMAIL`

#### Scenario: Register fails with inactive tenant
- **WHEN** `AuthService.register()` is called with an inactive tenant_id
- **THEN** the service raises `AuthError` with code `TENANT_NOT_FOUND`

### Requirement: Service-Layer Credential Verification
The system SHALL provide `AuthService.verify_credentials()` method that validates username/password pairs and returns admin object if valid, or raises specific exception if invalid.

#### Scenario: Valid credentials return admin
- **WHEN** `AuthService.verify_credentials()` is called with valid email and password
- **THEN** the service returns the admin object with is_active=True

#### Scenario: Invalid password raises exception
- **WHEN** `AuthService.verify_credentials()` is called with correct email but wrong password
- **THEN** the service raises `AuthError` with code `INVALID_CREDENTIALS`

#### Scenario: Inactive admin raises exception
- **WHEN** `AuthService.verify_credentials()` is called for an inactive admin
- **THEN** the service raises `AuthError` with code `ADMIN_INACTIVE`

### Requirement: Service-Layer Password Change
The system SHALL provide `AuthService.change_password()` method that validates old password, enforces new password rules, and updates the admin's password.

#### Scenario: Password changed successfully
- **WHEN** `AuthService.change_password()` is called with correct old password and valid new password
- **THEN** the password is updated and `AuditService` logs the event

#### Scenario: Wrong old password rejected
- **WHEN** `AuthService.change_password()` is called with incorrect old password
- **THEN** the service raises `AuthError` with code `INVALID_OLD_PASSWORD`

### Requirement: Router Delegates to AuthService
The system SHALL update all routers in `app/routers/auth.py` to delegate business logic to `AuthService` instead of handling it directly. Routers MUST focus only on HTTP request/response handling and Pydantic validation.

#### Scenario: POST /auth/register calls service
- **WHEN** POST `/auth/register` is called with valid request
- **THEN** the router calls `AuthService.register()`, receives result, and returns HTTP 201

#### Scenario: POST /auth/login calls service
- **WHEN** POST `/auth/login` is called with valid credentials
- **THEN** the router calls `AuthService.verify_credentials()` and returns token response

