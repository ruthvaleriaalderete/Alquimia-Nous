"""
╔══════════════════════════════════════════════════════╗
║   ALQUIMIA NOUS — Servidor completo                  ║
║   MercadoPago + DeepSeek + Tokens 90 días + Email    ║
║   Start command: gunicorn server:app                 ║
║                                                      ║
║   Variables de entorno en Render:                    ║
║   MP_ACCESS_TOKEN  → Access Token de MercadoPago     ║
║   MP_PUBLIC_KEY    → Public Key de MercadoPago       ║
║   DEEPSEEK_API_KEY → tu key de DeepSeek              ║
║   ADMIN_KEY        → clave que vos inventás          ║
║   EMAIL_FROM       → tu email Gmail                  ║
║   EMAIL_PASSWORD   → contraseña de aplicación Gmail  ║
║   URL_SITIO        → URL de tu sitio en Vercel       ║
╚══════════════════════════════════════════════════════╝
"""

import os
import json
import uuid
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
from flask_cors import CORS
import mercadopago

app = Flask(__name__)
CORS(app)

# ── Configuración ─────────────────────────────────────
DB_FILE          = "tokens.json"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_URL     = "https://api.deepseek.com/chat/completions"
MP_ACCESS_TOKEN  = os.environ.get("MP_ACCESS_TOKEN")
MP_PUBLIC_KEY    = os.environ.get("MP_PUBLIC_KEY")
EMAIL_FROM       = os.environ.get("EMAIL_FROM", "alquimianous.creaciones@gmail.com")
EMAIL_PASSWORD   = os.environ.get("EMAIL_PASSWORD")
URL_SITIO        = os.environ.get("URL_SITIO", "https://tusitio.com")
URL_SERVIDOR     = os.environ.get("URL_SERVIDOR", "https://tuservidor.onrender.com")
PRECIO           = 7000
DIAS_ACCESO      = 90

CONTEXTO_PRODUCTO = """
Sos el asistente virtual de Alquimia Nous.
Respondés preguntas sobre el primer volumen: el origen del universo.

SOBRE EL PRODUCTO:
- Sitio web interactivo de divulgación científica
- El tema central es el origen de todo: el Big Bang, el espacio,
  cómo se formaron las estrellas y los planetas, y cómo nosotros
  somos parte de esa historia
- Introducción clara con ejemplos concretos para que cualquier persona entienda
- Videos de divulgadores reconocidos en ciencias
- No hay un camino preestablecido: quien entra va a donde le interesa
  y sigue hacia donde su curiosidad le indica
- Textos con profundidad real, sin subestimar al lector
- En cada página hay una IA disponible para consultar cualquier duda
- Música de fondo suave y diseño inmersivo con video espacial

PARA QUIÉN ES:
- Para cualquier persona con curiosidad, sin importar la edad
- Nació para hacer el tema interesante incluso para niños pequeños,
  sin perder profundidad
- Lo ideal es recorrerlo en familia
- No hace falta saber nada previo

LA FILOSOFÍA:
- Nació de la pregunta de un nene de 5 años: "¿Cómo empezó todo, mamá?"
- No es un colegio. Es aprender en libertad.
- Sabemos dónde empieza la curiosidad, pero no a dónde nos puede llevar
- Sin subestimar a los peques. Sin exigir a los papás.
- Los adultos no estamos terminados de hacer. Seguimos construyendo.

ACCESO:
- Precio de lanzamiento: $7.000 ARS
- Acceso por 3 meses desde la compra
- Funciona en celular, tablet y computadora
- Una compra para toda la familia

TONO:
- Cálido, cercano, breve, en español rioplatense
- Nunca preguntes la edad
- Nunca inventés información
- Si preguntan precio exacto: $7.000 ARS, acceso 3 meses
"""

# ══════════════════════════════════════════════════════
# BASE DE DATOS
# ══════════════════════════════════════════════════════

def cargar_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE) as f:
        return json.load(f)

def guardar_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def generar_token():
    return str(uuid.uuid4()).replace("-", "").upper()[:12]

