import os
import json
from flask import Flask, request, jsonify, render_template
from google.oauth2 import service_account
from google.cloud import dialogflow_v2 as dialogflow
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURACIÓN DE MONGO DB ---
mongo_uri = os.environ.get('MONGO_URI')
try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client['tienda_tenis'] # Asegúrate de que este sea tu nombre de BD
    historial_col = db['historial_chat']
    print("Conexión a MongoDB exitosa")
except Exception as e:
    print(f"Error conectando a MongoDB: {e}")
    client = None

# --- CONFIGURACIÓN DE DIALOGFLOW ---
# Asegúrate de tener la variable DIALOGFLOW_KEY en Railway con el JSON de tus credenciales
if 'DIALOGFLOW_KEY' in os.environ:
    key_dict = json.loads(os.environ['DIALOGFLOW_KEY'])
    credentials = service_account.Credentials.from_service_account_info(key_dict)
    project_id = key_dict.get('project_id')
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
    
    if not credentials or not project_id:
        return jsonify({"reply": "Error de configuración del bot"}), 500

    # --- DIALOGFLOW: Procesar el mensaje ---
    session_client = dialogflow.SessionsClient(credentials=credentials)
    session = session_client.session_path(project_id, "user-session-123")
    text_input = dialogflow.TextInput(text=user_message, language_code="es")
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(request={"session": session, "query_input": query_input})
    
    # --- EXTRACCIÓN DE DATOS ---
    result = response.query_result
    bot_reply = result.fulfillment_text
    intent_name = result.intent.display_name
    
    # Extraemos los parámetros definidos en Dialogflow
    params = dict(result.parameters)
    modelo = params.get('modelo')
    talla = params.get('talla')

    # --- GUARDAR EN MONGO DB ---
    if client:
        try:
            historial_col.insert_one({
                "fecha": datetime.now(),
                "mensaje_usuario": user_message,
                "respuesta_bot": bot_reply,
                "intencion_detectada": intent_name,
                "modelo": modelo,
                "talla": talla
            })
        except Exception as e:
            print(f"Error al guardar en MongoDB: {e}")

    return jsonify({"reply": bot_reply})

if __name__ == '__main__':
    # Puerto 8080 es estándar en Railway
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
