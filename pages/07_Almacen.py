import io
import re
import unicodedata

import pandas as pd
import streamlit as st

from utils.almacen import (
    demanda_albaranes,
    desactivar_secciones,
    guardar_seccion,
    listar_almacenes,
    listar_secciones,
    listar_stock_ubicaciones,
    listar_ubicaciones_por_secciones,
    obtener_detalle_ubicacion,
    obtener_movimientos,
    registrar_movimiento,
    resumen_almacen,
    transferir_material,
)
from utils.branding import mostrar_logo
from utils.db import init_db


st.set_page_config(page_title="Almacen Virtual - Almacen Mator", layout="wide")
mostrar_logo()
init_db()

st.title("Almacen Virtual")
st.caption(
    "Selecciona una nave, crea secciones con su capacidad en palets y registra "
    "existencias o traslados."
)

almacenes = listar_almacenes()
almacen_id = st.selectbox(
    "Almacen",
    options=[fila[0] for fila in almacenes],
    format_func=lambda seleccionado: next(
        fila[1] for fila in almacenes if fila[0] == seleccionado
    ),
    key="almacen_seleccionado",
)


def formato_numero(valor):
    return f"{int(valor):,}".replace(",", ".")


def filas_a_dataframe(filas, columnas):
    return pd.DataFrame(filas, columns=columnas) if filas else pd.DataFrame(columns=columnas)


def clave_ubicacion(valor):
    return re.sub(r"[^A-Z0-9]", "", str(valor).strip().upper())


def mapa_importacion_ubicaciones(secciones, ubicaciones_por_seccion):
    ubicaciones = {}
    for seccion in secciones:
        espacios = ubicaciones_por_seccion.get(seccion[0], [])
        for ubicacion in espacios:
            ubicaciones[clave_ubicacion(ubicacion[1])] = ubicacion[0]
        if espacios:
            aliases = [seccion[1]]
            if seccion[2]:
                aliases.append(f"{seccion[2]} {seccion[1]}")
            for alias in aliases:
                ubicaciones.setdefault(clave_ubicacion(alias), espacios[0][0])
    return ubicaciones


capacidad_total, palets_ocupados = resumen_almacen(almacen_id)
porcentaje = (palets_ocupados / capacidad_total * 100) if capacidad_total else 0
metricas = st.columns(4)
metricas[0].metric("Capacidad total", f"{formato_numero(capacidad_total)} palets")
metricas[1].metric("Palets ocupados", formato_numero(palets_ocupados))
metricas[2].metric("Espacio libre", formato_numero(max(capacidad_total - palets_ocupados, 0)))
metricas[3].metric("Ocupacion", f"{porcentaje:.1f}%")
st.progress(min(porcentaje / 100, 1.0), text=f"Ocupacion global: {porcentaje:.1f}%")

secciones = listar_secciones(almacen_id)
ubicaciones_por_seccion = listar_ubicaciones_por_secciones(
    seccion[0] for seccion in secciones
)


def mapa_seccion():
    if not secciones:
        st.info("Crea una seccion en la pestaña Configuracion para empezar.")
        return

    nombres = {fila[1]: fila for fila in secciones}
    nombre_seccion = st.selectbox("Seccion del mapa", list(nombres), key="seccion_mapa")
    seccion = nombres[nombre_seccion]
    ubicaciones = ubicaciones_por_seccion.get(seccion[0], [])
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
        ubicaciones = ubicaciones_por_seccion.get(seccion[0], [])
        capacidad = sum(int(ubicacion[4]) for ubicacion in ubicaciones)
        ocupados = sum(int(ubicacion[9]) for ubicacion in ubicaciones)
        area_por_espacio = float(seccion[6]) * float(seccion[7])
        espacios_ocupados = sum(1 for ubicacion in ubicaciones if int(ubicacion[9]) > 0)
        area_restante = max(len(ubicaciones) - espacios_ocupados, 0) * area_por_espacio
        porcentaje_ocupado = round(ocupados / capacidad * 100, 1) if capacidad else 0
        filas.append(
            {
                "Seccion": seccion[1],
                "Espacios": len(ubicaciones),
                "Capacidad (palets)": capacidad,
                "Ocupados (palets)": ocupados,
                "Libres (palets)": max(capacidad - ocupados, 0),
                "Area restante (m2)": round(area_restante, 2),
                "Porcentaje ocupado (%)": porcentaje_ocupado,
                "Ocupacion (%)": porcentaje_ocupado,
            }
        )
    return pd.DataFrame(filas)


