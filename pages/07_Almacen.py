import io
import re
import unicodedata

import pandas as pd
import streamlit as st

from utils.almacen import (
    demanda_albaranes,
    eliminar_seccion,
    guardar_seccion,
    listar_secciones,
    listar_ubicaciones,
    obtener_detalle_ubicacion,
    obtener_movimientos,
    registrar_movimiento,
    resumen_almacen,
)
from utils.branding import mostrar_logo
from utils.db import get_conn, init_db


st.set_page_config(page_title="almacen virtual - Almacen Mator", layout="wide")
mostrar_logo()
init_db()

st.title("almacen virtual")
st.caption("Controla capacidad, ubicaciones, palets, unidades y pedidos desde un unico lugar.")


def formato_numero(valor):
    return f"{int(valor):,}".replace(",", ".")


def filas_a_dataframe(filas, columnas):
    return pd.DataFrame(filas, columns=columnas) if filas else pd.DataFrame(columns=columnas)


capacidad_total, palets_ocupados = resumen_almacen()
porcentaje = (palets_ocupados / capacidad_total * 100) if capacidad_total else 0
metricas = st.columns(4)
metricas[0].metric("Capacidad total", f"{formato_numero(capacidad_total)} palets")
metricas[1].metric("Palets ocupados", formato_numero(palets_ocupados))
metricas[2].metric("Espacio libre", formato_numero(max(capacidad_total - palets_ocupados, 0)))
metricas[3].metric("Ocupacion", f"{porcentaje:.1f}%")
st.progress(min(porcentaje / 100, 1.0), text=f"Ocupacion global: {porcentaje:.1f}%")

secciones = listar_secciones()


def mapa_seccion():
    if not secciones:
        st.info("Crea una seccion en la pestaña Configuracion para empezar.")
        return

    nombres = {fila[1]: fila for fila in secciones}
    nombre_seccion = st.selectbox("Seccion del mapa", list(nombres), key="seccion_mapa")
    seccion = nombres[nombre_seccion]
    ubicaciones = listar_ubicaciones(seccion[0])
    por_posicion = {(fila[2], fila[3]): fila for fila in ubicaciones}
    st.caption(
        f"{seccion[2] or 'Sin descripcion'} | {seccion[3]} filas x {seccion[4]} columnas | "
        f"{seccion[5]:g} m alto x {seccion[6]:g} m ancho x {seccion[7]:g} m fondo"
    )

    for fila in range(1, seccion[3] + 1):
        columnas = st.columns(seccion[4])
        for columna in range(1, seccion[4] + 1):
            ubicacion = por_posicion.get((fila, columna))
            with columnas[columna - 1]:
                if not ubicacion:
                    st.empty()
                    continue
                palets = int(ubicacion[9])
                capacidad = int(ubicacion[4])
                ocupada = palets >= capacidad
                tipo = "primary" if ocupada else "secondary"
                if st.button(
                    f"{ubicacion[1]}\n{palets}/{capacidad} palets",
                    key=f"mapa_{ubicacion[0]}",
                    type=tipo,
                    use_container_width=True,
                ):
                    st.session_state.ubicacion_seleccionada = ubicacion[0]
                st.caption("Completa" if ocupada else ("Libre" if palets == 0 else "Parcial"))

    ubicacion_id = st.session_state.get("ubicacion_seleccionada")
    ubicacion_seleccionada = next((fila for fila in ubicaciones if fila[0] == ubicacion_id), None)
    if not ubicacion_seleccionada:
        st.info("Haz clic en un espacio para consultar su contenido.")
        return

    st.subheader(f"Contenido de {ubicacion_seleccionada[1]}")
    detalle = obtener_detalle_ubicacion(ubicacion_id)
    if not detalle:
        st.success("Este espacio esta vacio.")
        return
    df_detalle = filas_a_dataframe(
        detalle,
        ["ID", "Material", "Codigo", "Palets", "Unidades por palet", "Unidades sueltas", "Actualizado"],
    )
    df_detalle["Unidades totales"] = (
        df_detalle["Palets"] * df_detalle["Unidades por palet"] + df_detalle["Unidades sueltas"]
    )
    st.dataframe(df_detalle.drop(columns=["ID"]), use_container_width=True, hide_index=True)


def resumen_por_seccion():
    filas = []
    for seccion in secciones:
        ubicaciones = listar_ubicaciones(seccion[0])
        capacidad = sum(int(ubicacion[4]) for ubicacion in ubicaciones)
        ocupados = sum(int(ubicacion[9]) for ubicacion in ubicaciones)
        filas.append(
            {
                "Seccion": seccion[1],
                "Espacios": len(ubicaciones),
                "Capacidad (palets)": capacidad,
                "Ocupados (palets)": ocupados,
                "Libres (palets)": max(capacidad - ocupados, 0),
                "Ocupacion (%)": round(ocupados / capacidad * 100, 1) if capacidad else 0,
            }
        )
    return pd.DataFrame(filas)


pestanas = st.tabs(["Mapa y ocupacion", "Movimientos", "Configuracion", "Importar Excel", "Pedidos"])

