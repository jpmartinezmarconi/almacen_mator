import html
import io
import json
import re
import tempfile
import base64

import streamlit as st
import streamlit.components.v1 as components

from utils.branding import LOGO_DATA, mostrar_logo

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
        encontrados.sort(
            key=lambda texto: (
                0 if re.match(r"^MATR[IÍ]CULA\s*:", texto["valor"], re.IGNORECASE) else
                1 if re.match(r"^AÑO\s*", texto["valor"], re.IGNORECASE) else 2
            )
        )
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


def elementos_visuales_lab(textos):
    ignorar = re.compile(
        r"^(Arial|Verdana|Tahoma|Text\d*|Text\d+ Copy.*|Line\d*.*|Image\d*|"
        r"Min=.*|Max=.*|All Image Files.*|Windows Bitmap.*|C:\\.*|2;0,.*)$",
        re.IGNORECASE,
    )
    visibles = [texto["valor"] for texto in textos if not ignorar.match(texto["valor"])]
    elementos = []
    for indice, valor in enumerate(visibles):
        columna, fila = divmod(indice, 10)
        x = 35 + columna * 620
        y = 30 + fila * 45
        matricula = re.match(r"^MATR[IÍ]CULA\s*:\s*(.+)$", valor, re.IGNORECASE)
        if matricula:
            elementos.append({"tipo": "BARCODE", "x": 353, "y": 300, "valor": matricula.group(1).strip()})
        else:
            elementos.append({"tipo": "TEXT", "x": x, "y": y, "valor": valor})
    return elementos


def vista_lab_datamax(textos, ancho, alto):
    elementos = elementos_visuales_lab(textos)
    return vista_etiqueta(elementos, ancho, alto)


