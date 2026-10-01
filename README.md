# Almacen Mator

Aplicacion Streamlit para gestionar albaranes, equipos y el almacen virtual.

## Almacen virtual

El almacen virtual permite alternar entre Nave 1 y Nave 2. En la primera
inicializacion de esta version, se vacian una sola vez las secciones, ubicaciones,
existencias y movimientos de Nave 1 para empezar desde cero; Nave 2 y los
albaranes no se modifican. Ambas naves empiezan sin secciones y se configuran de
forma independiente. Cada seccion tiene una sola ubicacion y se define por su
capacidad total en palets. En la pestaña Traslados se puede mover material entre
ubicaciones de ambas naves; el traslado actualiza las dos existencias en una sola
transaccion y registra su salida y recepcion en el historial.

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
