import html
import io
import json
import re
import tempfile

import streamlit as st
import streamlit.components.v1 as components

from utils.branding import mostrar_logo

st.set_page_config(page_title="Etiquetas - Almacén Mator", layout="wide")
mostrar_logo()


def parsear_dtl(contenido):
    elementos = []
    for numero_linea, linea in enumerate(contenido.splitlines(), start=1):
        linea = linea.strip()
        if not linea or linea.startswith(("#", ";")):
            continue
        coincidencia = re.match(
            r"^(TEXT|BARCODE)\s+(-?\d+)\s*,\s*(-?\d+)\s*,\s*[\"']?(.*?)[\"']?$",
            linea,
            re.IGNORECASE,
        )
        if coincidencia:
            tipo, x, y, valor = coincidencia.groups()
            elementos.append({"tipo": tipo.upper(), "x": int(x), "y": int(y), "valor": valor.strip()})
            continue
        if linea.upper().startswith("^FD"):
            valor = linea[3:].strip().strip('"')
            elementos.append({"tipo": "TEXT", "x": 30, "y": 30 + len(elementos) * 45, "valor": valor})
            continue
        raise ValueError(f"Línea {numero_linea} no reconocida: {linea}")
    return elementos


def parsear_zpl(contenido):
    elementos = []
    x_actual, y_actual = 30, 30
    codigo_de_barras = False
    tokens = re.finditer(r"\^FO(-?\d+),(-?\d+)|\^BC[^\^]*|\^FD(.*?)\^FS", contenido, re.IGNORECASE | re.DOTALL)
    for token in tokens:
        texto = token.group(0)
        if texto.upper().startswith("^FO"):
            x_actual, y_actual = int(token.group(1)), int(token.group(2))
        elif texto.upper().startswith("^BC"):
            codigo_de_barras = True
        elif token.group(3) is not None:
            elementos.append(
                {
                    "tipo": "BARCODE" if codigo_de_barras else "TEXT",
                    "x": x_actual,
                    "y": y_actual,
                    "valor": token.group(3).replace("\\,", ",").strip(),
                }
            )
            codigo_de_barras = False
    if not elementos:
        raise ValueError("No se encontraron campos de texto o código de barras")
    return elementos


def parsear_plantilla(contenido):
    if re.search(r"\^(?:XA|FO|BC|FD)", contenido, re.IGNORECASE):
        return parsear_zpl(contenido)
    return parsear_dtl(contenido)


def decodificar_plantilla(datos):
    if datos.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in datos:
        codificaciones = ("utf-16", "utf-16-le", "utf-16-be")
    else:
        codificaciones = ("utf-8-sig", "cp1252", "latin-1")
    for codificacion in codificaciones:
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    if b"\x00" in datos:
        raise ValueError("el archivo parece binario y no una plantilla de texto")
    raise ValueError("codificación de texto no compatible")


def nombre_sin_extension(nombre):
    return re.sub(r"\.[^.]+$", "", nombre)


def analizar_lab(datos):
    import olefile

    with olefile.OleFileIO(io.BytesIO(datos)) as archivo:
        objetos = archivo.openstream(["Objects"]).read()
        impresora = ""
        if archivo.exists("Printer"):
            impresora = archivo.openstream(["Printer"]).read().decode("utf-16le", errors="ignore")
        encontrados = []
        vistos = set()
        for coincidencia in re.finditer(rb"(?:[ -~\xA0-\xFF]\x00){4,}", objetos):
            texto = coincidencia.group().decode("utf-16le", errors="ignore").strip(" \x00")
            if texto and texto not in vistos and not re.fullmatch(r"[0-9]+", texto):
                vistos.add(texto)
                encontrados.append({"valor": texto, "indice": coincidencia.start()})
        return {"objetos": objetos, "impresora": impresora, "textos": encontrados}


