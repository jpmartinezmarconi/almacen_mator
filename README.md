# Almacen Mator

Aplicacion Streamlit para gestionar albaranes, equipos y el almacen virtual.

## Almacen virtual

El almacen virtual permite alternar entre Nave 1 y Nave 2. Los datos actuales
de secciones, ubicaciones, existencias e historial se conservan en Nave 1; Nave 2
empieza sin secciones para que se configure de forma independiente. En la pestaña
Traslados se puede mover material entre ubicaciones de ambas naves. El traslado
actualiza las dos existencias en una sola transaccion y registra su salida y
recepcion en el historial.

## Despliegue en Render

El servicio se configura con `render.yaml`. En Render, define `DATABASE_URL` como
la URL de una base de datos PostgreSQL para conservar los datos entre reinicios.
Si no se configura, la aplicacion usa SQLite local, que no es persistente en el
disco efimero de un servicio Render.

Configura `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` solo si se usan las
notificaciones de Telegram.

## Keepalive

El workflow `.github/workflows/render-keepalive.yml` consulta Render cada cinco
minutos. Para activarlo, configura el secreto `RENDER_APP_URL` en GitHub con la
URL publica completa del servicio, por ejemplo `https://tu-servicio.onrender.com`.
