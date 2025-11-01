# WANDA

This folder contains all data ingestion code on WANDA. The controls socket server in in the [sockets folder](/sockets/).

## Prerequisites

### Python
1. Check Python 3.11.0 or higher is installed  
    ```
    $ python3 --version
    ```

3. Create a virtual enviroment  
    ```
   $ python3 -m venv venv
    ```

4. Enter virtual enviroment  
    ```
   $ source venv/bin/activate
    ```
5. Install `swig` and `liblgpio-dev`
    ```
    $ sudo apt update
    $ sudo apt install swig liblgpio-dev
    ```

6. Install all required python packages in [requirements.txt](requirements.txt)  
    ```
   $ pip install -r requirements.txt
    ```

### QuestDB
Only follow the instructions in this section if a QuestDB docker container is not already set up.

1. Check for any existing QuestDB instances  
    ```
   $ sudo docker container ls -a
    ```  
    Check for any containers using the questdb image, if none found continue.

3. Create QuestDB container  
    ```
   $ sudo ./QuestdbScripts/createQuestDB.sh
    ```  

## Start Data Ingestion

1. Start QuestDB server  
    ```
   $ sudo ./QuestdbScripts/startQuestDB.sh
    ```  

3. Edit [config.yaml](ADC/config.yaml) with current configuration.  
> [!NOTE]  
> Currently all three loadcells must be assigned to a channel

3. Run [dataingestion.py](dataingestion.py)  
    ```
   $ python3 dataingestion.py
    ```

## Currently on the PI

In the home directory of the kxr user, there is a folder ```/home/kxr/LTI25```. This folder currently contains all this code, but a slightly out of data version. That version still requires the socket server and client to be connected and the enable fire key to be turned before data ingestion starts.

To start the code in that version:  

1. Start QuestDB  
    ```
   $ sudo /home/kxr/LTI-25/Wanda/QuestdbScripts/startQuestDB.sh
    ```  

3. Start the socket server  
    ```
   $ python3 /home/kxr/LTI-25/sockets/socket_server.py
    ```

5. Wait for socket client to connect

6. Start questdbTest.py  
    ```
   $ python3 /home/kxr/LTI-25/Wanda/dataingestion.py
    ```

8. Wait for print statement **"connected to questdb"** from questdbTest.py

9. Turn enable fire key

## Notes

The QuestDB dashboard is accessible at http://192.168.1.7:9000
