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

## Albaranes y existencias

Al crear un albaran, la pantalla y el Excel muestran las ubicaciones actuales
del material como referencia. Las existencias se descuentan al marcar el
albaran como Procesando, no al crearlo. El descuento solo se aplica a las lineas
con stock suficiente; las lineas insuficientes se dejan intactas y se indican
en las observaciones. En Procesando se pueden consultar las ubicaciones de las
que se descontaron las unidades. Al cumplir 24 horas en Procesando, los
albaranes se marcan automaticamente como finalizados y sus lineas se guardan en
el historial de finalizados que alimenta los reportes. Los albaranes que ya
estaban en Procesando al desplegar esta mejora empiezan su primer conteo de
24 horas desde la migracion, porque no existia una fecha de procesamiento previa.
Los albaranes ya completados tambien se pueden finalizar manualmente, en grupo,
desde la lista de Procesando, sin esperar las 24 horas.

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
El ping reintenta errores de red y tiempos de espera para dar margen a los
arranques en frio. GitHub Actions puede retrasar las ejecuciones programadas,
por lo que esto no garantiza que un servicio gratuito permanezca siempre activo.

## Plano del almacen

La primera pestana de Almacen Virtual muestra unicamente el plano interactivo
de Nave 1. Los
nombres de las secciones deben coincidir con las etiquetas del plano en
`assets/mapa_nave1.xlsx`. El color identifica la misma familia de seccion que en
la leyenda del mapa; cada plaza ocupada se rellena y las libres quedan en blanco. Al
hacer clic en una ubicacion se puede consultar su ocupacion, porcentaje y
materiales registrados.
