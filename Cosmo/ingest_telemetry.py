#!/usr/bin/env python3
"""
QuestDB Telemetry Data Ingestion Script (Two-Table Architecture)
Ingests telemetry data at 60 samples per second into wanda1 and wanda2 tables.
"""

import time
import random
import math
from datetime import datetime
from questdb.ingress import Sender
import argparse
import psycopg2


# QuestDB connection configuration
QUESTDB_HTTP_CONF = (
    'http::addr=localhost:9000;'
    'username=admin;'
    'password=quest;'
    'auto_flush=off;'  # Manual flush for better control at 60Hz
)

QUESTDB_PG_CONF = {
    'host': 'localhost',
    'port': 8812,
    'user': 'admin',
    'password': 'quest',
    'database': 'qdb'
}

# Target sampling rate
SAMPLES_PER_SECOND = 60
SAMPLE_INTERVAL = 1.0 / SAMPLES_PER_SECOND  # ~16.67ms per sample

# Rocket burn profile parameters
IGNITION_TIME = 2.0      # Ramp up time (seconds)
BURN_TIME = 20.0         # Steady burn duration (seconds)
SHUTDOWN_TIME = 1.5      # Shutdown time (seconds)
TOTAL_BURN_TIME = IGNITION_TIME + BURN_TIME + SHUTDOWN_TIME

# Performance parameters
MAX_THRUST = 800.0       # Peak thrust in Newtons
MAX_PRESSURE = 2000.0    # Peak chamber pressure in PSI
MAX_CHAMBER_TEMP = 2800.0  # Peak chamber temp in °C
MAX_NOZZLE_TEMP = 1500.0   # Peak nozzle temp in °C

# Noise levels (to simulate real sensor noise)
FORCE_NOISE = 5.0        # ±5N
PRESSURE_NOISE = 20.0    # ±20 PSI
TEMP_NOISE = 10.0        # ±10°C


