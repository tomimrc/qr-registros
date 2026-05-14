## ADDED Requirements

### Requirement: Frontend config API endpoint

The system SHALL expose an unauthenticated API endpoint `/api/config` that returns publicly safe configuration values needed by the React frontend. The endpoint SHALL NOT expose sensitive values like SECRET_KEY, database credentials, or internal secrets.

#### Scenario: Fetch config from backend
- **WHEN** the frontend makes a GET request to `/api/config`
- **THEN** the backend returns HTTP 200 with JSON: `{ "api_base_url": "http://localhost:8000", "app_name": "QR Attendance System", "debug": false, "features": { "email_notifications": true, "n8n_webhooks": true } }`

#### Scenario: Config endpoint is publicly accessible
- **WHEN** a client requests `/api/config` without authentication
- **THEN** the endpoint returns HTTP 200 (authentication is NOT required)

#### Scenario: Sensitive config is never exposed
- **WHEN** the frontend requests `/api/config`
- **THEN** the response does NOT contain: SECRET_KEY, DATABASE_URL, SMTP_PASSWORD, or any other credential

---

### Requirement: Frontend config context provider

The system SHALL provide a React Context that wraps the entire application and validates frontend configuration on initialization. If critical config is missing, the application SHALL display an error page instead of rendering normally.

#### Scenario: Config loads successfully
- **WHEN** the React app initializes and loads config from `/api/config`
- **THEN** ConfigContext is populated with valid config and the application renders normally

#### Scenario: Config fetch fails
- **WHEN** the React app initializes but the `/api/config` endpoint returns an error or times out
- **THEN** the application displays an error page: "Configuration could not be loaded. Please contact support." and does NOT render the main application

#### Scenario: Critical config is missing
- **WHEN** the React app initializes and `/api/config` returns valid JSON but missing required fields (e.g., api_base_url)
- **THEN** the application displays an error page: "Invalid configuration received from server" and does NOT render the main application

#### Scenario: Components access config via hook
- **WHEN** a React component uses the `useConfig()` hook
- **THEN** the component receives the validated config object with full type safety (TypeScript)

---

### Requirement: Feature flag support in frontend config

The system SHALL allow backend configuration to control feature visibility in the frontend via feature flags. Features can be enabled or disabled without redeploying the frontend.

#### Scenario: Feature flag controls conditional rendering
- **WHEN** a component checks `config.features.email_notifications`
- **THEN** the component renders email-related UI only if the feature flag is true

#### Scenario: Feature flag changes on backend require frontend refresh
- **WHEN** a feature flag is toggled on the backend
- **THEN** the frontend must be refreshed to pick up the new flag value (no hot reloading)

---

### Requirement: API endpoint from config

The system SHALL allow the frontend to determine the backend API base URL from configuration, supporting different environments (localhost, staging, production).

#### Scenario: Frontend uses API base URL from config
- **WHEN** the React app makes API calls (e.g., to `/attendance` endpoints)
- **THEN** the app constructs full URLs using `config.api_base_url` (e.g., `http://localhost:8000/api/attendance`)

#### Scenario: API base URL differs per environment
- **WHEN** the application is deployed to production with `BASE_URL=https://api.example.com`
- **THEN** the frontend config endpoint returns `api_base_url: "https://api.example.com"` and the frontend uses this URL