def visor_interactivo_lab(elementos, ancho, alto):
    etiqueta = vista_etiqueta(elementos, ancho, alto)
    escala = min(400 / ancho, 190 / alto)
    ancho_visible = ancho * escala
    alto_visible = alto * escala
    return f"""
        <style>
            body {{ margin: 0; font-family: Arial, sans-serif; }}
            .stage {{ min-height: 300px; padding: 14px; background: #edf0f2; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }}
            .label {{ position: relative; user-select: none; overflow: hidden; }}
            .label-text {{ position: absolute; white-space: nowrap; color: #111; }}
            .label-text, .barcode, .logo-slot {{ cursor: move; }}
            .logo-slot {{ position: absolute; display: flex; align-items: center; justify-content: flex-start; overflow: hidden; }}
            .logo-slot img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
            .barcode {{ cursor: move; outline: 2px solid #1976d2; outline-offset: 3px; touch-action: none; z-index: 20; }}
            .resize-handle {{ position: absolute; right: -7px; bottom: -7px; width: 14px; height: 14px; background: #1976d2; border: 2px solid white; border-radius: 50%; cursor: nwse-resize; }}
            .barcode img {{ display: block; width: 230px; height: 82px; }}
            .tools {{ display: flex; gap: 8px; align-items: center; margin-top: 8px; }}
            button {{ border: 0; border-radius: 4px; padding: 8px 12px; color: white; background: #d32f2f; cursor: pointer; }}
            .hint {{ color: #555; font-size: 12px; }}
        </style>
        <div class="stage"><div id="label">{etiqueta}</div></div>
        <div class="tools"><button id="print" type="button">Imprimir etiqueta centrada</button><span class="hint">Arrastra el código azul. Usa el punto azul para cambiar su tamaño.</span></div>
        <script>
            const label = document.querySelector('#label .label');
            const barcode = label ? label.querySelector('.barcode') : null;
            const draggable = label ? label.querySelectorAll('.label-text, .barcode, .logo-slot') : [];
            let action = null, active = null, startX = 0, startY = 0, startLeft = 0, startTop = 0, startWidth = 0;
            draggable.forEach((item) => {{
                item.addEventListener('pointerdown', (event) => {{
                    event.preventDefault();
                    event.stopPropagation();
                    active = item;
                    action = item === barcode && event.target.classList.contains('resize-handle') ? 'resize' : 'move';
                    startX = event.clientX; startY = event.clientY;
                    startLeft = parseFloat(item.style.left) || 0;
                    startTop = parseFloat(item.style.top) || 0;
                    startWidth = item.getBoundingClientRect().width;
                    item.setPointerCapture(event.pointerId);
                }});
                item.addEventListener('pointermove', (event) => {{
                    if (!action) return;
                    if (action === 'move') {{
                        const labelRect = label.getBoundingClientRect();
                        const dx = (event.clientX - startX) / (labelRect.width / label.offsetWidth);
                        const dy = (event.clientY - startY) / (labelRect.height / label.offsetHeight);
                        active.style.left = Math.max(0, Math.min(label.offsetWidth - active.offsetWidth, startLeft + dx)) + 'px';
                        active.style.top = Math.max(0, Math.min(label.offsetHeight - active.offsetHeight, startTop + dy)) + 'px';
                    }} else {{
                        const width = Math.max(90, startWidth + event.clientX - startX);
                        active.style.width = Math.min(label.clientWidth - active.offsetLeft, width) + 'px';
                        active.querySelector('img').style.width = width + 'px';
                        active.querySelector('img').style.height = Math.max(45, width * 0.36) + 'px';
                    }}
                }});
                item.addEventListener('pointerup', () => {{ action = null; active = null; }});
                item.addEventListener('pointercancel', () => {{ action = null; active = null; }});
            }});
            document.getElementById('print').addEventListener('click', () => {{
                const popup = window.open('', '_blank', 'width=900,height=700');
                const printLabel = label.cloneNode(true);
                const sourceWidth = label.offsetWidth;
                const sourceHeight = label.offsetHeight;
                const sourceItems = label.querySelectorAll('.label-text, .barcode, .logo-slot');
                printLabel.style.width = '107mm';
                printLabel.style.height = '42.2mm';
                printLabel.style.transform = 'none';
                printLabel.querySelectorAll('.label-text, .barcode, .logo-slot').forEach((item, index) => {{
                    const left = parseFloat(item.style.left) || 0;
                    const top = parseFloat(item.style.top) || 0;
                    item.style.left = `${{left / sourceWidth * 107}}mm`;
                    item.style.top = `${{top / sourceHeight * 42.2}}mm`;
                    if (item.classList.contains('barcode')) {{
                        const width = sourceItems[index].getBoundingClientRect().width / sourceWidth * 107;
                        item.style.width = `${{width}}mm`;
                        item.querySelector('img').style.width = `${{width}}mm`;
                        item.querySelector('img').style.height = `${{width * 0.36}}mm`;
                    }}
                }});
                const labelHtml = printLabel.outerHTML;
                popup.document.write(`<html><head><title></title><style>
                    @page {{ size: 107mm 42.2mm; margin: 0; }}
                    html,body {{ margin: 0; padding: 0; width: 107mm; height: 42.2mm; }}
                    html, body {{ width: 107mm; height: 42.2mm; overflow: hidden; break-after: avoid; page-break-after: avoid; }}
                    body {{ margin: 0; padding: 0; overflow: hidden; }}
                    .print-sheet {{ width: 107mm; height: 42.2mm; margin: 0; display: flex; align-items: center; justify-content: center; overflow: hidden; break-after: avoid; page-break-after: avoid; }}
                    .label {{ position: relative; flex: 0 0 auto; width: 107mm !important; height: 42.2mm !important; overflow: hidden; transform: none !important; }}
                    .label-text,.barcode {{ position: absolute; white-space: nowrap; color: #111; }}
                    .label-text {{ font-size: 5.5mm !important; font-weight: 600; }}
                      .logo-slot {{ position: absolute; display: flex; align-items: center; justify-content: flex-start; overflow: hidden; }}
                      .logo-slot img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
                    .barcode {{ display: flex; flex-direction: column; align-items: center; outline: none !important; }}
                    .resize-handle {{ display: none; }}
                    .barcode img {{ display: block; }}
                </style></head><body><div class="print-sheet">${{labelHtml}}</div></body></html>`);
                popup.document.close(); popup.title = ''; popup.focus(); popup.print();
            }});
        </script>
        """


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
    escala = min(400 / ancho, 190 / alto)
    contenido = []
    fuente_px = 5.5 / 25.4 * 96 * escala
    logo_x = 35 * escala
    logo_y = 15 * escala
    logo_ancho = 280 * escala
    logo_alto = 85 * escala
    contenido.append(
        f'<div class="logo-slot" style="left:{logo_x}px;top:{logo_y}px;width:{logo_ancho}px;height:{logo_alto}px">'
        f'<img src="data:image/png;base64,{LOGO_DATA}" alt="Logo Mator"></div>'
    )
    for elemento in elementos:
        x = int(elemento["x"]) * escala
        y = int(elemento["y"]) * escala
        valor = html.escape(str(elemento["valor"]))
        if elemento["tipo"] == "BARCODE":
            try:
                import barcode
                from barcode.writer import SVGWriter

                codigo = barcode.get("code128", str(elemento["valor"]), writer=SVGWriter())
                svg = codigo.render(
                    writer_options={
                        "module_width": 0.22,
                        "module_height": 12,
                        "font_size": 8,
                        "text_distance": 2,
                        "quiet_zone": 2,
                    }
                )
                svg_data = base64.b64encode(svg).decode("ascii")
                contenido.append(
                    f'<div class="barcode" style="left:{x}px;top:{y}px">'
                    f'<img src="data:image/svg+xml;base64,{svg_data}" alt="Code 128 {valor}">'
                    f'<span class="resize-handle" aria-label="Cambiar tamaño"></span></div>'
                )
            except (ImportError, ValueError):
                contenido.append(f'<div class="label-text" style="left:{x}px;top:{y}px">Código inválido: {valor}</div>')
        else:
            contenido.append(f'<div class="label-text" style="left:{x}px;top:{y}px;font-size:{fuente_px:.2f}px">{valor}</div>')
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
        matricula = re.match(r"^MATR[IÍ]CULA\s*:\s*(.+)$", texto["valor"], re.IGNORECASE)
        if matricula:
            numero = st.text_input("Matrícula / código Code 128", value=matricula.group(1).strip(), key=f"lab_matricula_{indice}")
            cambios.append(f"{texto['valor'][:texto['valor'].find(':') + 1]} {numero}")
        elif re.match(r"^AÑO\s*", texto["valor"], re.IGNORECASE):
            cambios.append(st.text_input("Año", value=texto["valor"], key=f"lab_ano_{indice}"))
        else:
            cambios.append(st.text_input(f"Texto {indice + 1}", value=texto["valor"], key=f"lab_texto_{indice}"))
    textos_preview = [dict(texto, valor=cambio) for texto, cambio in zip(analisis["textos"], cambios)]
    elementos_preview = elementos_visuales_lab(textos_preview)
    st.subheader("Vista previa de la etiqueta")
    lab_ancho = round(107 / 25.4 * 300)
    lab_alto = round(42.2 / 25.4 * 300)
    components.html(visor_interactivo_lab(elementos_preview, lab_ancho, lab_alto), height=390, scrolling=False)
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
        .barcode img { display: block; width: 230px; height: 82px; }
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
        ventana.document.write('<html><head><title></title><style>@page{{size:auto;margin:8mm}}body{{margin:0}}.label-wrap{{display:flex;align-items:center;justify-content:center}}.label{{position:relative;background:white;border:1px solid #222;overflow:hidden;font-family:Arial,sans-serif}}.label-text,.barcode{{position:absolute;white-space:nowrap;color:#111}}.label-text{{font-size:16px;font-weight:600}}.barcode{{display:flex;flex-direction:column;align-items:center;font-family:monospace;font-size:11px}}.bars{{font-size:28px;letter-spacing:2px;line-height:25px}}</style></head><body>' + {json.dumps(vista_impresion)} + '</body></html>');
    ventana.document.close(); ventana.title = ''; ventana.focus(); ventana.print();
}}
</script>''',
    height=55,
)
st.caption("La impresión abre el diálogo del navegador. Para impresión Zebra directa, descarga el ZPL y envíalo con el controlador o Zebra Browser Print.")
