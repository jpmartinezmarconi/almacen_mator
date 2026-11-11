import io
from html import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


COLUMNAS_RESUMEN = ("Material", "Código", "Unidades disponibles")
COLUMNAS_DETALLE = (
    "Nave", "Sección", "Ubicación", "Material", "Código", "Palets",
    "Unidades por palet", "Unidades sueltas", "Unidades disponibles",
    "Espacios por palet", "Espacios ocupados",
)


def preparar_inventario(almacenes, listar_stock):
    detalle = []
    totales = {}
    for almacen_id, nombre in almacenes:
        for fila in listar_stock(almacen_id):
            _, ubicacion, seccion, material, codigo, palets, por_palet, sueltas, espacios = fila
            if not palets and not sueltas:
                continue
            unidades = palets * por_palet + sueltas
            ocupados = (palets + (sueltas + por_palet - 1) // por_palet) * espacios
            codigo = codigo or ""
            detalle.append((
                nombre, seccion, ubicacion, material, codigo, palets, por_palet,
                sueltas, unidades, espacios, ocupados,
            ))
            clave = (material, codigo)
            totales[clave] = totales.get(clave, 0) + unidades
    resumen = [
        (material, codigo, unidades)
        for (material, codigo), unidades in sorted(totales.items())
    ]
    return resumen, detalle


def crear_excel_inventario(titulo_inventario, resumen, detalle):
    libro = Workbook()
    libro.remove(libro.active)
    for titulo, columnas, filas in (
        ("Resumen", COLUMNAS_RESUMEN, resumen),
        ("Detalle", COLUMNAS_DETALLE, detalle),
    ):
        hoja = libro.create_sheet(titulo)
        hoja.append([f"Inventario: {titulo_inventario}"])
        hoja.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columnas))
        hoja["A1"].font = Font(bold=True, size=14)
        hoja.append(columnas)
        for celda in hoja[2]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor="245A81")
            celda.alignment = Alignment(wrap_text=True)
        for fila in filas:
            hoja.append(fila)
            for celda in hoja[hoja.max_row]:
                if isinstance(celda.value, str):
                    celda.data_type = "s"
                    celda.alignment = Alignment(wrap_text=True, vertical="top")
        hoja.freeze_panes = "A3"
        hoja.auto_filter.ref = f"A2:{get_column_letter(len(columnas))}{hoja.max_row}"
        hoja.print_title_rows = "1:2"
        hoja.sheet_properties.pageSetUpPr.fitToPage = True
        hoja.page_setup.fitToWidth = 1
        hoja.page_setup.fitToHeight = 0
        hoja.page_setup.orientation = "landscape"
        hoja.page_setup.paperSize = hoja.PAPERSIZE_A4
        for indice, columna in enumerate(columnas, start=1):
            ancho = max(
                [len(columna)] + [len(str(fila[indice - 1])) for fila in filas]
            )
            hoja.column_dimensions[get_column_letter(indice)].width = min(ancho + 2, 35)
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def crear_html_impresion_inventario(titulo, resumen, detalle):
    def tabla(columnas, filas):
        cabecera = "".join(f"<th>{escape(columna)}</th>" for columna in columnas)
        cuerpo = "".join(
            "<tr>" + "".join(f"<td>{escape(str(valor))}</td>" for valor in fila) + "</tr>"
            for fila in filas
        )
        return f"<table><thead><tr>{cabecera}</tr></thead><tbody>{cuerpo}</tbody></table>"

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><style>
body {{ font-family: sans-serif; }}
button {{ cursor: pointer; padding: 0.5rem 1rem; }}
.informe {{ display: none; }}
@media print {{
  @page {{ size: A4 landscape; margin: 10mm; }}
  button {{ display: none; }}
  .informe {{ display: block; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 8pt; }}
  th, td {{ border: 1px solid #777; padding: 4px; text-align: left; overflow-wrap: anywhere; }}
  th {{ background: #eee; }}
  thead {{ display: table-header-group; }}
  tr {{ break-inside: avoid; }}
  h2 {{ margin-top: 20px; }}
}}
</style></head><body>
<button type="button" onclick="window.print()">Imprimir inventario</button>
<div class="informe">
<h1>Inventario: {escape(titulo)}</h1>
<h2>Resumen por material y código</h2>
{tabla(COLUMNAS_RESUMEN, resumen)}
<h2>Detalle por ubicación</h2>
{tabla(COLUMNAS_DETALLE, detalle)}
</div></body></html>"""
