import os
import json
from flask import Flask, request, jsonify, render_template
from google.oauth2 import service_account
from google.cloud import dialogflow_v2 as dialogflow
import mongomock

app = Flask(__name__)

# =====================================================================
# CONFIGURACIÓN DE CREDENCIALES (DIALOGFLOW)
# =====================================================================
# Si el proyecto corre en Railway, toma la llave desde la variable de entorno.
# Si estás en tu computadora local, buscará el archivo físico original.
if 'DIALOGFLOW_KEY' in os.environ:
    try:
        key_data = json.loads(os.environ['DIALOGFLOW_KEY'])
        credentials = service_account.Credentials.from_service_account_info(key_data)
        project_id = key_data.get('project_id')
    except Exception as e:
        print(f"Error al procesar la variable DIALOGFLOW_KEY: {e}")
        credentials = None
        project_id = None
else:
    # Configuración de respaldo para tu entorno de desarrollo local (PC)
    local_key_path = 'dialogflow_key.json'
    if os.path.exists(local_key_path):
        credentials = service_account.Credentials.from_service_account_file(local_key_path)
        with open(local_key_path) as f:
            project_id = json.load(f).get('project_id')
    else:
        credentials = None
        project_id = None

# =====================================================================
# RUTAS DE TU APLICACIÓN FLASK
# =====================================================================

@app.route('/')
def home():
    # Renderiza la página principal que está en tu carpeta de plantillas (templates)
    return render_template('index.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    if not credentials or not project_id:
        return jsonify({"reply": "Error de configuración: No se encontraron las credenciales de Dialogflow en el servidor."}), 500

    try:
        data = request.get_json()
        user_message = data.get("message", "")
        session_id = data.get("session_id", "default_session")

        # Conexión con el cliente de Dialogflow usando las credenciales inyectadas
        session_client = dialogflow.SessionsClient(credentials=credentials)
        session = session_client.session_path(project_id, session_id)

        text_input = dialogflow.TextInput(text=user_message, language_code="es")
        query_input = dialogflow.QueryInput(text=text_input)

        response = session_client.detect_intent(request={"session": session, "query_input": query_input})
        bot_reply = response.query_result.fulfillment_text

        return jsonify({"reply": bot_reply})

    except Exception as e:
        print(f"Error durante la comunicación con Dialogflow: {e}")
        return jsonify({"reply": "Hubo un problema al procesar tu mensaje. Inténtalo de nuevo."}), 500

# =====================================================================
# ARRANQUE DEL SERVIDOR (ADAPTADO PARA RAILWAY Y PC)
# =====================================================================
if __name__ == '__main__':
    # PORT es la variable dinámica que Railway inyecta de forma obligatoria.
    # En tu computadora usará el puerto 5000 por defecto.
    port = int(os.environ.get('PORT', 5000))
    
    # 0.0.0.0 es indispensable para que el contenedor escuche peticiones externas
    app.run(host='0.0.0.0', port=port)
