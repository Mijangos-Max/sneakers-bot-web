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
    # Asegúrate de que esta línea en app.py coincida con el nombre que creaste
    db = client['tienda_tenis'] 
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
    
    # 1. Dialogflow procesa el mensaje
    session_client = dialogflow.SessionsClient(credentials=credentials)
    session = session_client.session_path(project_id, "user-session-123")
    query_input = dialogflow.QueryInput(text=dialogflow.TextInput(text=user_message, language_code="es"))
    response = session_client.detect_intent(request={"session": session, "query_input": query_input})
    
    result = response.query_result
    intent_name = result.intent.display_name
    bot_reply = result.fulfillment_text

    # 2. LOGICA PARA EL CARRITO
    if intent_name == "Ver_Carrito": # Asegúrate que el nombre sea EXACTO como en Dialogflow
        if client:
            # Buscamos en MongoDB lo que el usuario ha pedido recientemente
            items = list(historial_col.find({"modelo": {"$ne": None}}).sort("fecha", -1).limit(3))
            if items:
                lista_nombres = ", ".join([i.get('modelo', 'desconocido') for i in items])
                bot_reply = f"En tu carrito tienes: {lista_nombres}."
            else:
                bot_reply = "Tu carrito está actualmente vacío."
        else:
            bot_reply = "No puedo conectar a la base de datos para ver tu carrito."

    # 3. Guardar interacción en MongoDB (si no es la consulta del carrito)
    elif client and intent_name != "Ver_Carrito":
        params = dict(result.parameters)
        historial_col.insert_one({
            "fecha": datetime.now(),
            "mensaje_usuario": user_message,
            "respuesta_bot": bot_reply,
            "intencion_detectada": intent_name,
            "modelo": params.get('modelo'),
            "talla": params.get('talla')
        })

    return jsonify({"reply": bot_reply})

if __name__ == '__main__':
    # Puerto 8080 es estándar en Railway
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
