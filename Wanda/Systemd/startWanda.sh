#!/usr/bin/bash

is_controller="true"
questdb_container="questdbscripts-questdb-1"

cd /home/lti/Production/
echo "Using Production Directory"

source /home/lti/venv/bin/activate

if [ "$is_controller" = "true" ] ; then
    echo "Controller Pi Configuration"
    # start questdb container
    sudo docker start $questdb_container
    echo "Sent docker start command"
else
    echo "Worker Pi Configuration"
fi

# check if QuestDB is active
echo "waiting for questdb"
until curl -s http://192.168.1.30:9003/status | grep -q "Healthy"; do
    sleep 1
done
echo "Questdb Active"


socket_pid=''
if [ "$is_controller" = "true" ] ; then
    python3 -u /home/lti/Production/Controls/controllerSocketServer.py >> socket.out 2>&1 &
    socket_pid=$!
    echo "Socket Server Started"
else
    python3 -u /home/lti/Production/Controls/workerSocketClient.py >> socket.out 2>&1 &
    socket_pid=$!
    echo "Socket Client Started"
fi
echo $socket_pid > /home/lti/Production/socket.pid
echo "Saved socket PID [$socket_pid] to file"

python3 -u /home/lti/Production/dataingestion.py >> data.out 2>&1 &
data_pid=$!
echo "Started dataingestion.py"
echo $data_pid > /home/lti/Production/data.pid
echo "Saved data PID [$data_pid] to file"