def editar_lab(datos, textos, cambios):
    import olefile

    descriptor, ruta = tempfile.mkstemp(suffix=".Lab")
    try:
        with open(descriptor, "wb", closefd=True) as temporal:
            temporal.write(datos)
        with olefile.OleFileIO(ruta, write_mode=True) as archivo:
            objetos = bytearray(archivo.openstream(["Objects"]).read())
            for original, cambio in zip(textos, cambios):
                original_bytes = original["valor"].encode("utf-16le")
                cambio_bytes = cambio.encode("utf-16le")
                if len(cambio_bytes) > len(original_bytes):
                    raise ValueError(f"El texto '{original['valor']}' no puede superar {len(original['valor'])} caracteres.")
                inicio = original["indice"]
                reemplazo = cambio_bytes.ljust(len(original_bytes), b"\x00")
                objetos[inicio:inicio + len(original_bytes)] = reemplazo
            archivo.write_stream(["Objects"], bytes(objetos))
        with open(ruta, "rb") as temporal:
            return temporal.read()
    finally:
        try:
            import os
            os.unlink(ruta)
        except OSError:
            pass


def zpl_de_elementos(elementos, ancho, alto, oscuridad, velocidad):
    partes = ["^XA", f"^PW{ancho}", f"^LL{alto}", "^CI28", f"^MD{oscuridad}", f"^PR{velocidad}"]
    for elemento in elementos:
        x, y = max(0, int(elemento["x"])), max(0, int(elemento["y"]))
        seguro = str(elemento["valor"]).replace("^", " ").replace("\\", "\\\\")
        partes.append(f"^FO{x},{y}")
        if elemento["tipo"] == "BARCODE":
            partes.append(f"^BY2,3,70^BCN,70,Y,N,N^FD{seguro}^FS")
        else:
            partes.append(f"^A0N,30,30^FD{seguro}^FS")
    partes.append("^XZ")
    return "\n".join(partes)


def vista_etiqueta(elementos, ancho, alto):
    escala = min(520 / ancho, 260 / alto)
    contenido = []
    for elemento in elementos:
        x = int(elemento["x"]) * escala
        y = int(elemento["y"]) * escala
        valor = html.escape(str(elemento["valor"]))
        if elemento["tipo"] == "BARCODE":
            contenido.append(
                f'<div class="barcode" style="left:{x}px;top:{y}px">'
                f'<span class="bars">||||| || ||||| | |||| ||| | |||||</span>'
                f'<small>{valor}</small></div>'
            )
        else:
            contenido.append(f'<div class="label-text" style="left:{x}px;top:{y}px">{valor}</div>')
    return f'<div class="label" style="width:{ancho * escala}px;height:{alto * escala}px">{"".join(contenido)}</div>'


st.title("Etiquetas")
st.caption("Edita etiquetas Zebra o Datamax y conserva el formato original cuando no sea necesario convertirlo.")

if "elementos_etiqueta" not in st.session_state:
    st.session_state.elementos_etiqueta = [
        {"tipo": "TEXT", "x": 30, "y": 30, "valor": "Almacén Mator"},
        {"tipo": "BARCODE", "x": 30, "y": 80, "valor": "123456789"},
    ]
if "plantilla_nativa" not in st.session_state:
    st.session_state.plantilla_nativa = None
if "lab_datamax" not in st.session_state:
    st.session_state.lab_datamax = None

with st.expander("Cargar plantilla", expanded=True):
    st.write('Admite `.dtl`, `.lab`, `.bak` y `.txt` con `TEXT x,y,"texto"`, `BARCODE x,y,"codigo"` o comandos ZPL.')
    archivo_plantilla = st.file_uploader("Selecciona una plantilla", type=["dtl", "lab", "bak", "txt"])
    if archivo_plantilla is not None and st.button("Importar plantilla", key="importar_plantilla"):
        datos_plantilla = archivo_plantilla.getvalue()
        if datos_plantilla.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"):
            try:
                st.session_state.lab_datamax = {
                    "nombre": archivo_plantilla.name,
                    "datos": datos_plantilla,
                    "analisis": analizar_lab(datos_plantilla),
                }
                st.session_state.plantilla_nativa = None
                st.success("Archivo Lab Datamax cargado sin convertirlo a ZPL.")
            except (ImportError, ValueError, OSError) as error:
                st.error(f"No se pudo leer el contenedor Lab: {error}")
            st.rerun()
        try:
            contenido = decodificar_plantilla(datos_plantilla)
            st.session_state.elementos_etiqueta = parsear_plantilla(contenido)
            st.session_state.plantilla_nativa = None
            st.success(f"Se importaron {len(st.session_state.elementos_etiqueta)} elementos.")
        except ValueError as error:
            try:
                contenido = decodificar_plantilla(datos_plantilla)
            except ValueError:
                contenido = None
            st.session_state.plantilla_nativa = {
                "nombre": archivo_plantilla.name,
                "datos": datos_plantilla,
                "contenido": contenido,
                "error": str(error),
            }
            st.warning("Se conservará en formato Datamax nativo. No se convertirá a ZPL.")

