#!/usr/bin/env sh

questdbPort=9000
volume="questdb-test"
containerName="questdb-test"

table=$(cat <<EOF
CREATE TABLE telemetry_data (
  timestamp TIMESTAMP,
  cell1_force DOUBLE,
  cell2_force DOUBLE,
  cell3_force DOUBLE,
  net_force DOUBLE,
  pressure_pt1 DOUBLE,
  pressure_pt2 DOUBLE,
  pressure_pt3 DOUBLE,
  pressure_pt4 DOUBLE,
  pressure_pt5 DOUBLE,
  pressure_pt6 DOUBLE,
  weight_load_cell DOUBLE,
  chamber_temp DOUBLE,
  nozzle_temp DOUBLE
) TIMESTAMP(timestamp) PARTITION BY DAY;
CREATE TABLE controls_data (
timestamp TIMESTAMP,
  switch_1 BOOLEAN,
  switch_2 BOOLEAN,
  switch_3 BOOLEAN,
  switch_4 BOOLEAN,
  switch_5 BOOLEAN,
  switch_6 BOOLEAN,
  switch_7 BOOLEAN,
  switch_8 BOOLEAN,
  switch_9 BOOLEAN,
  switch_10 BOOLEAN,
  bt_1 BOOLEAN,
  bt_2 BOOLEAN,
  bt_3 BOOLEAN,
  bt_4 BOOLEAN,
  bt_5 BOOLEAN,
  abort BOOLEAN,
  enable_fire BOOLEAN,
  fire BOOLEAN
) TIMESTAMP(timestamp) PARTITION BY DAY;
EOF
)

# sudo docker volume create $volume
# sudo docker run --name $containerName -d -p 9000:9000 -p 9009:9009 -p 8812:8812 -p 9003:9003 -v "$volume:/var/lib/questdb" questdb/questdb:latest

# start QuestDB and Grafana
sudo docker compose up -d

# check if QuestDB is active
until curl -s http://localhost:9003/status | grep -q "Healthy"; do
    echo "waiting for questdb"
    sleep 1
done

# create tables in QuestDB
curl -G \
    --data-urlencode "query=$table" \
    http://localhost:9000/exec