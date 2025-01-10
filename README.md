# Автоматизирано отдалечено декриптиране на устройства за съхранение на информация

- Virtual Enviorment of Master - `/env_master`
- Virtual Enviorment of Node - `/env_node`
- Prove of Concept - `/PoC`


## How to run the Master
1. Be in the correct python enviorment - `.\env_master\Scripts\Activate.ps1` (Windows) or `source \env_master\Scripts\activate`
2. Get in the right directory - `cd /PoC/master`
3. Start the server - `uvicorn server:app --host 0.0.0.0 --port 8000`
    - This will create a `nodes.db` file - the local database


## How to run the Node
1. Be in the correct python enviorment - `.\env_node\Scripts\Activate.ps1` (Windows) or `source \env_node\Scripts\activate`
2. Get in the right directory - `cd /PoC/node`
3. Start the server - `python node.py`