if st.session_state.lab_datamax is not None:
    lab = st.session_state.lab_datamax
    analisis = lab["analisis"]
    st.subheader("Editor Datamax Lab")
    st.info(f"Formato nativo detectado. Impresora guardada: {analisis['impresora'] or 'no indicada'}")
    cambios = []
    for indice, texto in enumerate(analisis["textos"]):
        cambios.append(st.text_input(f"Texto {indice + 1}", value=texto["valor"], key=f"lab_texto_{indice}"))
    editar_col, descargar_col = st.columns(2)
    if editar_col.button("Aplicar cambios al Lab", use_container_width=True):
        try:
            lab["datos"] = editar_lab(lab["datos"], analisis["textos"], cambios)
            lab["analisis"] = analizar_lab(lab["datos"])
            st.session_state.lab_datamax = lab
            st.success("Cambios aplicados al archivo Lab nativo.")
            st.rerun()
        except (ValueError, OSError) as error:
            st.error(str(error))
    descargar_col.download_button(
        "Descargar Lab editado",
        data=lab["datos"],
        file_name=f"{nombre_sin_extension(lab['nombre'])}_editado.Lab",
        mime="application/octet-stream",
        use_container_width=True,
        key="descargar_lab_editado",
    )
    st.caption("Los textos no pueden superar la longitud reservada por el archivo original. La plantilla se conserva en formato Datamax y no se convierte a ZPL.")
    st.stop()

if st.session_state.plantilla_nativa is not None:
    plantilla = st.session_state.plantilla_nativa
    st.subheader("Plantilla Datamax nativa")
    st.info("Este archivo no se interpreta como ZPL. Puedes editar su fuente si es texto y descargarlo para enviarlo a la impresora Datamax.")
    if plantilla["contenido"] is None:
        st.error("El archivo es binario propietario. Se puede conservar y descargar, pero no editarlo como texto sin la aplicación Datamax que lo creó.")
        st.download_button(
            "Descargar plantilla Datamax original",
            data=plantilla["datos"],
            file_name=plantilla["nombre"],
            mime="application/octet-stream",
            key="descargar_datamax_binario",
        )
        st.stop()
    contenido_editado = st.text_area("Contenido editable", value=plantilla["contenido"], height=360, key="contenido_datamax")
    extension = re.search(r"\.[^.]+$", plantilla["nombre"])
    nombre_editado = f"{nombre_sin_extension(plantilla['nombre'])}_editada{extension.group(0) if extension else '.dtl'}"
    st.download_button(
        "Descargar plantilla Datamax editada",
        data=contenido_editado.encode("cp1252", errors="replace"),
        file_name=nombre_editado,
        mime="application/octet-stream",
        key="descargar_datamax_texto",
    )
    st.caption("Envía este archivo a la impresora Datamax con su controlador o software de impresión. El navegador no puede enviar archivos nativos directamente al puerto de la impresora.")
    st.stop()