def token_expirado(entry):
    if not entry.get("fecha_vencimiento"):
        return False
    vencimiento = datetime.fromisoformat(entry["fecha_vencimiento"])
    return datetime.now() > vencimiento

# ══════════════════════════════════════════════════════
# EMAIL
# ══════════════════════════════════════════════════════

def enviar_email(destinatario, token, dias_restantes=90):
    if not EMAIL_PASSWORD:
        print(f"⚠️ Sin EMAIL_PASSWORD — token generado: {token} para {destinatario}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "✨ Tu acceso a Exploremos Juntos — Alquimia Nous"
        msg["From"]    = EMAIL_FROM
        msg["To"]      = destinatario

        html = f"""
        <div style="font-family:Arial,sans-serif; max-width:500px; margin:0 auto; padding:20px;">
          <h1 style="color:#0de41f; text-align:center;">✨ Exploremos Juntos</h1>
          <p style="color:#333;">¡Gracias por tu compra! 🎉</p>
          <p style="color:#333;">Tu código de acceso es:</p>
          <div style="background:#0d0d1a; border:2px solid #FFD700; border-radius:12px;
                      padding:20px; text-align:center; margin:20px 0;">
            <span style="font-size:2rem; font-weight:bold; color:#FFD700;
                         letter-spacing:4px;">{token}</span>
          </div>
          <p style="color:#333;">
            Ingresá con este código en:<br>
            <a href="{URL_SITIO}" style="color:#00D4FF;">{URL_SITIO}</a>
          </p>
          <p style="color:#666; font-size:0.85rem;">
            Tu acceso es válido por <strong>{dias_restantes} días</strong>
            desde hoy. Guardá este código.
          </p>
          <hr style="border:1px solid #eee; margin:20px 0;">
          <p style="color:#999; font-size:0.8rem; text-align:center;">
            Alquimia Nous — alquimianous.creaciones@gmail.com
          </p>
        </div>
        """

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, destinatario, msg.as_string())

        print(f"✅ Email enviado a {destinatario}")
        return True

    except Exception as e:
        print(f"❌ Error email: {e}")
        return False

# ══════════════════════════════════════════════════════
# DEEPSEEK
# ══════════════════════════════════════════════════════

def llamar_deepseek(historial, sistema=None):
    if sistema is None:
        sistema = CONTEXTO_PRODUCTO
    headers  = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type" : "application/json"
    }
    mensajes = [{"role": "system", "content": sistema}] + historial[-10:]
    body     = {
        "model"      : "deepseek-chat",
        "messages"   : mensajes,
        "max_tokens" : 600,
        "temperature": 0.7
    }
    res = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=30)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

# ══════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════

@app.route("/", methods=["GET"])
def home():
    return jsonify({"estado": "Alquimia Nous API — funcionando ✓"}), 200


