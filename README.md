# Alquimia Nous — Servidor

## Variables de entorno en Render

MP_ACCESS_TOKEN   → Access Token de MercadoPago (APP_USR-...)
MP_PUBLIC_KEY     → Public Key de MercadoPago (APP_USR-...)
DEEPSEEK_API_KEY  → tu key de DeepSeek (sk-...)
ADMIN_KEY         → clave que vos inventás
EMAIL_FROM        → alquimianous.creaciones@gmail.com
EMAIL_PASSWORD    → contraseña de aplicación de Gmail (ver abajo)
URL_SITIO         → https://tusitio.vercel.app
URL_SERVIDOR      → https://tuservidor.onrender.com

## Contraseña de aplicación Gmail
1. Entrás a myaccount.google.com
2. Seguridad → Verificación en 2 pasos (activar)
3. Seguridad → Contraseñas de aplicaciones
4. Generás una para "Correo"
5. Esa clave de 16 caracteres va en EMAIL_PASSWORD

## Start command
gunicorn server:app

## Endpoints
GET  /                           → verifica que funciona
POST /chat                       → chat IA (DeepSeek)
POST /crear_pago                 → crea link MercadoPago
POST /webhook/mp                 → webhook de MercadoPago
POST /verificar                  → verifica token
POST /admin/token_manual         → genera token a mano
GET  /admin/tokens?clave=X       → lista todos los tokens

## Webhook en MercadoPago
En mercadopago.com/developers → tu app → Webhooks:
URL: https://TUSERVIDOR.onrender.com/webhook/mp
Eventos: Pagos
