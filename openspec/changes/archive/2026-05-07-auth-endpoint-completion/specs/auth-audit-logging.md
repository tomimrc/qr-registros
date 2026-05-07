# Spec: auth-audit-logging

## ADDED Requirements

### Requirement: Audit Log Storage
The system SHALL store audit logs in a database table `auth_audit_logs` with the following fields:
- `id` (UUID): Primary key
- `tenant_id` (UUID): Tenant context
- `admin_id` (UUID, nullable): Admin who triggered the event
- `event_type` (enum): Type of auth event
- `ip_address` (string): Client IP from request
- `user_agent` (string): Client user agent
- `timestamp` (datetime UTC): When event occurred
- `details` (JSON): Event-specific metadata
- `success` (boolean): Whether action succeeded

#### Scenario: Login success event logged
- **WHEN** admin successfully logs in via POST `/auth/login`
- **THEN** entry is created in `auth_audit_logs` with event_type=`login_success`

#### Scenario: Login failure event logged
- **WHEN** admin attempts login with wrong password
- **THEN** entry is created in `auth_audit_logs` with event_type=`login_failed`, success=false

#### Scenario: Password change event logged
- **WHEN** admin changes password via POST `/auth/change-password`
- **THEN** entry is created in `auth_audit_logs` with event_type=`password_changed`

#### Scenario: Logout event logged
- **WHEN** admin logs out via POST `/auth/logout`
- **THEN** entry is created in `auth_audit_logs` with event_type=`logout`

#### Scenario: Token refresh event logged
- **WHEN** client refreshes token via POST `/auth/refresh`
- **THEN** entry is created in `auth_audit_logs` with event_type=`token_refreshed`

### Requirement: AuditService Handles Logging
The system SHALL provide `AuditService` with methods to log auth events asynchronously without blocking request handling.

#### Scenario: Audit logging does not block response
- **WHEN** auth event occurs
- **THEN** audit log is written asynchronously (fire-and-forget or background task)

#### Scenario: Audit log method accepts standardized event data
- **WHEN** any auth event occurs
- **THEN** caller provides event_type, admin_id (optional), ip_address, user_agent, details (dict), success (bool)

### Requirement: Audit Logs are Queryable
The system SHALL provide query methods to retrieve audit logs for compliance and investigation.

#### Scenario: Query logs by tenant and date range
- **WHEN** admin queries audit logs via GET `/audit/logs`
- **THEN** results are filtered by tenant_id and date range with pagination

#### Scenario: Query logs by event type
- **WHEN** admin filters logs by event_type
- **THEN** system returns only matching events

#### Scenario: Query logs by admin
- **WHEN** admin filters logs by admin_id
- **THEN** system returns only events triggered by that admin

### Requirement: Audit Log Retention Policy
The system SHALL implement automatic cleanup of old audit logs per retention policy (recommended: 1 year).

#### Scenario: Logs older than 1 year are archived or deleted
- **WHEN** cleanup job runs
- **THEN** logs older than 1 year are archived to separate table or deleted per policy

