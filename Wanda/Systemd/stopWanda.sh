#!/usr/bin/bash

is_controller="true"
questdb_container="questdbscripts-questdb-1"

cd /home/lti/Production/
echo "Using Production Directory"

kill -9 `cat /home/lti/Production/socket.pid`
rm /home/lti/Production/socket.pid
echo "Killed socket process"

kill -9 `cat /home/lti/Production/data.pid`
rm /home/lti/Production/data.pid
echo "Killed data ingestion process"

sudo docker stop $questdb_container
echo "killed docker container"