def setup_tables():
    """
    Check if wanda1 and wanda2 tables exist.
    If they don't exist, create them.
    If they exist, truncate them.
    """
    print("Setting up database tables...\n")

    conn = psycopg2.connect(**QUESTDB_PG_CONF)
    cursor = conn.cursor()

    try:
        # Check if wanda1 exists
        cursor.execute("""
            SELECT table_name
            FROM tables()
            WHERE table_name = 'wanda1'
        """)
        wanda1_exists = cursor.fetchone() is not None

        # Check if wanda2 exists
        cursor.execute("""
            SELECT table_name
            FROM tables()
            WHERE table_name = 'wanda2'
        """)
        wanda2_exists = cursor.fetchone() is not None

        # Handle wanda1
        if wanda1_exists:
            print("✓ Table 'wanda1' exists - truncating...")
            cursor.execute("TRUNCATE TABLE wanda1")
            conn.commit()
        else:
            print("✗ Table 'wanda1' not found - creating...")
            cursor.execute("""
                CREATE TABLE wanda1 (
                    timestamp TIMESTAMP,
                    pt1 DOUBLE,
                    pt2 DOUBLE,
                    pt3 DOUBLE,
                    pt4 DOUBLE,
                    pt5 DOUBLE,
                    pt6 DOUBLE,
                    pt7 DOUBLE,
                    pt8 DOUBLE,
                    pt9 DOUBLE,
                    continuity_raw DOUBLE
                ) TIMESTAMP(timestamp) PARTITION BY DAY
            """)
            conn.commit()
            print("✓ Table 'wanda1' created")

        # Handle wanda2
        if wanda2_exists:
            print("✓ Table 'wanda2' exists - truncating...")
            cursor.execute("TRUNCATE TABLE wanda2")
            conn.commit()
        else:
            print("✗ Table 'wanda2' not found - creating...")
            cursor.execute("""
                CREATE TABLE wanda2 (
                    timestamp TIMESTAMP,
                    lc1 DOUBLE,
                    lc2 DOUBLE,
                    lc3 DOUBLE,
                    lc4 DOUBLE,
                    lc_net_force DOUBLE,
                    tc1 DOUBLE,
                    tc2 DOUBLE
                ) TIMESTAMP(timestamp) PARTITION BY DAY
            """)
            conn.commit()
            print("✓ Table 'wanda2' created")

        print("\n✅ Database setup complete!\n")

    except Exception as e:
        print(f"❌ Error setting up tables: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def rocket_burn_profile(t, duration_seconds):
    """
    Generate realistic rocket motor burn profile.

    Returns a value between 0 and 1 representing the burn intensity at time t.

    Phases:
    1. Ignition (0 to IGNITION_TIME): Rapid ramp up
    2. Steady burn (IGNITION_TIME to IGNITION_TIME+BURN_TIME): Steady with slight variations
    3. Shutdown (after BURN_TIME): Rapid decay
    4. Post-burn: Zero
    """
    if t < 0:
        return 0.0

    # Phase 1: Ignition - smooth S-curve ramp up
    if t < IGNITION_TIME:
        # Smooth sigmoid curve for ignition
        progress = t / IGNITION_TIME
        return 0.5 * (1 + math.tanh(8 * (progress - 0.5)))

    # Phase 2: Steady burn with slight oscillations
    elif t < IGNITION_TIME + BURN_TIME:
        burn_progress = (t - IGNITION_TIME) / BURN_TIME
        # 100% thrust with slight sinusoidal variations
        base = 1.0
        # Add some realistic oscillations (combustion instabilities)
        oscillation = 0.02 * math.sin(10 * t) + 0.01 * math.sin(23 * t)
        # Slight decay over time (propellant consumption)
        decay = 1.0 - 0.05 * burn_progress
        return (base + oscillation) * decay

    # Phase 3: Shutdown - rapid exponential decay
    elif t < IGNITION_TIME + BURN_TIME + SHUTDOWN_TIME:
        shutdown_progress = (t - IGNITION_TIME - BURN_TIME) / SHUTDOWN_TIME
        return math.exp(-5 * shutdown_progress)

    # Phase 4: Post-burn
    else:
        return 0.0


def generate_sample_data(elapsed_time, duration_seconds):
    """
    Generate realistic rocket motor telemetry data for wanda1 and wanda2 tables.
    Simulates a complete burn cycle with ignition, steady burn, and shutdown.

    Returns tuple: (wanda1_data, wanda2_data)
    """
    # Get burn profile intensity (0 to 1)
    intensity = rocket_burn_profile(elapsed_time, duration_seconds)

    # Add sensor noise
    def add_noise(value, noise_level):
        return max(0, value + random.uniform(-noise_level, noise_level))

    # === WANDA2: THRUST / LOAD CELLS ===
    # Individual thrust sensors (4 sensors)
    lc1 = add_noise(200 - (elapsed_time / TOTAL_BURN_TIME) * 100, FORCE_NOISE)  # Nox Tank Weight
    lc2 = add_noise(MAX_THRUST * intensity * 0.33, FORCE_NOISE)  # Thrust 1
    lc3 = add_noise(MAX_THRUST * intensity * 0.35, FORCE_NOISE)  # Thrust 2
    lc4 = add_noise(MAX_THRUST * intensity * 0.32, FORCE_NOISE)  # Thrust 3
    lc_net_force = lc2 + lc3 + lc4

    # === WANDA1: PRESSURE TRANSDUCERS ===
    # Main chamber pressure correlates with thrust
    chamber_pressure = add_noise(MAX_PRESSURE * intensity, PRESSURE_NOISE)

    pt01 = add_noise(1800 * intensity, PRESSURE_NOISE * 0.8)  # N2 Inlet
    pt02 = add_noise(1200 * intensity, PRESSURE_NOISE * 0.7)  # NOX Inlet
    pt03 = add_noise(800 * intensity, PRESSURE_NOISE * 0.6)   # Dome Reg
    pt04 = add_noise(3000 * intensity, PRESSURE_NOISE * 0.9)  # N2 Tank
    pt05 = add_noise(900 * intensity, PRESSURE_NOISE * 0.6)   # Fuel Tank
    pt06 = chamber_pressure                                    # Chamber A
    pt07 = add_noise(chamber_pressure * 0.98, PRESSURE_NOISE * 0.5)  # Chamber B
    pt08 = add_noise(850 * intensity, PRESSURE_NOISE * 0.6)   # Fuel Feed

    # Continuity sensor (dummy value for now)
    continuity_raw = 5.0 if intensity > 0.1 else 0.0

    # === WANDA2: TEMPERATURES ===
    # Temperature lags behind thrust due to thermal mass
    temp_lag_factor = min(1.0, elapsed_time / 5.0)  # Takes 5s to reach full temp

    # TC-1: Nitrous feed temperature (cryogenic when flowing)
    if intensity > 0.1:
        tc1 = add_noise(-20 + (30 * intensity * temp_lag_factor), TEMP_NOISE * 0.5)
    else:
        tc1 = add_noise(20, TEMP_NOISE * 0.2)  # Ambient when not flowing

    # TC-2: Chamber temperature
    tc2 = add_noise(MAX_CHAMBER_TEMP * intensity * temp_lag_factor, TEMP_NOISE)

    # PT-9: HPA pressure (mapped to W1ADC1CH2)
    pt9 = add_noise(1500 * intensity, PRESSURE_NOISE * 0.7)  # HPA

    # Prepare data for each table
    wanda1_data = {
        'pt1': round(pt01, 2),
        'pt2': round(pt02, 2),
        'pt3': round(pt03, 2),
        'pt4': round(pt04, 2),
        'pt5': round(pt05, 2),
        'pt6': round(pt06, 2),
        'pt7': round(pt07, 2),
        'pt8': round(pt08, 2),
        'pt9': round(pt9, 2),
        'continuity_raw': round(continuity_raw, 2)
    }

    wanda2_data = {
        'lc1': round(lc1, 2),
        'lc2': round(lc2, 2),
        'lc3': round(lc3, 2),
        'lc4': round(lc4, 2),
        'lc_net_force': round(lc_net_force, 2),
        'tc1': round(tc1, 2),
        'tc2': round(tc2, 2)
    }

    return wanda1_data, wanda2_data


def ingest_telemetry(duration_seconds, batch_size=1):
    """
    Ingest telemetry data at 60 samples per second into wanda1 and wanda2 tables.

    Args:
        duration_seconds: How long to run the ingestion (seconds)
        batch_size: Number of rows to batch before flushing (default: 1 for real-time)
    """
    total_samples = duration_seconds * SAMPLES_PER_SECOND
    samples_sent = 0

    print(f"Starting telemetry ingestion:")
    print(f"  - Duration: {duration_seconds} seconds")
    print(f"  - Target rate: {SAMPLES_PER_SECOND} samples/second")
    print(f"  - Total samples: {total_samples}")
    print(f"  - Batch size: {batch_size} rows")
    print(f"  - Sample interval: {SAMPLE_INTERVAL*1000:.2f}ms\n")

    try:
        with Sender.from_conf(QUESTDB_HTTP_CONF) as sender:
            print("Connected to QuestDB\n")

            start_time = time.time()
            next_sample_time = start_time
            last_report_time = start_time

            while samples_sent < total_samples:
                # Calculate elapsed time for this sample
                elapsed_time = samples_sent / SAMPLES_PER_SECOND

                # Generate sample data for both tables
                wanda1_data, wanda2_data = generate_sample_data(elapsed_time, duration_seconds)

                # Use same timestamp for both tables
                timestamp = datetime.now()

                # Send to wanda1
                sender.row(
                    'wanda1',
                    columns=wanda1_data,
                    at=timestamp
                )

                # Send to wanda2
                sender.row(
                    'wanda2',
                    columns=wanda2_data,
                    at=timestamp
                )

                samples_sent += 1

                # Flush batch periodically
                if samples_sent % batch_size == 0:
                    sender.flush()

                # Progress reporting every second
                current_time = time.time()
                if current_time - last_report_time >= 1.0:
                    elapsed = current_time - start_time
                    actual_rate = samples_sent / elapsed
                    progress = (samples_sent / total_samples) * 100
                    print(f"Progress: {progress:.1f}% | "
                          f"Samples: {samples_sent}/{total_samples} | "
                          f"Rate: {actual_rate:.1f} samples/sec")
                    last_report_time = current_time

                # Precise timing control
                next_sample_time += SAMPLE_INTERVAL
                sleep_time = next_sample_time - time.time()

                if sleep_time > 0:
                    time.sleep(sleep_time)
                elif sleep_time < -SAMPLE_INTERVAL:
                    # If we're falling behind by more than one interval, resync
                    print(f"Warning: Falling behind schedule by {-sleep_time*1000:.1f}ms")
                    next_sample_time = time.time()

            # Final flush
            sender.flush()

            # Final statistics
            total_time = time.time() - start_time
            actual_rate = samples_sent / total_time

            print(f"\n{'='*60}")
            print(f"Ingestion Complete!")
            print(f"  - Total samples sent: {samples_sent} (to BOTH tables)")
            print(f"  - Total time: {total_time:.2f} seconds")
            print(f"  - Actual rate: {actual_rate:.2f} samples/second")
            print(f"  - Target rate: {SAMPLES_PER_SECOND} samples/second")
            print(f"  - Accuracy: {(actual_rate/SAMPLES_PER_SECOND)*100:.2f}%")
            print(f"{'='*60}\n")

    except KeyboardInterrupt:
        print(f"\n\nInterrupted by user after {samples_sent} samples")
    except Exception as e:
        print(f"\nError during ingestion: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Ingest telemetry data into QuestDB wanda1/wanda2 tables at 60 samples per second'
    )
    parser.add_argument(
        'duration',
        type=int,
        help='Duration to run ingestion in seconds'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1,
        help='Number of rows to batch before flushing (default: 1 for real-time)'
    )

    args = parser.parse_args()

    if args.duration <= 0:
        print("Error: Duration must be positive")
        return

    # Setup tables (create if not exist, truncate if exist)
    setup_tables()

    # Start ingestion
    ingest_telemetry(args.duration, args.batch_size)


if __name__ == '__main__':
    main()
