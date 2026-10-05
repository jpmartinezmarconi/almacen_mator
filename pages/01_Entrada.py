import streamlit as st
from utils.branding import mostrar_logo
from utils.db import get_conn
from utils.excel import generar_excel
from utils.telegram import enviar_telegram
from utils.almacen import (
    analizar_materiales_albaran,
    clave_material_pedido,
    formatear_material_albaran,
    obtener_catalogo_materiales_con_codigo,
    obtener_ubicaciones_materiales,
)
import datetime
from zoneinfo import ZoneInfo

mostrar_logo()
st.title("Albarán de Entrada")

nombre = st.text_input("Nombre")
empresa = st.text_input("Empresa")
solicitado_por = st.text_input("Solicitado por")

st.subheader("Materiales pedidos")
materiales = []

conn_materiales = get_conn()
filas_materiales = conn_materiales.execute("SELECT materiales FROM albaranes").fetchall()
conn_materiales.close()

catalogo_por_clave = {}
for (materiales_guardados,) in filas_materiales:
    for pedido_guardado in analizar_materiales_albaran(materiales_guardados):
        clave = clave_material_pedido(pedido_guardado)
        catalogo_por_clave.setdefault(
            clave,
            (pedido_guardado["material"], pedido_guardado["codigo_material"]),
        )

for material, codigo_material in obtener_catalogo_materiales_con_codigo():
    clave = clave_material_pedido(
        {"material": material, "codigo_material": codigo_material or ""}
    )
    catalogo_por_clave[clave] = (material, codigo_material or "")

catalogo_por_etiqueta = {}
for material, codigo_material in sorted(
    catalogo_por_clave.values(),
    key=lambda articulo: (articulo[0].casefold(), articulo[1].casefold()),
):
    etiqueta = (
        f"{material} — Código: {codigo_material}"
        if codigo_material
        else material
    )
    catalogo_por_etiqueta[etiqueta] = formatear_material_albaran(
        material, codigo_material
    )
catalogo_materiales = list(catalogo_por_etiqueta)

num_lineas = st.number_input("Número de líneas", min_value=1, value=1)

for i in range(num_lineas):
    usar_material_manual = st.checkbox("Escribir material nuevo", key=f"usar_material_manual_{i}")
    if usar_material_manual:
        mat = st.text_input(
            f"Material {i+1}",
            key=f"material_manual_{i}",
        )
    else:
        material_seleccionado = st.selectbox(
            f"Material {i+1}",
            catalogo_materiales,
            index=None,
            placeholder="Busca por nombre o código de material",
            key=f"seleccion_material_{i}",
        )
        mat = catalogo_por_etiqueta.get(material_seleccionado, "")
    uni = st.number_input(f"Unidades {i+1}", min_value=1, value=1)
    materiales.append(f"{mat} - {uni} unidades")

pedidos_material = analizar_materiales_albaran("\n".join(materiales))
stock_por_material = obtener_ubicaciones_materiales(pedidos_material)
ubicaciones_albaran = []
if pedidos_material:
    st.subheader("Ubicaciones actuales del material")
    for pedido in pedidos_material:
        clave_material = clave_material_pedido(pedido)
        ubicaciones = stock_por_material.get(clave_material, [])
        disponible = sum(fila["unidades_disponibles"] for fila in ubicaciones)
        nombre_visible = pedido["material"]
        if pedido["codigo_material"]:
            nombre_visible += f" (Código: {pedido['codigo_material']})"
        if ubicaciones:
            detalle = ", ".join(
                f"{fila['nave']} / {fila['seccion']} / {fila['ubicacion']} "
                f"({fila['unidades_disponibles']} unidades)"
                for fila in ubicaciones
            )
            st.caption(
                f"{nombre_visible}: {detalle}. "
                f"Disponible: {disponible}; pedido: {pedido['unidades']}."
            )
            ubicaciones_albaran.append(
                f"{nombre_visible} ({pedido['unidades']} unidades): {detalle}"
            )
        else:
            st.warning(f"{nombre_visible}: no aparece en existencias de ninguna nave.")
            ubicaciones_albaran.append(
                f"{nombre_visible} ({pedido['unidades']} unidades): sin existencias registradas"
            )
    st.info(
        "Estas ubicaciones son orientativas al crear el albaran. "
        "El stock se descuenta al marcarlo como Procesando."
    )

comentario = st.text_area("Comentario opcional")

envio_recogida = st.radio("Tipo de entrega", ["Enviado por nosotros", "Vienen a buscar"])

if st.button("Enviar albarán"):
    conn = get_conn()
    cur = conn.cursor()

    datos = {
        "nombre": nombre,
        "empresa": empresa,
        "solicitado_por": solicitado_por,
        "materiales": "\n".join(materiales),
        "comentario": comentario,
        "envio_recogida": envio_recogida,
        "estado": "entrada",
        "observaciones": "",
        "fecha": datetime.datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
    }

    cur.execute("""
        INSERT INTO albaranes (nombre, empresa, solicitado_por, materiales, comentario,
        envio_recogida, estado, observaciones, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """, tuple(datos.values()))

    conn.commit()
    id_albaran = cur.fetchone()[0]

    datos_excel = {
        **datos,
        "ubicaciones": "\n".join(ubicaciones_albaran),
    }
    ruta_excel = generar_excel(datos_excel, id_albaran)

    telegram_enviado, telegram_error = enviar_telegram(
        "Tienes un nuevo albarán", devolver_error=True
    )

    st.success("Albarán enviado correctamente")
    st.info("Revisar en Finalizados cuando el albarán esté procesado.")
    st.info(f"Excel generado en: {ruta_excel}")
    if not telegram_enviado:
        st.error(f"El albarán se guardó, pero Telegram respondió: {telegram_error}")
