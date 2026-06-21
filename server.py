"""
╔══════════════════════════════════════════════════════╗
║   ALQUIMIA NOUS — Servidor principal                 ║
║   MercadoPago + DeepSeek + Tokens 90 días + Email    ║
║   Start command: gunicorn server:app                 ╚══════════════════════════════════════════════════════╝
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

# CORS — permite llamadas desde Cloudflare Pages, Netlify (legado) y entornos locales de prueba
CORS(app, resources={r"/*": {"origins": [
    "https://exploremos-juntos-alquimia-nous.ruthvaleriaal.workers.dev",
    "https://exploremos-juntos.netlify.app",
    "http://localhost",
    "http://127.0.0.1"
]}}, supports_credentials=False)

DB_FILE          = "tokens.json"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_URL     = "https://api.deepseek.com/chat/completions"
MP_ACCESS_TOKEN  = os.environ.get("MP_ACCESS_TOKEN")
EMAIL_FROM       = os.environ.get("EMAIL_FROM", "alquimianous.creaciones@gmail.com")
EMAIL_PASSWORD   = os.environ.get("EMAIL_PASSWORD")
URL_SITIO        = os.environ.get("URL_SITIO", "https://exploremos-juntos-alquimia-nous.ruthvaleriaal.workers.dev")
URL_SERVIDOR     = os.environ.get("URL_SERVIDOR", "https://alquimia-nous.onrender.com")
PRECIO           = 7000
DIAS_ACCESO      = 90

CONTEXTO_PRODUCTO = """
Sos el asistente virtual de Alquimia Nous.
Respondés preguntas sobre el primer volumen: el origen del universo.
Tono cálido, profundo, en español rioplatense. Sin tecnicismos innecesarios.
Nunca subestimás al que pregunta. Podés hacer preguntas de vuelta.
"""

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
    return datetime.now() > datetime.fromisoformat(entry["fecha_vencimiento"])

def enviar_email(destinatario, token, dias=90):
    if not EMAIL_PASSWORD:
        print(f"Token generado: {token} para {destinatario}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "✨ Tu acceso a Exploremos Juntos — Alquimia Nous"
        msg["From"]    = EMAIL_FROM
        msg["To"]      = destinatario
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px;">
          <h1 style="color:#0de41f;text-align:center;">✨ Exploremos Juntos</h1>
          <p>¡Gracias por tu compra! 🎉</p>
          <p>Tu código de acceso es:</p>
          <div style="background:#0d0d1a;border:2px solid #FFD700;border-radius:12px;
                      padding:20px;text-align:center;margin:20px 0;">
            <span style="font-size:2rem;font-weight:bold;color:#FFD700;letter-spacing:4px;">{token}</span>
          </div>
          <p>Ingresá en: <a href="{URL_SITIO}">{URL_SITIO}</a></p>
          <p style="color:#666;font-size:0.85rem;">Acceso válido por <strong>{dias} días</strong>.</p>
        </div>
        """
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, destinatario, msg.as_string())
        return True
    except Exception as e:
        print(f"Error email: {e}")
        return False

def llamar_deepseek(historial, sistema=None):
    if sistema is None:
        sistema = CONTEXTO_PRODUCTO
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    mensajes = [{"role": "system", "content": sistema}] + historial[-10:]
    body = {
        "model": "deepseek-chat",
        "messages": mensajes,
        "max_tokens": 600,
        "temperature": 0.7
    }
    res = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=30)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

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
    data  = request.json or {}
    email = data.get("email", "")
    sdk   = mercadopago.SDK(MP_ACCESS_TOKEN)
    preference = {
        "items": [{
            "title"      : "Exploremos Juntos — Vol.1 El Universo",
            "quantity"   : 1,
            "unit_price" : float(PRECIO),
            "currency_id": "ARS"
        }],
        "payer"             : {"email": email},
        "external_reference": email,
        "back_urls"         : {
            "success": f"{URL_SITIO}?pago=ok",
            "failure": f"{URL_SITIO}?pago=error",
            "pending": f"{URL_SITIO}?pago=pendiente"
        },
        "auto_return"      : "approved",
        "notification_url" : f"{URL_SERVIDOR}/webhook/mp"
    }
    result = sdk.preference().create(preference)
    if result["status"] == 201:
        return jsonify({"link": result["response"]["init_point"], "ok": True}), 200
    return jsonify({"error": "no se pudo crear el link"}), 500

@app.route("/webhook/mp", methods=["POST"])
def webhook_mp():
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
    email = info.get("external_reference") or info.get("payer", {}).get("email", "")
    if not email:
        return jsonify({"error": "sin email"}), 400
    db = cargar_db()
    for entry in db.values():
        if entry.get("email") == email and not token_expirado(entry):
            enviar_email(email, entry["token"])
            return jsonify({"ok": True}), 200
    token       = generar_token()
    vencimiento = datetime.now() + timedelta(days=DIAS_ACCESO)
    db[token]   = {
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
    token = (request.json or {}).get("token", "").strip().upper()
    db    = cargar_db()
    if token not in db:
        return jsonify({"valido": False}), 200
    entry  = db[token]
    valido = entry.get("activo") and not token_expirado(entry)
    dias   = 0
    if valido and entry.get("fecha_vencimiento"):
        dias = (datetime.fromisoformat(entry["fecha_vencimiento"]) - datetime.now()).days
    return jsonify({"valido": valido, "dias_restantes": dias}), 200

@app.route("/admin/token_manual", methods=["POST"])
def token_manual():
    data = request.json or {}
    if data.get("clave") != os.environ.get("ADMIN_KEY", ""):
        return jsonify({"error": "no autorizado"}), 401
    email       = data.get("email", "manual")
    dias        = int(data.get("dias", DIAS_ACCESO))
    token       = generar_token()
    vencimiento = datetime.now() + timedelta(days=dias)
    db          = cargar_db()
    db[token]   = {
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
    return jsonify({"token": token, "ok": True}), 200

@app.route("/admin/tokens", methods=["GET"])
def listar_tokens():
    if request.args.get("clave") != os.environ.get("ADMIN_KEY", ""):
        return jsonify({"error": "no autorizado"}), 401
    db = cargar_db()
    for entry in db.values():
        entry["expirado"] = token_expirado(entry)
    return jsonify({"total": len(db), "tokens": list(db.values())}), 200

if __name__ == "__main__":
    print("🚀 Alquimia Nous — servidor iniciado")
    app.run(host="0.0.0.0", port=5000, debug=False)
