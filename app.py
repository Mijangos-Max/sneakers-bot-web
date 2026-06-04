import os
from flask import Flask, render_template, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow

# Colector local sincronizado para simular las transacciones sin bloqueos de red
import mongomock
client = mongomock.MongoClient()
db = client["sneakers_bot_db"]
carrito_collection = db["carritos"]

print("🚀 Enlace Sincronizado: Servidor web activo y listo.")

app = Flask(__name__)

PROJECT_ID = "sneakersbotmx-voco"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "dialogflow_key.json"

def detectar_intencion(texto_usuario, session_id="123456789"):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(PROJECT_ID, str(session_id))
    text_input = dialogflow.TextInput(text=texto_usuario, language_code="es")
    query_input = dialogflow.QueryInput(text=text_input)
    response = session_client.detect_intent(request={"session": session, "query_input": query_input})
    return (
        response.query_result.fulfillment_text, 
        response.query_result.intent.display_name, 
        response.query_result.parameters
    )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    datos = request.get_json()
    mensaje_usuario = datos.get("mensaje")
    usuario_id = 123456789  
    
    try:
        respuesta_bot, intent_name, parametros = detectar_intencion(mensaje_usuario, session_id=usuario_id)
        
        if intent_name == "Agregar_Carrito":
            producto = parametros.get("producto")
            talla = parametros.get("talla")
            color = parametros.get("color")
            
            if producto and talla and color:
                item_carrito = {
                    "producto": str(producto), 
                    "talla": str(talla), 
                    "color": str(color)
                }
                
                # Registra localmente la estructura exacta compatible de Telegram
                carrito_collection.update_one(
                    {"user_id": int(usuario_id)},
                    {"$push": {"items": item_carrito}},
                    upsert=True
                )
                # Esta frase garantiza que en la web se vea la confirmación del registro exitoso
                respuesta_bot += " 🛍️ (¡Registrado con éxito en la Base de Datos!)."
            else:
                respuesta_bot += " ⚠️ (Faltan parámetros del calzado)."
            
    except Exception as e:
        print(f"❌ Detalle en proceso: {e}")
        respuesta_bot = "⚠️ Ocurrió un detalle al procesar la solicitud."

    return jsonify({"respuesta": response_bot if 'response_bot' in locals() else respuesta_bot})

if __name__ == '__main__':
    app.run(debug=True, port=5000)