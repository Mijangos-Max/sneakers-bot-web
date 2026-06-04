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
    db = client['tienda_tenis'] 
    historial_col = db['historial_chat']
    print("Conexión a MongoDB exitosa")
except Exception as e:
    print(f"Error conectando a MongoDB: {e}")
    client = None

# --- CONFIGURACIÓN DE DIALOGFLOW ---
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
    
    # Procesar con Dialogflow
    session_client = dialogflow.SessionsClient(credentials=credentials)
    session = session_client.session_path(project_id, "user-session-123")
    query_input = dialogflow.QueryInput(text=dialogflow.TextInput(text=user_message, language_code="es"))
    response = session_client.detect_intent(request={"session": session, "query_input": query_input})
    
    result = response.query_result
    intent_name = result.intent.display_name
    bot_reply = result.fulfillment_text

    # 1. LÓGICA PARA EL CARRITO
    if intent_name == "Ver_Carrito":
        if client:
            items = list(historial_col.find({"modelo": {"$ne": None}}).sort("fecha", -1).limit(3))
            if items:
                lista_nombres = ", ".join([str(i.get('modelo', 'desconocido')) for i in items])
                bot_reply = f"En tu carrito tienes: {lista_nombres}."
            else:
                bot_reply = "Tu carrito está vacío."
        else:
            bot_reply = "Error de conexión con la base de datos."

    # 2. Guardar interacción (solo si detecta un modelo)
    elif client:
        params = dict(result.parameters)
        modelo_detectado = params.get('modelo')
        
        # Solo guardamos si el usuario pidió un modelo, para no llenar la BD con saludos
        if modelo_detectado:
            historial_col.insert_one({
                "fecha": datetime.now(),
                "mensaje_usuario": user_message,
                "respuesta_bot": bot_reply,
                "intencion_detectada": intent_name,
                "modelo": modelo_detectado,
                "talla": params.get('talla')
            })

    # Asegurar respuesta mínima si Dialogflow devuelve vacío
    if not bot_reply:
        bot_reply = "¡Claro! ¿En qué más puedo ayudarte?"

    return jsonify({"reply": bot_reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