pestanas = st.tabs(
    [
        "Mapa y ocupacion",
        "Movimientos",
        "Configuracion",
        "Importar Excel",
        "Pedidos",
        "Traslados entre naves",
    ]
)
if not secciones:
    st.info(
        f"{next(fila[1] for fila in almacenes if fila[0] == almacen_id)} esta vacia. "
        "Ve a Configuracion para crear tu primera seccion."
    )

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
            for ubicacion in ubicaciones_por_seccion.get(seccion[0], []):
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

        movimientos = obtener_movimientos(almacen_id)
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
    valores = seleccionada or (None, "", "", 1, 1, 2.5, 1.2, 1.2, 1, 1)
    with st.form("formulario_seccion"):
        nombre = st.text_input("Nombre", value=valores[1])
        descripcion = st.text_input("Descripcion", value=valores[2] or "")
        capacidad_palets = st.number_input(
            "Capacidad de la seccion (palets)",
            min_value=1,
            step=1,
            value=int(valores[8]),
        )
        with st.expander("Dimensiones (opcional)"):
            alto_m = st.number_input("Alto (m)", min_value=0.1, step=0.1, value=float(valores[5]))
            ancho_m = st.number_input("Ancho (m)", min_value=0.1, step=0.1, value=float(valores[6]))
            fondo_m = st.number_input("Fondo (m)", min_value=0.1, step=0.1, value=float(valores[7]))
        guardar_config = st.form_submit_button("Guardar seccion", type="primary")
    if guardar_config:
        try:
            guardar_seccion(
                nombre,
                descripcion,
                1,
                1,
                float(alto_m),
                float(ancho_m),
                float(fondo_m),
                int(capacidad_palets),
                valores[0],
                almacen_id,
            )
            st.success(
                f"Seccion guardada con capacidad para {int(capacidad_palets)} palets."
            )
            st.rerun()
        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"No se pudo guardar la seccion: {error}")
    with st.form("formulario_desactivar_secciones"):
        secciones_a_desactivar = st.multiselect(
            "Secciones a desactivar",
            options=[seccion[0] for seccion in secciones],
            format_func=lambda seccion_id: next(
                seccion[1] for seccion in secciones if seccion[0] == seccion_id
            ),
        )
        desactivar = st.form_submit_button("Desactivar secciones", type="secondary")
    if desactivar:
        if not secciones_a_desactivar:
            st.error("Selecciona al menos una seccion.")
        else:
            try:
                cantidad = desactivar_secciones(secciones_a_desactivar)
                st.success(f"Se desactivaron {cantidad} secciones de esta nave. El historial se conserva.")
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
                    secciones_actualizadas = listar_secciones(almacen_id)
                    ubicaciones_actualizadas = listar_ubicaciones_por_secciones(
                        seccion[0] for seccion in secciones_actualizadas
                    )
                    ubicaciones = mapa_importacion_ubicaciones(
                        secciones_actualizadas,
                        ubicaciones_actualizadas,
                    )
                    ejemplos_ubicaciones = ", ".join(sorted(ubicaciones)[:8])
                    errores = []
                    importados = 0
                    for indice, fila in datos.fillna("").iterrows():
                        try:
                            codigo_ubicacion = str(fila["ubicacion"]).strip()
                            codigo_normalizado = clave_ubicacion(codigo_ubicacion)
                            if codigo_normalizado not in ubicaciones:
                                raise ValueError(
                                    f"ubicacion desconocida: {codigo_ubicacion}. "
                                    f"Ejemplos disponibles: {ejemplos_ubicaciones}"
                                )
                            registrar_movimiento(
                                str(fila.get("tipo_movimiento", "entrada") or "entrada"),
                                ubicaciones[codigo_normalizado],
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

with pestanas[5]:
    st.caption(
        "El almacen seleccionado arriba sera el origen; elige la otra nave como destino."
    )
    otros_almacenes = [fila for fila in almacenes if fila[0] != almacen_id]
    stock_origen = listar_stock_ubicaciones(almacen_id)
    if not otros_almacenes:
        st.info("No hay otra nave disponible para recibir el traslado.")
    elif not stock_origen:
        st.info("Esta nave no tiene existencias que se puedan trasladar.")
    else:
        destino_almacen_id = st.selectbox(
            "Trasladar a",
            options=[fila[0] for fila in otros_almacenes],
            format_func=lambda seleccionado: next(
                fila[1] for fila in otros_almacenes if fila[0] == seleccionado
            ),
            key="almacen_destino_traslado",
        )
        indice_stock = st.selectbox(
            "Material y ubicacion de origen",
            options=range(len(stock_origen)),
            format_func=lambda indice: (
                f"{stock_origen[indice][3]}"
                f"{' (' + stock_origen[indice][4] + ')' if stock_origen[indice][4] else ''}"
                f" | {stock_origen[indice][2]} / {stock_origen[indice][1]}"
                f" | {stock_origen[indice][5]} palets + {stock_origen[indice][7]} sueltas"
            ),
        )
        material_origen = stock_origen[indice_stock]
        secciones_destino = listar_secciones(destino_almacen_id)
        ubicaciones_destino_por_seccion = listar_ubicaciones_por_secciones(
            seccion[0] for seccion in secciones_destino
        )
        ubicaciones_destino = [
            (ubicacion[0], ubicacion[1], seccion[1])
            for seccion in secciones_destino
            for ubicacion in ubicaciones_destino_por_seccion.get(seccion[0], [])
        ]
        if not ubicaciones_destino:
            st.info("Configura secciones y ubicaciones en la nave de destino antes de trasladar.")
        else:
            ubicacion_destino_id = st.selectbox(
                "Ubicacion de destino",
                options=[ubicacion[0] for ubicacion in ubicaciones_destino],
                format_func=lambda seleccionado: next(
                    f"{ubicacion[1]} ({ubicacion[2]})"
                    for ubicacion in ubicaciones_destino
                    if ubicacion[0] == seleccionado
                ),
            )
            st.caption(
                f"Disponible en origen: {material_origen[5]} palets de "
                f"{material_origen[6]} unidades y {material_origen[7]} unidades sueltas."
            )
            with st.form("formulario_traslado", clear_on_submit=True):
                palets_trasladar = st.number_input(
                    "Palets a trasladar", min_value=0, step=1, value=0
                )
                unidades_sueltas_trasladar = st.number_input(
                    "Unidades sueltas a trasladar", min_value=0, step=1, value=0
                )
                referencia_traslado = st.text_input("Referencia o nota del traslado")
                confirmar_traslado = st.form_submit_button(
                    "Trasladar material", type="primary"
                )
            if confirmar_traslado:
                try:
                    transferir_material(
                        material_origen[0],
                        ubicacion_destino_id,
                        material_origen[3],
                        material_origen[4],
                        palets_trasladar,
                        unidades_sueltas_trasladar,
                        referencia_traslado,
                    )
                    st.success("Traslado registrado y existencias actualizadas en ambas naves.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
