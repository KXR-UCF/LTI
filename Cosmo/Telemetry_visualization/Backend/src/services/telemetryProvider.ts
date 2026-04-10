// src/services/telemetryProvider.ts
import sql from '../db/client';
import { RawTelemetryRow } from '../types/telemetry';

/**
 * Fetches the single most recent telemetry record from QuestDB.
 * Two parallel O(1) queries instead of one O(n) ASOF JOIN.
 */
export async function fetchLatestTelemetry(): Promise<RawTelemetryRow | null> {
  try {
    const [w1Result, w2Result] = await Promise.all([
      sql`SELECT * FROM wanda1 ORDER BY timestamp DESC LIMIT 1`,
      sql`SELECT * FROM wanda2 ORDER BY timestamp DESC LIMIT 1`,
    ]);

    if (!w1Result || w1Result.length === 0) {
      return null;
    }

    const w1 = w1Result[0];
    const w2 = w2Result?.[0];

    return {
      timestamp: w1.timestamp,
      pt1: w1.pt1, pt2: w1.pt2, pt3: w1.pt3, pt4: w1.pt4,
      pt5: w1.pt5, pt6: w1.pt6, pt7: w1.pt7, pt8: w1.pt8,
      pt9: w1.pt9, pt25: w1.pt25,
      continuity_raw: w1.continuity_raw,
      lc1: w2?.lc1 ?? 0, lc2: w2?.lc2 ?? 0,
      lc3: w2?.lc3 ?? 0, lc4: w2?.lc4 ?? 0,
      lc_net_force: w2?.lc_net_force ?? 0,
      tc1: w2?.tc1 ?? 0, tc2: w2?.tc2 ?? 0,
    } as RawTelemetryRow;
  } catch (error) {
    console.error('QuestDB Query Error:', error);
    return null;
  }
}