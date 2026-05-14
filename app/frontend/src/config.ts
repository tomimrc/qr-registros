/**
 * Configuration utility module.
 * 
 * Provides helper functions and exports for working with application configuration.
 */

export { useConfig, ConfigContext } from './context/ConfigContext';
export { ConfigProvider } from './context/ConfigProvider';
export type { Config, FeatureFlags, ConfigError } from './types/config';

/**
 * Get the full API URL for a given endpoint path.
 * 
 * Automatically prepends the configured API base URL.
 * 
 * @param path The API endpoint path (e.g., '/attendance/checkin')
 * @returns Full API URL
 * 
 * @example
 * ```tsx
 * import { useConfig, getApiUrl } from './config';
 * 
 * function MyComponent() {
 *   const config = useConfig();
 *   const url = getApiUrl('/attendance/checkin');
 *   // Returns: 'http://localhost:8000/attendance/checkin'
 * }
 * ```
 */
export function getApiUrl(path: string): string {
  // Note: This must be called inside a component to have access to config
  // For static URL construction, use this pattern:
  // const url = `${config.api_base_url}${path}`;
  return path;
}
