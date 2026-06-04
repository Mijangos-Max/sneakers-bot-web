import os
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from google.cloud import dialogflow_v2 as dialogflow
from motor.motor_asyncio import AsyncIOMotorClient

# ==========================================
# CONFIGURACIÓN
# ==========================================
TELEGRAM_TOKEN = "8651294518:AAFyQI5k8p4b191QU8FSaAAIDmHb4qTJsOM"
DIALOGFLOW_PROJECT_ID = "sneakersbotmx-voco"  # El ID de tu agente de Dialogflow

# Enlace de conexión real a tu propia base de datos de MongoDB Atlas
MONGO_URI = "mongodb+srv://josemanueldominguez875_db_user:9KTzR7KPJGgTTzBd@cluster0.lkq7koy.mongodb.net/?appName=Cluster0"

# Inicialización de MongoDB
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["sneakers_bot_db"]
carrito_collection = db["carritos"]


# Menú de botones en Telegram
def menu_principal():
    return ReplyKeyboardMarkup(
        [["Ver tenis", "Ver playeras"], ["Mi Carrito", "Ayuda"]], resize_keyboard=True
    )


# Función que conecta con la API de Dialogflow
def detectar_intencion(session_id, text, language_code="es"):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(DIALOGFLOW_PROJECT_ID, str(session_id))
    
    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)
    
    response = session_client.detect_intent(request={"session": session, "query_input": query_input})
    return response.query_result


# Catálogo de Productos
catalogo = {
    "tenis": [
        {"nombre": "Nike Air Max", "precio": "$1,999", "tallas": ["25", "26", "27", "28"], "colores": ["Negro", "Blanco", "Rojo"]},
        {"nombre": "Adidas Ultraboost", "precio": "$2,299", "tallas": ["26", "27", "28"], "colores": ["Negro", "Gris"]}
    ],
    "playeras": [
        {"nombre": "Playera Nike", "precio": "$299", "tallas": ["CH", "M", "G"], "colores": ["Blanco", "Negro"]},
        {"nombre": "Playera Adidas", "precio": "$349", "tallas": ["M", "G"], "colores": ["Rojo", "Azul"]}
    ]
}


# Genera respuestas para el catálogo
def obtener_texto_catalogo(tipo):
    productos = catalogo.get(tipo, [])
    
    if tipo == "tenis":
        frases_introduccion = [
            "¡Claro que sí! Con gusto te muestro los modelos de tenis que tenemos disponibles ahorita en tienda. Échales un ojo: 🔥\n\n",
            "¡Excelente elección! Aquí tienes nuestro catálogo actual de tenis con sus tallas y colores en existencia: 👟\n\n",
            "Por supuesto, aquí te dejo los tenis que tenemos listos para envío inmediato. Dime cuál te gusta: 👇\n\n"
        ]
    else:
        frases_introduccion = [
            "¡Claro! Te comparto las playeras que tenemos en stock justo ahora: 👕\n\n",
            "¡Excelente! Aquí tienes los modelos de playeras disponibles con sus tallas: 👇\n\n",
            "¡Por supuesto! Mira las playeras que nos acaban de llegar a tienda: 🔥\n\n"
        ]
    
    texto = random.choice(frases_introduccion)
    
    for p in productos:
        texto += f"⭐ *{p['nombre']}*\n   Precio: {p['precio']}\n   Tallas: {', '.join(p['tallas'])}\n   Colores: {', '.join(p['colores'])}\n\n"
    
    texto += "Si te interesa alguno, solo dime completo: *'Quiero agregar los Nike Air Max en talla 27 color Negro'* o como gustes."
    return texto


# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Bienvenido a SneakersBot MX! 👟\n¿En qué te puedo ayudar hoy?",
        reply_markup=menu_principal(),
    )


