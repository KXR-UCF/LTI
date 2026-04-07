
// 1. Force Node.js to treat all Dates as UTC (Must be at the top)
process.env.TZ = 'UTC';

import postgres from 'postgres';

// 2. Define connection options with hardcoded credentials
const sql = postgres({
  host: '127.0.0.1',
  port: 8812,
  username: 'admin',
  password: 'quest',
  database: 'qdb',

  // Pooling & Reliability Settings
  max: 10,                // Max number of connections (NFR-SC1 support)
  idle_timeout: 30,       // Close idle connections after 30s
  connect_timeout: 10,    // Fail fast if DB is down (10s)

  // Transform parameter names (optional, but good for consistency)
  transform: {
    undefined: null,
  },
});

/**
 * Helper to verify database connectivity on startup.
 * Logs success or throws error to prevent "silent failures".
 */
export async function checkConnection(): Promise<boolean> {
  try {
    const result = await sql`SELECT 1 as status`;
    if (result && result.length > 0) {
      console.log('Connected to QuestDB successfully via postgres.js');
      return true;
    }
    return false;
  } catch (error) {
    console.error('Failed to connect to QuestDB:', error);
    // We throw here so the main application knows not to start
    throw error;
  }
}

// Export the singleton instance
export default sql;