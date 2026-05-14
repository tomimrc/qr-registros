/**
 * Configuration context for React application.
 * 
 * Provides application configuration to all components via React Context.
 * Configuration is loaded from the backend `/api/config` endpoint on app initialization.
 */

import React, { createContext, useContext } from 'react';
import { Config } from '../types/config';

/**
 * Configuration context.
 * 
 * Provides config to all components via useConfig() hook.
 */
export const ConfigContext = createContext<Config | null>(null);

/**
 * Hook to access application configuration from anywhere in the React component tree.
 * 
 * @returns Configuration object
 * @throws Error if used outside ConfigProvider
 * 
 * @example
 * ```tsx
 * function MyComponent() {
 *   const config = useConfig();
 *   return <p>API URL: {config.api_base_url}</p>;
 * }
 * ```
 */
export function useConfig(): Config {
  const config = useContext(ConfigContext);
  
  if (!config) {
    throw new Error(
      'useConfig() must be used within a ConfigProvider. ' +
      'Wrap your app with <ConfigProvider> at the root level.'
    );
  }
  
  return config;
}