with pestanas[0]:
    mapa_seccion()
    st.subheader("Ocupacion por seccion")
    resumen = resumen_por_seccion()
    if resumen.empty:
        st.info("Todavia no hay secciones configuradas.")
    else:
        st.dataframe(resumen, use_container_width=True, hide_index=True)
        st.bar_chart(resumen.set_index("Seccion")["Ocupacion (%)"])

with pestanas[1]:
    if not secciones:
        st.info("Crea primero una seccion y sus espacios.")
    else:
        ubicaciones_totales = []
        for seccion in secciones:
            for ubicacion in listar_ubicaciones(seccion[0]):
                ubicaciones_totales.append((ubicacion[1], ubicacion[0], seccion[1]))
        ubicaciones_totales.sort()
        ubicacion_labels = [f"{codigo} ({seccion})" for codigo, _id, seccion in ubicaciones_totales]
        seleccion = st.selectbox("Espacio", ubicacion_labels, key="movimiento_ubicacion")
        ubicacion_id = ubicaciones_totales[ubicacion_labels.index(seleccion)][1]
        detalle = obtener_detalle_ubicacion(ubicacion_id)
        if detalle:
            st.dataframe(
                filas_a_dataframe(
                    detalle,
                    ["ID", "Material", "Codigo", "Palets", "Unidades por palet", "Unidades sueltas", "Actualizado"],
                ).drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
            )

        pedidos = demanda_albaranes()
        opciones_pedido = [0] + [pedido["albaran_id"] for pedido in pedidos]
        with st.form("formulario_movimiento", clear_on_submit=True):
            tipo = st.radio("Tipo de movimiento", ["entrada", "salida"], horizontal=True)
            material = st.text_input("Material")
            codigo_material = st.text_input("Codigo de material (opcional)")
            col1, col2, col3 = st.columns(3)
            palets = col1.number_input("Palets", min_value=0, step=1, value=0)
            unidades_por_palet = col2.number_input("Unidades por palet", min_value=1, step=1, value=1)
            unidades_sueltas = col3.number_input("Unidades sueltas", min_value=0, step=1, value=0)
            referencia = st.text_input("Referencia o nota")
            albaran_id = st.selectbox(
                "Vincular albaran (opcional)",
                opciones_pedido,
                format_func=lambda valor: "Sin vincular" if valor == 0 else f"Albaran #{valor}",
            )
            guardar_movimiento = st.form_submit_button("Registrar movimiento", type="primary")
        if guardar_movimiento:
            try:
                registrar_movimiento(
                    tipo,
                    ubicacion_id,
                    material,
                    codigo_material,
                    palets,
                    unidades_por_palet,
                    unidades_sueltas,
                    referencia,
                    albaran_id or None,
                )
                st.success("Movimiento registrado y ocupacion actualizada.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

        movimientos = obtener_movimientos()
        if movimientos:
            st.subheader("Ultimos movimientos")
            st.dataframe(
                filas_a_dataframe(
                    movimientos,
                    ["Fecha", "Tipo", "Ubicacion", "Material", "Palets", "Unidades por palet", "Unidades sueltas", "Referencia"],
                ),
                use_container_width=True,
                hide_index=True,
            )

with pestanas[2]:
    opciones_config = {"Nueva seccion": None}
    opciones_config.update({seccion[1]: seccion for seccion in secciones})
    seleccion_config = st.selectbox("Seccion a editar", list(opciones_config), key="seccion_config")
    seleccionada = opciones_config[seleccion_config]
    valores = seleccionada or (None, "", "", 1, 1, 2.5, 10.0, 10.0, 1, 1)
    with st.form("formulario_seccion"):
        nombre = st.text_input("Nombre", value=valores[1])
        descripcion = st.text_input("Descripcion", value=valores[2] or "")
        c1, c2, c3 = st.columns(3)
        filas = c1.number_input("Filas", min_value=1, step=1, value=int(valores[3]))
        columnas = c2.number_input("Columnas", min_value=1, step=1, value=int(valores[4]))
        capacidad_palets = c3.number_input(
            "Palets por espacio", min_value=1, step=1, value=int(valores[8])
        )
        c4, c5, c6 = st.columns(3)
        alto_m = c4.number_input("Alto (m)", min_value=0.1, step=0.1, value=float(valores[5]))
        ancho_m = c5.number_input("Ancho de espacio (m)", min_value=0.1, step=0.1, value=float(valores[6]))
        fondo_m = c6.number_input("Fondo de espacio (m)", min_value=0.1, step=0.1, value=float(valores[7]))
        guardar_config = st.form_submit_button("Guardar seccion y generar espacios", type="primary")
    if guardar_config:
        try:
            guardar_seccion(
                nombre,
                descripcion,
                int(filas),
                int(columnas),
                float(alto_m),
                float(ancho_m),
                float(fondo_m),
                int(capacidad_palets),
                valores[0],
            )
            st.success("Seccion guardada. Los espacios ya estan disponibles en el mapa.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"No se pudo guardar la seccion: {error}")
    if seleccionada and st.button("Desactivar seccion", type="secondary"):
        try:
            eliminar_seccion(seleccionada[0])
            st.success("Seccion desactivada.")
            st.rerun()
        except ValueError as error:
            st.error(str(error))

with pestanas[3]:
    st.subheader("Importar movimientos desde Excel o CSV")
    st.caption(
        "Columnas: ubicacion, material, palets, unidades_por_palet, unidades_sueltas, "
        "tipo_movimiento, codigo_material, referencia y albaran_id."
    )
    plantilla = pd.DataFrame(
        [{
            "ubicacion": "RECEPCION-R01-C01",
            "material": "Ejemplo",
            "codigo_material": "MAT-001",
            "palets": 1,
            "unidades_por_palet": 20,
            "unidades_sueltas": 0,
            "tipo_movimiento": "entrada",
            "referencia": "Inicial",
            "albaran_id": "",
        }]
    )
    st.download_button(
        "Descargar plantilla",
        plantilla.to_csv(index=False).encode("utf-8-sig"),
        "plantilla_movimientos_almacen.csv",
        "text/csv",
    )
    archivo = st.file_uploader("Selecciona un archivo", type=["xlsx", "xls", "csv"])
    if archivo:
        try:
            datos = (
                pd.read_csv(io.BytesIO(archivo.getvalue()))
                if archivo.name.lower().endswith(".csv")
                else pd.read_excel(archivo)
            )
            normalizadas = {
                unicodedata.normalize("NFKD", str(columna)).encode("ascii", "ignore").decode().lower().replace(" ", "_"): columna
                for columna in datos.columns
            }
            aliases = {
                "ubicacion": ("ubicacion", "espacio", "location"),
                "material": ("material", "producto", "descripcion"),
                "palets": ("palets", "pallets", "pallet"),
                "unidades_por_palet": ("unidades_por_palet", "unidades_palet", "cantidad_por_palet"),
                "unidades_sueltas": ("unidades_sueltas", "sueltas", "unidades"),
                "tipo_movimiento": ("tipo_movimiento", "tipo", "movimiento"),
                "codigo_material": ("codigo_material", "codigo", "sku"),
                "referencia": ("referencia", "nota", "pedido"),
                "albaran_id": ("albaran_id", "albaran"),
            }
            renombrar = {}
            for destino, nombres in aliases.items():
                encontrado = next((normalizadas[nombre] for nombre in nombres if nombre in normalizadas), None)
                if encontrado:
                    renombrar[encontrado] = destino
            datos = datos.rename(columns=renombrar)
            obligatorias = {"ubicacion", "material", "palets", "unidades_por_palet"}
            faltantes = obligatorias - set(datos.columns)
            if faltantes:
                st.error("Faltan columnas: " + ", ".join(sorted(faltantes)))
            else:
                st.dataframe(datos, use_container_width=True, hide_index=True)
                if st.button("Importar movimientos", type="primary"):
                    ubicaciones = {}
                    for seccion in secciones:
                        for ubicacion in listar_ubicaciones(seccion[0]):
                            ubicaciones[ubicacion[1]] = ubicacion[0]
                    errores = []
                    importados = 0
                    for indice, fila in datos.fillna("").iterrows():
                        try:
                            codigo_ubicacion = str(fila["ubicacion"]).strip()
                            if codigo_ubicacion not in ubicaciones:
                                raise ValueError(f"ubicacion desconocida: {codigo_ubicacion}")
                            registrar_movimiento(
                                str(fila.get("tipo_movimiento", "entrada") or "entrada"),
                                ubicaciones[codigo_ubicacion],
                                str(fila["material"]),
                                str(fila.get("codigo_material", "")),
                                int(float(fila["palets"] or 0)),
                                int(float(fila["unidades_por_palet"] or 1)),
                                int(float(fila.get("unidades_sueltas", 0) or 0)),
                                str(fila.get("referencia", "")),
                                int(float(fila["albaran_id"])) if str(fila.get("albaran_id", "")).strip() else None,
                            )
                            importados += 1
                        except (ValueError, TypeError) as error:
                            errores.append(f"Fila {indice + 2}: {error}")
                    if importados:
                        st.success(f"{importados} movimientos importados correctamente.")
                    for error in errores:
                        st.error(error)
        except Exception as error:
            st.error(f"No se pudo leer el archivo: {error}")

with pestanas[4]:
    st.subheader("Demanda pendiente de albaranes")
    demanda = demanda_albaranes()
    if not demanda:
        st.info("No hay materiales pendientes en albaranes de entrada o en proceso.")
    else:
        df_demanda = pd.DataFrame(demanda)
        st.dataframe(df_demanda, use_container_width=True, hide_index=True)
        agrupada = df_demanda.groupby("material", as_index=False)["unidades"].sum()
        agrupada = agrupada.rename(columns={"unidades": "Unidades pedidas"}).sort_values("Unidades pedidas", ascending=False)
        st.subheader("Unidades pedidas por material")
        st.bar_chart(agrupada.set_index("material"))
