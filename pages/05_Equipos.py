import io
import io
import re
import unicodedata
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from utils.branding import mostrar_logo
from utils.db import get_conn, init_db

PASSWORDS_EQUIPOS = {"ju@n", "t@ny"}
EQUIPO_COLUMNS = ["nombre", "cantidad", "numero_serie", "seccion"]

st.set_page_config(page_title="Equipos - Almacén Mator", layout="wide")
mostrar_logo()
init_db()

if not st.session_state.get("equipos_autorizado"):
    st.title("Equipos")
    st.info("Introduce la contraseña para acceder a esta sección.")
    password = st.text_input("Contraseña", type="password")
    if password:
        if password in PASSWORDS_EQUIPOS:
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
st.caption("Puedes escribir el número de serie, usar la cámara o abrir un lector externo.")


def decodificar_codigo(imagen):
    import zxingcpp
    from PIL import Image, ImageEnhance, ImageOps

    imagen_pil = Image.open(imagen).convert("RGB")
    if max(imagen_pil.size) < 1600:
        escala = 1600 / max(imagen_pil.size)
        imagen_pil = imagen_pil.resize(
            (int(imagen_pil.width * escala), int(imagen_pil.height * escala))
        )

    imagenes = [imagen_pil, ImageOps.grayscale(imagen_pil)]
    imagenes.append(ImageEnhance.Contrast(imagenes[-1]).enhance(2.0))
    resultados = []
    for imagen_preparada in imagenes:
        matriz = np.array(imagen_preparada)
        for giro in range(4):
            matriz_girada = np.rot90(matriz, giro)
            resultados.extend(zxingcpp.read_barcodes(matriz_girada))
    return next((codigo.text for codigo in resultados if codigo.text.strip()), "")

numero_serie_camara = ""
captura = st.camera_input("Leer código de barras", key="camara_codigo_barras")
if captura is not None:
    try:
        numero_serie_camara = decodificar_codigo(captura)
        if numero_serie_camara:
            st.success(f"Código leído: {numero_serie_camara}")
        else:
            st.warning("No se ha detectado ningún código de barras en la imagen.")
    except ImportError:
        st.error("La lectura de códigos no está disponible en este despliegue.")

st.markdown(
    "<a href='intent://scan/#Intent;scheme=zxing;end' target='_blank'>"
    "Abrir lector de códigos externo (Android)</a>",
    unsafe_allow_html=True,
)
numero_serie_externo = st.text_input(
    "Código leído con otra aplicación (opcional)",
    key="codigo_externo",
)
numero_serie_detectado = numero_serie_externo.strip() or numero_serie_camara

with st.form("formulario_equipo", clear_on_submit=True):
    nombre = st.text_input("Nombre")
    cantidad = st.number_input("Cantidad", min_value=1, step=1, value=1)
    numero_serie = st.text_input("Número de serie", value=numero_serie_detectado)
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
    valor = unicodedata.normalize("NFKD", str(valor).strip().lower())
    valor = "".join(caracter for caracter in valor if not unicodedata.combining(caracter))
    return re.sub(r"[^a-z0-9]", "", valor)


def limpiar_cantidad(valor):
    if pd.isna(valor):
        return 0

    texto = str(valor).strip().lower()
    if texto == "":
        return 0

    palabras = {
        "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
        "diez": 10,
    }
    if texto in palabras:
        return palabras[texto]

    numeros = re.findall(r"\d+", texto)
    return int(numeros[0]) if numeros else 0


def leer_csv_universal(archivo, header=0):
    contenido = archivo.getvalue()
    ultimo_error = None
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(
                io.BytesIO(contenido),
                sep=None,
                engine="python",
                encoding=encoding,
                header=header,
            )
        except (UnicodeDecodeError, pd.errors.ParserError) as error:
            ultimo_error = error
    raise ValueError(f"No se pudo leer el CSV: {ultimo_error}")


def preparar_importacion(archivo):
    nombre_archivo = archivo.name.lower()
    if nombre_archivo.endswith(".csv"):
        datos = leer_csv_universal(archivo)
    elif nombre_archivo.endswith(".xls"):
        datos = pd.read_excel(archivo, engine="xlrd")
    else:
        datos = pd.read_excel(archivo, engine="openpyxl")

    columnas = {normalizar_columna(columna): columna for columna in datos.columns}
    alias = {
        "nombre": ("nombre", "producto", "material", "equipo", "descripcion"),
        "cantidad": ("cantidad", "unidades", "unidad", "cantidadtotal", "qty"),
        "numero_serie": ("numerodeserie", "numeroserie", "serie", "serial", "serialnumber"),
        "seccion": ("seccion", "area", "departamento", "ubicacion", "ubicación"),
    }

    resultado = pd.DataFrame()
    columnas_encontradas = {}
    for destino, posibles in alias.items():
        columna = next((columnas[posible] for posible in posibles if posible in columnas), None)
        if columna is not None:
            columnas_encontradas[destino] = columna

    if len(columnas_encontradas) == 0 and nombre_archivo.endswith(".csv"):
        datos = leer_csv_universal(archivo, header=None)
        datos = datos.iloc[:, :4].copy()
        datos.columns = list(alias)
        resultado = datos
    elif len(columnas_encontradas) < len(alias):
        if len(datos.columns) < 4:
            faltantes = [destino for destino in alias if destino not in columnas_encontradas]
            raise ValueError("El archivo necesita al menos cuatro columnas: " + ", ".join(faltantes))
        datos = datos.iloc[:, :4].copy()
        datos.columns = list(alias)
        resultado = datos
    else:
        for destino, columna in columnas_encontradas.items():
            resultado[destino] = datos[columna]

    resultado["cantidad"] = resultado["cantidad"].apply(limpiar_cantidad).astype("Int64")
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
    except (ImportError, ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
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