# Manejador de mensajes e Inteligencia Artificial
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    texto_usuario = update.message.text
    texto_limpio = texto_usuario.strip().lower()

    # =====================================================================
    # INTERCEPCIÓN EN PYTHON: Evita que Dialogflow confunda botones y saludos
    # =====================================================================
    saludos = ["hola", "hola!", "buen dia", "buenas noches", "buenas tardes", "que tal"]
    if any(saludo in texto_limpio for saludo in saludos):
        await update.message.reply_text(
            "¡Hola! Buenas noches. 😊 ¿En qué te puedo colaborar hoy? Puedes revisar nuestro catálogo usando los botones de abajo o pedirme un modelo directamente.",
            reply_markup=menu_principal()
        )
        return

    elif texto_limpio == "mi carrito":
        try:
            carrito = await carrito_collection.find_one({"user_id": user_id})
            if carrito and carrito.get("items"):
                texto_carrito = "🛒 *Tu Carrito Actual:*\n\n"
                for idx, item in enumerate(carrito["items"], 1):
                    texto_carrito += f"{idx}. *{item['producto']}* - Talla {item['talla']} ({item['color']})\n"
                await update.message.reply_text(texto_carrito, parse_mode="Markdown")
            else:
                await update.message.reply_text("Tu carrito está vacío todavía. ¡Échale un ojo al catálogo para agregar algo!")
        except Exception as mongo_err:
            print(f"Error al leer de MongoDB: {mongo_err}")
            await update.message.reply_text("No pude consultar tu carrito en este momento.")
        return

    elif texto_limpio == "ayuda":
        await update.message.reply_text(
            "Puedes usar los botones de abajo para ver la mercancía disponible o escribir directamente cosas como: *'Quiero ver tenis'* o *'Quiero añadir unas playeras al carrito'*.",
            parse_mode="Markdown"
        )
        return

    # =====================================================================
    # PROCESAMIENTO CON DIALOGFLOW (Para intenciones complejas)
    # =====================================================================
    try:
        query_result = detectar_intencion(user_id, texto_usuario)
        intent_name = query_result.intent.display_name
        respuesta_dialogflow = query_result.fulfillment_text
    except Exception as e:
        print(f"Error con Dialogflow: {e}")
        await update.message.reply_text("Ups, tuve un problema al conectarme con mi cerebro de IA. Intenta de nuevo.")
        return

    # 1. Intención: Ver catálogo
    if intent_name == "Ver_Catalogo":
        tipo_producto = query_result.parameters.get("tipo_producto", "").lower()
        
        if not tipo_producto:
            if "tenis" in texto_usuario.lower():
                tipo_producto = "tenis"
            elif "playera" in texto_usuario.lower():
                tipo_producto = "playeras"

        if tipo_producto in catalogo:
            await update.message.reply_text(obtener_texto_catalogo(tipo_producto), parse_mode="Markdown")
        else:
            await update.message.reply_text("Por ahora solo tengo disponibles 'tenis' y 'playeras'.")

    # 2. Intención: Agregar productos al Carrito (Guarda en MongoDB Atlas)
    elif intent_name == "Agregar_Carrito":
        producto = query_result.parameters.get("producto")
        talla = query_result.parameters.get("talla")
        color = query_result.parameters.get("color")

        if producto and talla and color:
            item_carrito = {"producto": producto, "talla": talla, "color": color}
            
            try:
                await carrito_collection.update_one(
                    {"user_id": user_id},
                    {"$push": {"items": item_carrito}},
                    upsert=True
                )
                await update.message.reply_text(
                    f"🛒 *¡Añadido al carrito con éxito!*\n\n• *Producto:* {producto}\n• *Talla:* {talla}\n• *Color:* {color}\n\nEscribe *'Mi Carrito'* para ver tu lista completa.",
                    parse_mode="Markdown"
                )
            except Exception as mongo_err:
                print(f"Error al guardar en MongoDB: {mongo_err}")
                await update.message.reply_text("Hubo un problema al guardar el producto en tu carrito en la nube.")
        else:
            if respuesta_dialogflow:
                await update.message.reply_text(respuesta_dialogflow)
            else:
                await update.message.reply_text("Faltan datos del producto (talla, color o modelo). ¿Me los puedes detallar?")

    # 3. Respuesta fallback o por defecto de Dialogflow
    else:
        if respuesta_dialogflow:
            await update.message.reply_text(respuesta_dialogflow, reply_markup=menu_principal())
        else:
            print(f"⚠️ Alerta: Dialogflow detectó el intent '{intent_name}' pero la respuesta de texto está vacía.")
            await update.message.reply_text("¡Hola! Recibí tu mensaje, pero aún sigo aprendiendo a responder esto. ¿Te puedo ayudar con el catálogo o el carrito?", reply_markup=menu_principal())


# Arranque del Servidor
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("Bot con Dialogflow y MongoDB Atlas funcionando correctamente...")
    app.run_polling()