sudo docker run -d --name osiris \
  -p 9000:9000 -p 9009:9009 -p 8812:8812 -p 9003:9003 \
  --ulimit nofile=1048576:1048576 \
  questdb/questdb