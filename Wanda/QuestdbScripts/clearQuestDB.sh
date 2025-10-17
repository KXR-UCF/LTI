#!/usr/bin/env sh

sudo docker stop questdb-test-questdb-1
sudo docker stop questdb-test-grafana-1

sudo docker container rm questdb-test-questdb-1
sudo docker container rm questdb-test-grafana-1

sudo docker volume rm questdb-test_questdb-data
sudo docker volume rm questdb-test_grafana-data