col_config, col_preview = st.columns([1, 1])
with col_config:
    st.subheader("Diseño editable")
    dpi = st.selectbox("Resolución de la impresora", [203, 300, 600], index=1, format_func=lambda valor: f"{valor} dpi")
    ancho_mm = st.number_input("Ancho de etiqueta (mm)", min_value=10.0, max_value=300.0, value=107.0, step=0.1, format="%.1f")
    alto_mm = st.number_input("Alto de etiqueta (mm)", min_value=10.0, max_value=200.0, value=42.2, step=0.1, format="%.1f")
    oscuridad = st.number_input("Oscuridad", min_value=0, max_value=30, value=30, step=1)
    velocidad = st.number_input("Velocidad de impresión", min_value=1, max_value=15, value=5, step=1)
    ancho = round(ancho_mm / 25.4 * dpi)
    alto = round(alto_mm / 25.4 * dpi)
    st.caption(f"Tamaño ZPL calculado: {ancho} × {alto} puntos")
    nuevos = []
    for indice, elemento in enumerate(st.session_state.elementos_etiqueta):
        with st.expander(f"{elemento['tipo']} {indice + 1}", expanded=True):
            tipo = st.selectbox("Tipo", ["TEXT", "BARCODE"], index=["TEXT", "BARCODE"].index(elemento["tipo"]), key=f"tipo_{indice}")
            x_col, y_col = st.columns(2)
            x = x_col.number_input("X", value=int(elemento["x"]), min_value=0, max_value=int(ancho), key=f"x_{indice}")
            y = y_col.number_input("Y", value=int(elemento["y"]), min_value=0, max_value=int(alto), key=f"y_{indice}")
            valor = st.text_input("Texto o código", value=elemento["valor"], key=f"valor_{indice}")
            nuevos.append({"tipo": tipo, "x": x, "y": y, "valor": valor})
    st.session_state.elementos_etiqueta = nuevos
    add_col, clear_col = st.columns(2)
    if add_col.button("Añadir elemento", use_container_width=True):
        st.session_state.elementos_etiqueta.append({"tipo": "TEXT", "x": 30, "y": 30, "valor": "Nuevo texto"})
        st.rerun()
    if clear_col.button("Vaciar diseño", use_container_width=True):
        st.session_state.elementos_etiqueta = []
        st.rerun()

with col_preview:
    st.subheader("Vista previa")
    st.markdown(
        """<style>
        .label-wrap { background: #edf0f2; padding: 24px; min-height: 310px; display: flex; align-items: center; justify-content: center; }
        .label { position: relative; background: white; border: 1px solid #222; overflow: hidden; font-family: Arial, sans-serif; }
        .label-text, .barcode { position: absolute; white-space: nowrap; color: #111; }
        .label-text { font-size: 16px; font-weight: 600; }
        .barcode { display: flex; flex-direction: column; align-items: center; font-family: monospace; font-size: 11px; }
        .bars { font-size: 28px; letter-spacing: 2px; line-height: 25px; transform: scaleX(.8); }
        </style>"""
        + f'<div class="label-wrap">{vista_etiqueta(st.session_state.elementos_etiqueta, int(ancho), int(alto))}</div>',
        unsafe_allow_html=True,
    )

zpl = zpl_de_elementos(st.session_state.elementos_etiqueta, int(ancho), int(alto), int(oscuridad), int(velocidad))
vista_impresion = vista_etiqueta(st.session_state.elementos_etiqueta, int(ancho), int(alto))
st.subheader("Salida ZPL")
st.code(zpl, language="text")
download_col, print_col = st.columns(2)
download_col.download_button("Descargar ZPL", data=zpl.encode("utf-8"), file_name="etiqueta.zpl", mime="text/plain", use_container_width=True)
components.html(
    f'''<button onclick="imprimirEtiqueta()" style="width:100%;padding:0.55rem;border:1px solid #ff4b4b;border-radius:0.35rem;background:#ff4b4b;color:white;font-weight:600;cursor:pointer">Imprimir etiqueta</button>
<script>
function imprimirEtiqueta() {{
  const ventana = window.open('', '_blank', 'width=800,height=600');
    ventana.document.write('<html><head><title>Etiqueta</title><style>@page{{size:auto;margin:8mm}}body{{margin:0}}.label-wrap{{display:flex;align-items:center;justify-content:center}}.label{{position:relative;background:white;border:1px solid #222;overflow:hidden;font-family:Arial,sans-serif}}.label-text,.barcode{{position:absolute;white-space:nowrap;color:#111}}.label-text{{font-size:16px;font-weight:600}}.barcode{{display:flex;flex-direction:column;align-items:center;font-family:monospace;font-size:11px}}.bars{{font-size:28px;letter-spacing:2px;line-height:25px}}</style></head><body>' + {json.dumps(vista_impresion)} + '</body></html>');
  ventana.document.close(); ventana.focus(); ventana.print();
}}
</script>''',
    height=55,
)
st.caption("La impresión abre el diálogo del navegador. Para impresión Zebra directa, descarga el ZPL y envíalo con el controlador o Zebra Browser Print.")
