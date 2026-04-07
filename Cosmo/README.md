# COSMO WANDA - Launch Test & Infrastructure

Real-time telemetry system for rocket motor testing with dual Raspberry Pi data acquisition.

## Prerequisites

- Node.js v18+
- Python 3.8+
- QuestDB

## Complete Setup

### 1. Install QuestDB
```bash
# macOS with Homebrew
brew install questdb

# Alternative: Download from https://questdb.io/get-questdb/
```

### 2. Start QuestDB Database
```bash
questdb start
```
- Database runs on port 8812 (PostgreSQL Wire)
- Web console available at http://localhost:9000

### 3. Create Database Tables
Open QuestDB web console (http://localhost:9000) and run:
```sql
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
    pt25 DOUBLE,
    continuity_raw DOUBLE
) TIMESTAMP(timestamp) PARTITION BY DAY WITH maxUncommittedRows=1, o3MaxLag=1ms;

CREATE TABLE wanda2 (
    timestamp TIMESTAMP,
    lc1 DOUBLE,
    lc2 DOUBLE,
    lc3 DOUBLE,
    lc4 DOUBLE,
    lc_net_force DOUBLE,
    tc1 DOUBLE,
    tc2 DOUBLE
) TIMESTAMP(timestamp) PARTITION BY DAY WITH maxUncommittedRows=1, o3MaxLag=1ms;
```

### 4. Install Dependencies
```bash
# Backend
cd Backend
npm install

# Frontend
cd Frontend/vite-project
npm install
```

## Running the System

**Terminal 1 - Backend:**
```bash
cd Backend
npm run dev
```
- WebSocket server runs on port 3001
- Polls QuestDB at 60Hz

**Terminal 2 - Frontend:**
```bash
cd Frontend/vite-project
npm run dev
```
- Dashboard available at http://localhost:5173

## Shutting Down

### 1. Stop Frontend
```bash
# In frontend terminal:
Ctrl + C
```

### 2. Stop Backend
```bash
# In backend terminal:
Ctrl + C
```

### 3. Stop QuestDB
```bash
questdb stop
```

## Testing with Sample Data

The `ingest_telemetry.py` script generates realistic telemetry data for testing.

### Prerequisites
```bash
pip install questdb psycopg2-binary
```

### Running the Script

**Basic usage (30 seconds of data at 60Hz):**
```bash
cd cosmo
python ingest_telemetry.py 30
```

**Custom duration and batch size:**
```bash
python ingest_telemetry.py 60 --batch-size 20
```

### What It Does
- Automatically creates/truncates `wanda1` and `wanda2` tables
- Generates realistic rocket burn profile data
- Ingests at 60 samples per second to both tables
- Uses same timestamp for synchronized data

### Example Output
```
Setting up database tables...
✓ Table 'wanda1' exists - truncating...
✓ Table 'wanda2' exists - truncating...
✅ Database setup complete!

Starting telemetry ingestion:
  - Duration: 30 seconds
  - Target rate: 60 samples/second

Progress: 10.0% | Samples: 180/1800 | Rate: 60.1 samples/sec
...
============================================================
Ingestion Complete!
  - Total samples sent: 1800 (to BOTH tables)
  - Accuracy: 99.95%
============================================================
```
