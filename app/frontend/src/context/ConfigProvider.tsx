/**
 * Configuration provider component.
 * 
 * Wraps the React application and loads configuration from the backend.
 * Handles loading states, errors, and validation of configuration.
 */

import React, { useEffect, useState, ReactNode } from 'react';
import { ConfigContext } from './ConfigContext';
import { Config, ConfigError } from '../types/config';

interface ConfigProviderProps {
  children: ReactNode;
  configUrl?: string; // Allow override for testing
}

/**
 * Configuration error boundary component.
 * Displays a user-friendly error page if config loading fails.
 */
function ConfigErrorPage({ error }: { error: ConfigError }): JSX.Element {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#f3f4f6',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          padding: '2rem',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          maxWidth: '500px',
          textAlign: 'center',
        }}
      >
        <h1 style={{ color: '#dc2626', marginTop: 0 }}>Configuration Error</h1>
        <p style={{ color: '#666', marginBottom: '1rem' }}>
          {error.message || 'Failed to load application configuration. Please try again or contact support.'}
        </p>
        <button
          onClick={() => window.location.reload()}
          style={{
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            padding: '0.5rem 1rem',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem',
          }}
        >
          Retry
        </button>
      </div>
    </div>
  );
}

/**
 * Configuration loading spinner.
 */
function ConfigLoadingPage(): JSX.Element {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#f3f4f6',
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            border: '4px solid #e5e7eb',
            borderTop: '4px solid #3b82f6',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 1rem',
          }}
        />
        <p style={{ color: '#666', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
          Loading configuration...
        </p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    </div>
  );
}

/**
 * Validates that config has all required fields.
 * @throws ConfigError if validation fails
 */
function validateConfig(config: unknown): asserts config is Config {
  if (!config || typeof config !== 'object') {
    throw new Error('Configuration is not an object');
  }

  const cfg = config as Record<string, unknown>;

  // Required fields
  const requiredFields = ['api_base_url', 'app_name'];
  for (const field of requiredFields) {
    if (typeof cfg[field] !== 'string' || !cfg[field]) {
      throw new Error(`Configuration missing required field: ${field}`);
    }
  }

  // Validate debug flag
  if (typeof cfg.debug !== 'boolean') {
    throw new Error('Configuration field "debug" must be a boolean');
  }

  // Validate log_level
  if (typeof cfg.log_level !== 'string' || !cfg.log_level) {
    throw new Error('Configuration field "log_level" must be a non-empty string');
  }

  // Validate features object
  if (!cfg.features || typeof cfg.features !== 'object') {
    throw new Error('Configuration field "features" must be an object');
  }
}

/**
 * ConfigProvider component.
 * 
 * Must wrap the entire application to provide configuration to all components.
 * 
 * @example
 * ```tsx
 * <ConfigProvider>
 *   <App />
 * </ConfigProvider>
 * ```
 */
export function ConfigProvider({ children, configUrl }: ConfigProviderProps): JSX.Element {
  const [config, setConfig] = useState<Config | null>(null);
  const [error, setError] = useState<ConfigError | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadConfig(): Promise<void> {
      try {
        const url = configUrl || '/api/config';

        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 5000, // 5 second timeout
        } as RequestInit & { timeout: number });

        if (!response.ok) {
          throw new Error(`Configuration endpoint returned ${response.status}`);
        }

        const data: unknown = await response.json();

        // Validate the configuration
        validateConfig(data);

        setConfig(data);
        setError(null);
        console.log('[ConfigProvider] Configuration loaded successfully');
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        const configError: ConfigError = {
          message: `Configuration could not be loaded: ${errorMessage}. Please contact support if this persists.`,
          code: 'CONFIG_LOAD_ERROR',
        };
        setError(configError);
        console.error('[ConfigProvider] Configuration loading failed:', configError);
      } finally {
        setIsLoading(false);
      }
    }

    loadConfig();
  }, [configUrl]);

  // Show error page if configuration failed to load
  if (error) {
    return <ConfigErrorPage error={error} />;
  }

  // Show loading page while configuration is loading
  if (isLoading || !config) {
    return <ConfigLoadingPage />;
  }

  // Provide config to all child components
  return (
    <ConfigContext.Provider value={config}>
      {children}
    </ConfigContext.Provider>
  );
}
