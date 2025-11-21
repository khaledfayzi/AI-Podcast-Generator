# NOTE: Datenbankverbindung
# Verwaltet die technische Verbindung zur MongoDB-Instanz.
#
# Einzufügen / Umzusetzen:
# - Funktion 'init_db()':
#   1. Erstellt einen asynchronen Motor-Client.
#   2. Verbindet sich mit der Datenbank 'podcast_db'.
#   3. Initialisiert Beanie mit den Modellen aus models.py.
#
# Diese Datei stellt sicher, dass die Datenbank bereit ist, bevor die App startet.

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from config import MONGODB_URI
uri = MONGODB_URI
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)