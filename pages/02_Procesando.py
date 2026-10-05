import os
from io import BytesIO

import streamlit as st
from PIL import Image, ImageOps
from utils.almacen import (
    analizar_materiales_albaran,
    clave_material_pedido,
    obtener_consumos_albaran,
    obtener_ubicaciones_materiales,
    procesar_albaran,
)
from utils.branding import mostrar_logo
from utils.albaranes import (
    finalizar_albaranes_vencidos,
    finalizar_albaranes_seleccionados,
    iniciar_finalizador_automatico,
)
from utils.db import get_conn, init_db

mostrar_logo()
init_db()
finalizar_albaranes_vencidos()
iniciar_finalizador_automatico()
st.title("Procesando Albaranes")

password = st.text_input("Contraseña", type="password")

if password != "ju@n":
    st.error("Contraseña incorrecta")
    st.stop()

conn = get_conn()
cur = conn.cursor()
MAX_ALBARANES_PROCESANDO = 20

cur.execute("SELECT * FROM albaranes WHERE estado='entrada' ORDER BY id")
pendientes = cur.fetchall()
cur.execute("SELECT COUNT(*) FROM albaranes WHERE estado='procesando'")
albaranes_en_proceso = cur.fetchone()[0]
cur.execute("SELECT * FROM albaranes WHERE estado='procesando' ORDER BY id")
en_proceso = cur.fetchall()
conn.close()

st.subheader("Albaranes pendientes")
st.caption(f"Albaranes en procesando: {albaranes_en_proceso}/{MAX_ALBARANES_PROCESANDO}")

if albaranes_en_proceso >= MAX_ALBARANES_PROCESANDO:
    st.warning("Se ha alcanzado el máximo de 20 albaranes en procesando. Finaliza alguno antes de añadir otro.")

for albaran in pendientes:
    (
        id_,
        nombre,
        empresa,
        solicitado_por,
        materiales,
        comentario,
        envio_recogida,
        estado,
        observaciones,
        _,
        fecha,
        foto_preparacion,
        numero_serie,
        _,
    ) = albaran

    with st.expander(f"Albarán #{id_} - {nombre}"):
        st.write(f"Empresa: {empresa}")
        st.write(f"Solicitado por: {solicitado_por}")
        st.write(f"Materiales:\n{materiales}")
        st.write(f"Comentario: {comentario}")
        st.write(f"Entrega: {envio_recogida}")

        pedidos = analizar_materiales_albaran(materiales)
        stock_por_material = obtener_ubicaciones_materiales(
            pedidos
        )
        st.subheader("Ubicaciones para preparar el pedido")
        for pedido in pedidos:
            clave = clave_material_pedido(pedido)
            ubicaciones = stock_por_material.get(clave, [])
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
                st.write(
                    f"**{nombre_visible}** — {detalle}. "
                    f"Pedido: {pedido['unidades']}; disponible: {disponible}."
                )
                if disponible < pedido["unidades"]:
                    st.warning(
                        "No hay existencias suficientes; esta línea no se descontará "
                        "al pasar el albarán a Procesando."
                    )
            else:
                st.warning(
                    f"{nombre_visible}: sin existencias registradas; "
                    "esta línea no se descontará."
                )

        st.subheader("Observaciones internas")
        nuevas_obs = st.text_area(
            "Añadir observaciones", value=observaciones or "", key=f"observaciones_{id_}"
        )

        st.subheader("Lectura de código de barras")
        codigo = st.text_input("Escanea el código aquí (lector Zebra)", key=f"codigo_{id_}")
        st.write(f"Código leído: {codigo or numero_serie or 'Pendiente'}")

        imagen = st.camera_input("O usa la cámara de la Zebra", key=f"imagen_{id_}")

        if st.button(f"Marcar como procesado #{id_}", key=f"procesar_{id_}"):
            if albaranes_en_proceso >= MAX_ALBARANES_PROCESANDO:
                st.error("No puedes tener más de 20 albaranes en procesando a la vez.")
                continue
            if imagen is None:
                st.error("Debes sacar una foto de la preparación antes de marcar el albarán como procesado.")
                continue

            ruta_foto = os.path.join("data", f"albaran_{id_}_preparacion.jpg")
            ruta_foto_completa = os.path.join(os.path.dirname(os.path.dirname(__file__)), ruta_foto)
            imagen_preparada = ImageOps.exif_transpose(Image.open(BytesIO(imagen.getvalue())))
            if imagen_preparada.mode != "RGB":
                imagen_preparada = imagen_preparada.convert("RGB")
            with open(ruta_foto_completa, "wb") as archivo_foto:
                imagen_preparada.save(
                    archivo_foto,
                    format="JPEG",
                    quality=95,
                    subsampling=0,
                    optimize=True,
                )

            try:
                resultado = procesar_albaran(
                    id_,
                    nuevas_obs,
                    ruta_foto,
                    codigo.strip(),
                )
                st.success("Albarán actualizado y existencias disponibles descontadas.")
                if resultado["faltantes"]:
                    st.warning(
                        "Se procesó el albarán, pero estas líneas no se descontaron "
                        "por falta de stock: "
                        + "; ".join(
                            f"{fila['material']} (pedido {fila['unidades']}, "
                            f"disponible {fila['disponibles']})"
                            for fila in resultado["faltantes"]
                        )
                    )
                st.rerun()
            except ValueError as error:
                st.error(str(error))

