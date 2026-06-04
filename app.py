import os
import json
from flask import Flask, request, jsonify, render_template
from google.oauth2 import service_account
from google.cloud import dialogflow_v2 as dialogflow
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# 1. CONFIGURACIÓN DE BASE DE DATOS (MONGODB)
# Asegúrate de tener la variable MONGO_URI en la configuración de Railway
mongo_uri = os.environ.get('MONGO_URI', 'mongodb+srv://tu_usuario:tu_password@cluster.mongodb.net/tienda_tenis')
client = MongoClient(mongo_uri)
db = client['tienda_tenis']
historial_col = db['historial_chat']

# 2. CONFIGURACIÓN DE DIALOGFLOW
if 'DIALOGFLOW_KEY' in os.environ:
    key_data = json.loads(os.environ['DIALOGFLOW_KEY'])
    credentials = service_account.Credentials.from_service_account_info(key_data)
    project_id = key_data.get('project_id')
else:
    credentials = None
    project_id = None

# 3. FUNCIONES DE APOYO
def guardar_en_db(mensaje, respuesta):
    try:
        historial_col.insert_one({
            "fecha": datetime.now(),
            "mensaje_usuario": mensaje,
            "respuesta_bot": respuesta
        })
    except Exception as e:
        print(f"Error al guardar en MongoDB: {e}")

# 4. RUTAS
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    if not credentials or not project_id:
        return jsonify({"reply": "Error: Credenciales no configuradas."}), 500

    data = request.get_json()
    user_message = data.get("message", "")
    
    # Conexión Dialogflow
    session_client = dialogflow.SessionsClient(credentials=credentials)
    session = session_client.session_path(project_id, "user-session-123")
    text_input = dialogflow.TextInput(text=user_message, language_code="es")
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(request={"session": session, "query_input": query_input})
    bot_reply = response.query_result.fulfillment_text

    # Guardar en MongoDB (Punto NoSQL/JSON)
    guardar_en_db(user_message, bot_reply)

    return jsonify({"reply": bot_reply})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
