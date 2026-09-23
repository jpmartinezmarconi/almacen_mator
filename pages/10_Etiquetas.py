import html
import json
import re

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


def zpl_de_elementos(elementos, ancho, alto):
    partes = ["^XA", f"^PW{ancho}", f"^LL{alto}", "^CI28"]
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
st.caption("Carga una plantilla DTL, ajusta sus elementos y genera ZPL para una impresora Zebra.")

if "elementos_etiqueta" not in st.session_state:
    st.session_state.elementos_etiqueta = [
        {"tipo": "TEXT", "x": 30, "y": 30, "valor": "Almacén Mator"},
        {"tipo": "BARCODE", "x": 30, "y": 80, "valor": "123456789"},
    ]

with st.expander("Cargar plantilla", expanded=True):
    st.write('Admite `.dtl`, `.lab`, `.bak` y `.txt` con `TEXT x,y,"texto"`, `BARCODE x,y,"codigo"` o comandos ZPL.')
    archivo_plantilla = st.file_uploader("Selecciona una plantilla", type=["dtl", "lab", "bak", "txt"])
    if archivo_plantilla is not None and st.button("Importar plantilla", key="importar_plantilla"):
        try:
            contenido = archivo_plantilla.getvalue().decode("utf-8-sig")
            st.session_state.elementos_etiqueta = parsear_plantilla(contenido)
            st.success(f"Se importaron {len(st.session_state.elementos_etiqueta)} elementos.")
        except (UnicodeDecodeError, ValueError) as error:
            st.error(f"No se pudo convertir la plantilla. Comprueba que sea texto o ZPL: {error}")

col_config, col_preview = st.columns([1, 1])
with col_config:
    st.subheader("Diseño editable")
    dpi = st.selectbox("Resolución de la impresora", [203, 300, 600], index=0, format_func=lambda valor: f"{valor} dpi")
    ancho_mm = st.number_input("Ancho de etiqueta (mm)", min_value=10.0, max_value=300.0, value=107.0, step=0.1, format="%.1f")
    alto_mm = st.number_input("Alto de etiqueta (mm)", min_value=10.0, max_value=200.0, value=42.2, step=0.1, format="%.1f")
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

zpl = zpl_de_elementos(st.session_state.elementos_etiqueta, int(ancho), int(alto))
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
