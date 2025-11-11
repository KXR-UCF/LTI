sudo /home/kxr/LTI-25/Wanda/QuestdbScripts/startQuestDB.sh &
nohup python3 /home/kxr/LTI-25/Wanda/sockets/socket_server.py &
nohup python3 /home/kxr/LTI-25/Wanda/dataingestion.py &