@app.route("/chat", methods=["POST"])
def chat():
    data      = request.json or {}
    historial = data.get("historial", [])
    sistema   = data.get("sistema", None)
    if not historial:
        return jsonify({"error": "sin mensajes"}), 400
    try:
        respuesta = llamar_deepseek(historial, sistema)
        return jsonify({"respuesta": respuesta}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/crear_pago", methods=["POST"])
def crear_pago():
    """Crea un link de pago en MercadoPago y lo devuelve."""
    data  = request.json or {}
    email = data.get("email", "")

    sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

    preference = {
        "items": [{
            "title"     : "Exploremos Juntos — Vol.1 El Universo",
            "quantity"  : 1,
            "unit_price": float(PRECIO),
            "currency_id": "ARS"
        }],
        "payer": { "email": email },
        "external_reference": email,
        "back_urls": {
            "success": f"{URL_SITIO}?pago=ok",
            "failure": f"{URL_SITIO}?pago=error",
            "pending": f"{URL_SITIO}?pago=pendiente"
        },
        "auto_return"      : "approved",
        "notification_url" : f"{URL_SERVIDOR}/webhook/mp"
    }

    result = sdk.preference().create(preference)
    if result["status"] == 201:
        return jsonify({
            "link": result["response"]["init_point"],
            "ok"  : True
        }), 200
    else:
        return jsonify({"error": "no se pudo crear el link"}), 500


@app.route("/webhook/mp", methods=["POST"])
def webhook_mp():
    """MercadoPago llama aquí cuando se confirma un pago."""
    data = request.json or {}

    if data.get("type") != "payment":
        return jsonify({"ok": True}), 200

    payment_id = data["data"]["id"]
    sdk  = mercadopago.SDK(MP_ACCESS_TOKEN)
    pago = sdk.payment().get(payment_id)

    if pago["status"] != 200:
        return jsonify({"error": "no se pudo verificar"}), 400

    info = pago["response"]
    if info["status"] != "approved":
        return jsonify({"ok": True}), 200

    email = info.get("external_reference") or \
            info.get("payer", {}).get("email", "")

    if not email:
        return jsonify({"error": "sin email"}), 400

    # Verificar si ya tiene acceso activo
    db = cargar_db()
    for entry in db.values():
        if entry.get("email") == email and not token_expirado(entry):
            enviar_email(email, entry["token"])
            return jsonify({"ok": True}), 200

    # Generar token nuevo con vencimiento
    token      = generar_token()
    vencimiento = datetime.now() + timedelta(days=DIAS_ACCESO)

    db[token] = {
        "token"            : token,
        "email"            : email,
        "fecha"            : datetime.now().isoformat(),
        "fecha_vencimiento": vencimiento.isoformat(),
        "payment_id"       : str(payment_id),
        "activo"           : True
    }
    guardar_db(db)

    enviar_email(email, token, DIAS_ACCESO)
    return jsonify({"ok": True}), 200


@app.route("/verificar", methods=["POST"])
def verificar():
    """Verifica si un token es válido y no expiró."""
    token = (request.json or {}).get("token", "").strip().upper()
    db    = cargar_db()

    if token not in db:
        return jsonify({"valido": False, "motivo": "no existe"}), 200

    entry = db[token]

    if not entry.get("activo"):
        return jsonify({"valido": False, "motivo": "inactivo"}), 200

    if token_expirado(entry):
        return jsonify({"valido": False, "motivo": "expirado"}), 200

    # Calcular días restantes
    vencimiento   = datetime.fromisoformat(entry["fecha_vencimiento"])
    dias_restantes = (vencimiento - datetime.now()).days

    return jsonify({
        "valido"        : True,
        "dias_restantes": dias_restantes
    }), 200


@app.route("/admin/token_manual", methods=["POST"])
def token_manual():
    """Genera un token a mano — para pruebas o regalos."""
    data = request.json or {}
    if data.get("clave") != os.environ.get("ADMIN_KEY", ""):
        return jsonify({"error": "no autorizado"}), 401

    email      = data.get("email", "manual")
    dias       = int(data.get("dias", DIAS_ACCESO))
    token      = generar_token()
    vencimiento = datetime.now() + timedelta(days=dias)
    db         = cargar_db()

    db[token] = {
        "token"            : token,
        "email"            : email,
        "fecha"            : datetime.now().isoformat(),
        "fecha_vencimiento": vencimiento.isoformat(),
        "payment_id"       : "manual",
        "activo"           : True
    }
    guardar_db(db)

    if email != "manual" and "@" in email:
        enviar_email(email, token, dias)

    return jsonify({"token": token, "ok": True, "vence": vencimiento.isoformat()}), 200


@app.route("/admin/tokens", methods=["GET"])
def listar_tokens():
    if request.args.get("clave") != os.environ.get("ADMIN_KEY", ""):
        return jsonify({"error": "no autorizado"}), 401
    db = cargar_db()
    # Agrega estado de expiración a cada token
    for token, entry in db.items():
        entry["expirado"] = token_expirado(entry)
    return jsonify({"total": len(db), "tokens": list(db.values())}), 200


if __name__ == "__main__":
    print("🚀 Alquimia Nous — servidor iniciado")
    app.run(host="0.0.0.0", port=5000, debug=False)
