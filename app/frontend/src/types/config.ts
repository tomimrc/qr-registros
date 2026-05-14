/**
 * Configuration types for the frontend application.
 * 
 * These types define the shape of the configuration object
 * returned by the `/api/config` endpoint from the backend.
 */

/**
 * Feature flags configuration.
 * Controls which features are enabled/disabled in the frontend.
 */
export interface FeatureFlags {
  /** Email notification features enabled */
  email_notifications: boolean;
  /** N8N webhook integration enabled */
  n8n_webhooks: boolean;
}

/**
 * Public application configuration.
 * 
 * This configuration is fetched from the `/api/config` endpoint
 * and is safe to expose to frontend clients.
 * 
 * Sensitive fields like SECRET_KEY, DATABASE_URL, and SMTP_PASSWORD
 * are NEVER included here.
 */
export interface Config {
  /** API base URL for backend requests */
  api_base_url: string;
  /** Application name */
  app_name: string;
  /** Debug mode flag */
  debug: boolean;
  /** Logging level */
  log_level: string;
  /** Feature flags */
  features: FeatureFlags;
}

/**
 * Error response from config loading.
 */
export interface ConfigError {
  /** Error message */
  message: string;
  /** Error code or status */
  code?: string;
}
