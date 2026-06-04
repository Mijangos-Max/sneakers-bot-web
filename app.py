import os
import json
from flask import Flask, request, jsonify, render_template
from google.oauth2 import service_account
from google.cloud import dialogflow_v2 as dialogflow
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# Configuración MongoDB
mongo_uri = os.environ.get('MONGO_URI')
try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client['tienda_tenis']
    historial_col = db['historial_chat']
except Exception as e:
    print(f"Error MongoDB: {e}")
    client = None

# Configuración Dialogflow
if 'DIALOGFLOW_KEY' in os.environ:
    key_data = json.loads(os.environ['DIALOGFLOW_KEY'])
    credentials = service_account.Credentials.from_service_account_info(key_data)
    project_id = key_data.get('project_id')
else:
    credentials = None
    project_id = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    
    # Dialogflow
    session_client = dialogflow.SessionsClient(credentials=credentials)
    session = session_client.session_path(project_id, "user-session-123")
    text_input = dialogflow.TextInput(text=user_message, language_code="es")
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(request={"session": session, "query_input": query_input})
    
    # --- LO NUEVO: Extraer parámetros de Dialogflow ---
    result = response.query_result
    bot_reply = result.fulfillment_text
    
    # Extraemos los parámetros (modelo y talla) si existen
    params = dict(result.parameters)
    modelo = params.get('modelo', None)
    talla = params.get('talla', None)

    # Guardar en MongoDB con los datos extraídos
    if client:
        historial_col.insert_one({
            "fecha": datetime.now(),
            "mensaje_usuario": user_message,
            "respuesta_bot": bot_reply,
            "intencion": result.intent.display_name,
            "modelo_detectado": modelo,
            "talla_detectada": talla
        })

    return jsonify({"reply": bot_reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