st.subheader("Albaranes en Procesando")
if not en_proceso:
    st.info("No hay albaranes en proceso.")
else:
    st.caption(
        f"Hay {len(en_proceso)} albaranes en Procesando. "
        "Si ya están completados, puedes finalizarlos aquí sin esperar 24 horas. "
        "Esta acción no vuelve a descontar existencias."
    )
    etiquetas_por_id = {
        albaran[0]: f"#{albaran[0]} - {albaran[1]} ({albaran[2]})"
        for albaran in en_proceso
    }
    ids_para_finalizar = st.multiselect(
        "Selecciona los albaranes completados",
        options=list(etiquetas_por_id),
        format_func=lambda albaran_id: etiquetas_por_id[albaran_id],
        key="albaranes_para_finalizar",
    )
    if st.button(
        f"Finalizar seleccionados ({len(ids_para_finalizar)})",
        type="primary",
        disabled=not ids_para_finalizar,
        key="finalizar_albaranes_procesando",
    ):
        try:
            cantidad_finalizada = finalizar_albaranes_seleccionados(ids_para_finalizar)
        except ValueError as error:
            st.error(str(error))
        else:
            if cantidad_finalizada:
                st.success(
                    f"{cantidad_finalizada} albarán(es) finalizado(s). "
                    "El cupo de Procesando ya está disponible."
                )
            else:
                st.info("Los albaranes seleccionados ya no estaban en Procesando.")
            st.rerun()

for albaran in en_proceso:
    (
        id_,
        nombre,
        empresa,
        solicitado_por,
        materiales,
        comentario,
        envio_recogida,
        estado,
        observaciones,
        _,
        fecha,
        foto_preparacion,
        numero_serie,
        _,
    ) = albaran
    with st.expander(f"Albarán #{id_} - {nombre}"):
        st.write(f"Empresa: {empresa}")
        st.write(f"Materiales:\n{materiales}")
        consumos = obtener_consumos_albaran(id_)
        if consumos:
            st.write("**Ubicaciones de las que se descontó el material:**")
            for nave, seccion, ubicacion, material, codigo_material, unidades in consumos:
                codigo = f" ({codigo_material})" if codigo_material else ""
                st.write(
                    f"- {material}{codigo}: {unidades} unidades — "
                    f"{nave} / {seccion} / {ubicacion}"
                )
        else:
            st.info("No se descontó material del inventario para este albarán.")
        if observaciones:
            st.write(f"Observaciones: {observaciones}")
