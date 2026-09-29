---
title: Almacen Mator
sdk: streamlit
sdk_version: 1.49.0
app_file: app.py
python_version: 3.11
pinned: false
---

# Almacen Mator

Aplicacion Streamlit para gestionar albaranes, equipos y reparaciones.

## Keepalive de Render

El workflow `.github/workflows/render-keepalive.yml` consulta Render cada 5 minutos.
Para activarlo, configura el secreto `RENDER_APP_URL` en GitHub con la URL publica
completa del servicio, por ejemplo `https://tu-servicio.onrender.com`.

## Persistencia

Este Space necesita almacenamiento persistente para conservar la base SQLite, las fotos de preparacion y los archivos generados en `data/`. Sin almacenamiento persistente, esos datos pueden perderse cuando el Space se reinicia.
