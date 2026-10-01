import streamlit as st
from utils.branding import mostrar_logo
from utils.db import get_conn
from utils.excel import generar_excel
from utils.telegram import enviar_telegram
from utils.almacen import analizar_materiales_albaran, obtener_ubicaciones_materiales
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

catalogo_materiales = sorted({
    linea.rsplit(" - ", 1)[0].strip()
    for (materiales_guardados,) in filas_materiales
    for linea in (materiales_guardados or "").splitlines()
    if linea.strip()
})

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
            placeholder="Escribe para buscar un material existente",
            key=f"seleccion_material_{i}",
        )
        mat = material_seleccionado or ""
    uni = st.number_input(f"Unidades {i+1}", min_value=1, value=1)
    materiales.append(f"{mat} - {uni} unidades")

pedidos_material = analizar_materiales_albaran("\n".join(materiales))
stock_por_material = obtener_ubicaciones_materiales(
    [pedido["material"] for pedido in pedidos_material]
)
ubicaciones_albaran = []
if pedidos_material:
    st.subheader("Ubicaciones actuales del material")
    for pedido in pedidos_material:
        clave_material = " ".join(pedido["material"].casefold().split())
        ubicaciones = stock_por_material.get(clave_material, [])
        disponible = sum(fila["unidades_disponibles"] for fila in ubicaciones)
        if ubicaciones:
            detalle = ", ".join(
                f"{fila['nave']} / {fila['seccion']} / {fila['ubicacion']} "
                f"({fila['unidades_disponibles']} unidades)"
                for fila in ubicaciones
            )
            st.caption(
                f"{pedido['material']}: {detalle}. "
                f"Disponible: {disponible}; pedido: {pedido['unidades']}."
            )
            ubicaciones_albaran.append(
                f"{pedido['material']} ({pedido['unidades']} unidades): {detalle}"
            )
        else:
            st.warning(f"{pedido['material']}: no aparece en existencias de ninguna nave.")
            ubicaciones_albaran.append(
                f"{pedido['material']} ({pedido['unidades']} unidades): sin existencias registradas"
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
