import re
from datetime import date

import pandas as pd
import streamlit as st

from utils.db import get_conn, init_db

PASSWORD_EQUIPOS = "ju@n"
EQUIPO_COLUMNS = ["nombre", "cantidad", "numero_serie", "seccion"]

st.set_page_config(page_title="Equipos - Almacén Mator", layout="wide")
init_db()

if not st.session_state.get("equipos_autorizado"):
    st.title("Equipos")
    st.info("Introduce la contraseña para acceder a esta sección.")
    password = st.text_input("Contraseña", type="password")
    if password:
        if password == PASSWORD_EQUIPOS:
            st.session_state.equipos_autorizado = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

st.title("Equipos")

if st.button("Cerrar sesión de Equipos"):
    st.session_state.equipos_autorizado = False
    st.rerun()

st.subheader("Añadir equipo")
st.caption("Puedes escribir el número de serie o leerlo con la cámara del móvil.")

numero_serie_camara = ""
captura = st.camera_input("Leer código de barras", key="camara_codigo_barras")
if captura is not None:
    try:
        import numpy as np
        import zxingcpp
        from PIL import Image

        imagen = np.array(Image.open(captura).convert("RGB"))
        codigos = zxingcpp.read_barcodes(imagen)
        if codigos:
            numero_serie_camara = codigos[0].text
            st.success(f"Código leído: {numero_serie_camara}")
        else:
            st.warning("No se ha detectado ningún código de barras en la imagen.")
    except ImportError:
        st.error("La lectura de códigos no está disponible en este despliegue.")

with st.form("formulario_equipo", clear_on_submit=True):
    nombre = st.text_input("Nombre")
    cantidad = st.number_input("Cantidad", min_value=1, step=1, value=1)
    numero_serie = st.text_input("Número de serie", value=numero_serie_camara)
    seccion = st.text_input("Sección")
    guardar_equipo = st.form_submit_button("Guardar equipo")

if guardar_equipo:
    if not all((nombre.strip(), numero_serie.strip(), seccion.strip())):
        st.error("Nombre, número de serie y sección son obligatorios.")
    else:
        conn = get_conn()
        conn.execute(
            "INSERT INTO equipos (nombre, cantidad, numero_serie, seccion, fecha_alta) VALUES (?, ?, ?, ?, ?)",
            (nombre.strip(), int(cantidad), numero_serie.strip(), seccion.strip(), date.today().isoformat()),
        )
        conn.commit()
        conn.close()
        st.success("Equipo guardado correctamente.")


def normalizar_columna(valor):
    valor = str(valor).strip().lower()
    return re.sub(r"[^a-z0-9]", "", valor.replace("ñ", "n"))


def preparar_importacion(archivo):
    nombre_archivo = archivo.name.lower()
    if nombre_archivo.endswith(".csv"):
        datos = pd.read_csv(archivo)
    else:
        datos = pd.read_excel(archivo)

    columnas = {normalizar_columna(columna): columna for columna in datos.columns}
    alias = {
        "nombre": ("nombre",),
        "cantidad": ("cantidad",),
        "numero_serie": ("numerodeserie", "numeroserie", "serie"),
        "seccion": ("seccion",),
    }
    faltantes = [
        destino
        for destino, posibles in alias.items()
        if not any(posible in columnas for posible in posibles)
    ]
    if faltantes:
        raise ValueError("Faltan columnas: " + ", ".join(faltantes))

    resultado = pd.DataFrame()
    for destino, posibles in alias.items():
        columna = next(columnas[posible] for posible in posibles if posible in columnas)
        resultado[destino] = datos[columna]

    resultado["cantidad"] = pd.to_numeric(resultado["cantidad"], errors="raise").astype(int)
    if (resultado["cantidad"] < 1).any():
        raise ValueError("La cantidad debe ser mayor que cero.")
    for columna in ("nombre", "numero_serie", "seccion"):
        resultado[columna] = resultado[columna].fillna("").astype(str).str.strip()
        if resultado[columna].eq("").any():
            raise ValueError(f"Hay valores vacíos en {columna}.")
    return resultado


st.subheader("Importar equipos")
archivo_importacion = st.file_uploader(
    "Selecciona un CSV o Excel",
    type=["csv", "xlsx", "xls"],
    key="importador_equipos",
)

if archivo_importacion is not None:
    try:
        equipos_importados = preparar_importacion(archivo_importacion)
        st.dataframe(equipos_importados, use_container_width=True)
        if st.button("Importar equipos", key="confirmar_importacion"):
            conn = get_conn()
            conn.executemany(
                "INSERT INTO equipos (nombre, cantidad, numero_serie, seccion, fecha_alta) VALUES (?, ?, ?, ?, ?)",
                [
                    (fila.nombre, int(fila.cantidad), fila.numero_serie, fila.seccion, date.today().isoformat())
                    for fila in equipos_importados.itertuples(index=False)
                ],
            )
            conn.commit()
            conn.close()
            st.success(f"Se han importado {len(equipos_importados)} equipos.")
    except (ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        st.error(f"No se pudo importar el archivo: {error}")


st.subheader("Equipos registrados")
conn = get_conn()
equipos = pd.read_sql_query(
    "SELECT id, nombre, cantidad, numero_serie, seccion, fecha_alta FROM equipos ORDER BY id DESC",
    conn,
)
conn.close()
if equipos.empty:
    st.info("Todavía no hay equipos registrados.")
else:
    st.dataframe(equipos, use_container_width=True, hide_index=True)
