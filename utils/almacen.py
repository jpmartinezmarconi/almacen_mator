import re
from datetime import datetime, timezone

from utils.db import get_conn


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
OCUPACION_POR_STOCK_SQL = (
    "({alias}.palets + CASE WHEN {alias}.unidades_sueltas > 0 "
    "THEN ({alias}.unidades_sueltas + {alias}.unidades_por_palet - 1) "
    "/ {alias}.unidades_por_palet ELSE 0 END) * {alias}.espacios_por_palet"
)


def _espacios_ocupados(
    palets,
    unidades_por_palet,
    unidades_sueltas,
    espacios_por_palet=1,
):
    espacios_sueltos = (
        (unidades_sueltas + unidades_por_palet - 1) // unidades_por_palet
        if unidades_sueltas
        else 0
    )
    return (palets + espacios_sueltos) * espacios_por_palet


def ahora():
    return datetime.now().strftime(DATE_FORMAT)


def listar_almacenes():
    conn = get_conn()
    try:
        return conn.execute("SELECT id, nombre FROM almacenes ORDER BY id").fetchall()
    finally:
        conn.close()


def listar_secciones(almacen_id=1, incluir_inactivas=False):
    conn = get_conn()
    try:
        filtro = "" if incluir_inactivas else " AND activa = 1"
        return conn.execute(
            "SELECT id, nombre, descripcion, filas, columnas, alto_m, ancho_m, fondo_m, "
            "capacidad_palets, activa FROM almacen_secciones "
            "WHERE almacen_id = ?" + filtro + " ORDER BY nombre",
            (almacen_id,),
        ).fetchall()
    finally:
        conn.close()


def listar_ubicaciones(seccion_id, incluir_inactivas=False):
    conn = get_conn()
    try:
        filtro = "" if incluir_inactivas else " AND u.activa = 1"
        return conn.execute(
            "SELECT u.id, u.codigo, u.fila, u.columna, u.capacidad_palets, u.alto_m, "
            "u.ancho_m, u.fondo_m, u.activa, "
            f"COALESCE(SUM({OCUPACION_POR_STOCK_SQL.format(alias='s')}), 0) "
            "AS palets_ocupados "
            "FROM almacen_ubicaciones u LEFT JOIN almacen_stock s ON s.ubicacion_id = u.id "
            "WHERE u.seccion_id = ?" + filtro + " GROUP BY u.id ORDER BY u.fila, u.columna",
            (seccion_id,),
        ).fetchall()
    finally:
        conn.close()


def listar_ubicaciones_por_secciones(seccion_ids):
    seccion_ids = tuple(seccion_ids)
    if not seccion_ids:
        return {}

    placeholders = ", ".join("?" for _ in seccion_ids)
    conn = get_conn()
    try:
        filas = conn.execute(
            "SELECT u.seccion_id, u.id, u.codigo, u.fila, u.columna, "
            "u.capacidad_palets, u.alto_m, u.ancho_m, u.fondo_m, u.activa, "
            f"COALESCE(SUM({OCUPACION_POR_STOCK_SQL.format(alias='s')}), 0) "
            "AS palets_ocupados "
            "FROM almacen_ubicaciones u LEFT JOIN almacen_stock s ON s.ubicacion_id = u.id "
            f"WHERE u.seccion_id IN ({placeholders}) AND u.activa = 1 "
            "GROUP BY u.id ORDER BY u.seccion_id, u.fila, u.columna",
            seccion_ids,
        ).fetchall()
    finally:
        conn.close()

    resultado = {seccion_id: [] for seccion_id in seccion_ids}
    for fila in filas:
        resultado[fila[0]].append(fila[1:])
    return resultado


def obtener_detalle_ubicacion(ubicacion_id):
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT s.id, s.material, s.codigo_material, s.palets, s.unidades_por_palet, "
            "s.unidades_sueltas, s.actualizado, s.espacios_por_palet FROM almacen_stock s "
            "WHERE s.ubicacion_id = ? ORDER BY s.material",
            (ubicacion_id,),
        ).fetchall()
    finally:
        conn.close()


def listar_stock_ubicaciones(almacen_id):
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT u.id, u.codigo, sec.nombre, s.material, s.codigo_material, s.palets, "
            "s.unidades_por_palet, s.unidades_sueltas, s.espacios_por_palet "
            "FROM almacen_stock s "
            "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "WHERE sec.almacen_id=? AND sec.activa=1 AND u.activa=1 "
            "ORDER BY sec.nombre, u.codigo, s.material",
            (almacen_id,),
        ).fetchall()
    finally:
        conn.close()


def buscar_stock_materiales(consulta):
    consulta = consulta.strip()
    if not consulta:
        return []
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT a.nombre, sec.nombre, u.codigo, s.material, s.codigo_material, "
            "s.palets, s.unidades_por_palet, s.unidades_sueltas, s.espacios_por_palet "
            "FROM almacen_stock s "
            "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "JOIN almacenes a ON a.id=sec.almacen_id "
            "WHERE sec.activa=1 AND u.activa=1 "
            "AND (s.palets > 0 OR s.unidades_sueltas > 0) "
            "AND (LOWER(s.material) LIKE LOWER(?) "
            "OR LOWER(s.codigo_material) LIKE LOWER(?)) "
            "ORDER BY CASE WHEN LOWER(TRIM(a.nombre))='nave 1' THEN 0 ELSE 1 END, "
            "a.nombre, sec.nombre, s.material, s.codigo_material, u.codigo",
            (f"%{consulta}%", f"%{consulta}%"),
        ).fetchall()
    finally:
        conn.close()


def obtener_catalogo_materiales_con_codigo():
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT DISTINCT s.material, s.codigo_material FROM almacen_stock s "
            "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "WHERE sec.activa=1 AND u.activa=1 "
            "AND (s.palets > 0 OR s.unidades_sueltas > 0) "
            "ORDER BY s.material, s.codigo_material"
        ).fetchall()
    finally:
        conn.close()


def obtener_catalogo_materiales():
    conn = get_conn()
    try:
        filas = conn.execute(
            "SELECT DISTINCT s.material FROM almacen_stock s "
            "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "WHERE sec.activa=1 AND u.activa=1 "
            "AND (s.palets > 0 OR s.unidades_sueltas > 0) "
            "ORDER BY s.material"
        ).fetchall()
        return [fila[0] for fila in filas]
    finally:
        conn.close()


def guardar_seccion(
    nombre,
    descripcion,
    filas,
    columnas,
    alto_m,
    ancho_m,
    fondo_m,
    capacidad_palets,
    seccion_id=None,
    almacen_id=1,
):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la seccion es obligatorio.")
    if min(filas, columnas, capacidad_palets) < 1:
        raise ValueError("Filas, columnas y capacidad deben ser mayores que cero.")
    if min(alto_m, ancho_m, fondo_m) <= 0:
        raise ValueError("Las dimensiones deben ser mayores que cero.")

    conn = get_conn()
    try:
        prefijo_existente = None
        if seccion_id:
            pertenece_a_nave = conn.execute(
                "SELECT 1 FROM almacen_secciones WHERE id=? AND almacen_id=?",
                (seccion_id, almacen_id),
            ).fetchone()
            if not pertenece_a_nave:
                raise ValueError("La seccion seleccionada no pertenece a esta nave.")
            palets_actuales = conn.execute(
                f"SELECT COALESCE(SUM({OCUPACION_POR_STOCK_SQL.format(alias='s')}), 0) "
                "FROM almacen_stock s "
                "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
                "WHERE u.seccion_id=?",
                (seccion_id,),
            ).fetchone()[0]
            if palets_actuales > capacidad_palets:
                raise ValueError(
                    f"No puedes reducir la capacidad por debajo de los "
                    f"{palets_actuales} espacios de palet ocupados en la seccion."
                )
            codigo_existente = conn.execute(
                "SELECT codigo FROM almacen_ubicaciones WHERE seccion_id=? ORDER BY id LIMIT 1",
                (seccion_id,),
            ).fetchone()
            if codigo_existente:
                prefijo_existente = codigo_existente[0].split("-R", 1)[0]
        if seccion_id:
            conn.execute(
                "UPDATE almacen_secciones SET nombre=?, descripcion=?, filas=?, columnas=?, "
                "alto_m=?, ancho_m=?, fondo_m=?, capacidad_palets=?, activa=1 WHERE id=?",
                (nombre, descripcion.strip(), filas, columnas, alto_m, ancho_m, fondo_m, capacidad_palets, seccion_id),
            )
            fuera_de_mapa = conn.execute(
                "SELECT u.id, COALESCE(SUM(s.palets), 0), COALESCE(SUM(s.unidades_sueltas), 0) "
                "FROM almacen_ubicaciones u LEFT JOIN almacen_stock s ON s.ubicacion_id=u.id "
                "WHERE u.seccion_id=? AND (u.fila>? OR u.columna>?) GROUP BY u.id",
                (seccion_id, filas, columnas),
            ).fetchall()
            if any(palets or sueltas for _id, palets, sueltas in fuera_de_mapa):
                raise ValueError("No puedes reducir la seccion mientras sus espacios tengan stock.")
            for ubicacion_id, _palets, _sueltas in fuera_de_mapa:
                conn.execute("UPDATE almacen_ubicaciones SET activa=0 WHERE id=?", (ubicacion_id,))
        else:
            conn.execute(
                "INSERT INTO almacen_secciones "
                "(almacen_id, nombre, descripcion, filas, columnas, alto_m, ancho_m, fondo_m, capacidad_palets) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (almacen_id, nombre, descripcion.strip(), filas, columnas, alto_m, ancho_m, fondo_m, capacidad_palets),
            )
            seccion_id = conn.execute(
                "SELECT id FROM almacen_secciones WHERE almacen_id=? AND nombre = ?",
                (almacen_id, nombre),
            ).fetchone()[0]

        prefijo = prefijo_existente or re.sub(r"[^A-Za-z0-9]+", "-", nombre).strip("-").upper() or "SEC"
        for fila in range(1, filas + 1):
            for columna in range(1, columnas + 1):
                codigo = f"{prefijo}-R{fila:02d}-C{columna:02d}"
                existente = conn.execute(
                    "SELECT id FROM almacen_ubicaciones WHERE seccion_id=? AND codigo = ?",
                    (seccion_id, codigo),
                ).fetchone()
                if existente:
                    conn.execute(
                        "UPDATE almacen_ubicaciones SET seccion_id=?, fila=?, columna=?, "
                        "capacidad_palets=?, alto_m=?, ancho_m=?, fondo_m=?, activa=1 WHERE id=?",
                        (seccion_id, fila, columna, capacidad_palets, alto_m, ancho_m, fondo_m, existente[0]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO almacen_ubicaciones "
                        "(seccion_id, almacen_id, codigo, fila, columna, capacidad_palets, alto_m, ancho_m, fondo_m) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (seccion_id, almacen_id, codigo, fila, columna, capacidad_palets, alto_m, ancho_m, fondo_m),
                    )
        conn.commit()
        return seccion_id
    except Exception:
        conn.close()
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


def desactivar_secciones(seccion_ids):
    seccion_ids = tuple(dict.fromkeys(seccion_ids))
    if not seccion_ids:
        raise ValueError("Selecciona al menos una seccion.")

    placeholders = ", ".join("?" for _ in seccion_ids)
    conn = get_conn()
    try:
        filas = conn.execute(
            "SELECT sec.id, sec.nombre, sec.activa, "
            "COALESCE(SUM(stock.palets), 0), COALESCE(SUM(stock.unidades_sueltas), 0) "
            "FROM almacen_secciones sec "
            "LEFT JOIN almacen_ubicaciones u ON u.seccion_id = sec.id "
            "LEFT JOIN almacen_stock stock ON stock.ubicacion_id = u.id "
            f"WHERE sec.id IN ({placeholders}) GROUP BY sec.id",
            seccion_ids,
        ).fetchall()
        ids_encontrados = {fila[0] for fila in filas}
        if ids_encontrados != set(seccion_ids):
            raise ValueError("No se encontraron todas las secciones seleccionadas.")

        con_stock = [fila[1] for fila in filas if fila[3] or fila[4]]
        if con_stock:
            raise ValueError(
                "No se pueden desactivar secciones con stock: " + ", ".join(con_stock)
            )

        ids_activas = [fila[0] for fila in filas if fila[2]]
        if not ids_activas:
            raise ValueError("Las secciones seleccionadas ya estan desactivadas.")

        activos_placeholders = ", ".join("?" for _ in ids_activas)
        conn.execute(
            f"UPDATE almacen_secciones SET activa=0 WHERE id IN ({activos_placeholders})",
            tuple(ids_activas),
        )
        conn.execute(
            f"UPDATE almacen_ubicaciones SET activa=0 WHERE seccion_id IN ({activos_placeholders})",
            tuple(ids_activas),
        )
        conn.commit()
        return len(ids_activas)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def eliminar_seccion(seccion_id):
    desactivar_secciones([seccion_id])


def ajustar_stock(
    ubicacion_id,
    almacen_id,
    material,
    codigo_material,
    palets,
    unidades_por_palet,
    unidades_sueltas,
    espacios_por_palet=None,
):
    material = material.strip()
    codigo_material = codigo_material.strip()
    palets = int(palets)
    unidades_por_palet = int(unidades_por_palet)
    unidades_sueltas = int(unidades_sueltas)
    if espacios_por_palet is not None:
        espacios_por_palet = int(espacios_por_palet)
    if (
        palets < 0
        or unidades_sueltas < 0
        or unidades_por_palet < 1
    ):
        raise ValueError("Las cantidades no pueden ser negativas y las unidades por palet deben ser al menos 1.")
    if espacios_por_palet is not None and espacios_por_palet < 1:
        raise ValueError("Los espacios ocupados por palet deben ser al menos 1.")

    conn = get_conn()
    try:
        stock = conn.execute(
            "SELECT s.id, s.palets, s.unidades_por_palet, s.unidades_sueltas, "
            "u.codigo, sec.nombre, s.espacios_por_palet "
            "FROM almacen_stock s "
            "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "WHERE s.ubicacion_id=? AND sec.almacen_id=? AND sec.activa=1 "
            "AND u.activa=1 AND s.material=? AND s.codigo_material=?",
            (ubicacion_id, almacen_id, material, codigo_material),
        ).fetchone()
        if not stock:
            raise ValueError("No se encontro ese material activo en esta nave.")

        espacios_por_palet = (
            stock[6] if espacios_por_palet is None else espacios_por_palet
        )
        anteriores = (stock[1], stock[2], stock[3], stock[6])
        nuevos = (palets, unidades_por_palet, unidades_sueltas, espacios_por_palet)
        if anteriores == nuevos:
            raise ValueError("Las cantidades indicadas son iguales a las actuales.")

        capacidad = conn.execute(
            "SELECT u.capacidad_palets, "
            f"COALESCE(SUM({OCUPACION_POR_STOCK_SQL.format(alias='s')}), 0) "
            "FROM almacen_ubicaciones u "
            "LEFT JOIN almacen_stock s ON s.ubicacion_id=u.id "
            "WHERE u.id=? AND u.activa=1 GROUP BY u.id",
            (ubicacion_id,),
        ).fetchone()
        palets_ubicacion = (
            capacidad[1]
            - _espacios_ocupados(stock[1], stock[2], stock[3], stock[6])
            + _espacios_ocupados(
                palets,
                unidades_por_palet,
                unidades_sueltas,
                espacios_por_palet,
            )
        )
        if palets_ubicacion > capacidad[0]:
            raise ValueError(
                f"La ubicacion {stock[4]} solo admite {capacidad[0]} espacios de palet y "
                f"quedaria con {palets_ubicacion}."
            )

        if palets == 0 and unidades_sueltas == 0:
            conn.execute("DELETE FROM almacen_stock WHERE id=?", (stock[0],))
        else:
            conn.execute(
                "UPDATE almacen_stock SET palets=?, unidades_por_palet=?, "
                "unidades_sueltas=?, espacios_por_palet=?, actualizado=? WHERE id=?",
                (
                    palets,
                    unidades_por_palet,
                    unidades_sueltas,
                    espacios_por_palet,
                    ahora(),
                    stock[0],
                ),
            )

        conn.execute(
            "INSERT INTO almacen_movimientos "
            "(fecha, tipo, ubicacion_id, material, codigo_material, palets, "
            "unidades_por_palet, unidades_sueltas, referencia) "
            "VALUES (?, 'ajuste', ?, ?, ?, ?, ?, ?, ?)",
            (
                ahora(),
                ubicacion_id,
                material,
                codigo_material,
                palets,
                unidades_por_palet,
                unidades_sueltas,
                f"Ajuste manual en {stock[5]} / {stock[4]}: "
                f"{anteriores[0]} palets x {anteriores[1]} + {anteriores[2]} sueltas "
                f"(ocupan {anteriores[3]} espacios por palet) -> {palets} palets x "
                f"{unidades_por_palet} + {unidades_sueltas} sueltas "
                f"(ocupan {espacios_por_palet} espacios por palet)",
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def registrar_movimiento(
    tipo,
    ubicacion_id,
    material,
    codigo_material,
    palets,
    unidades_por_palet,
    unidades_sueltas,
    referencia="",
    albaran_id=None,
    espacios_por_palet=1,
):
    tipo = tipo.lower().strip()
    material = material.strip()
    codigo_material = codigo_material.strip()
    palets = int(palets)
    unidades_por_palet = int(unidades_por_palet)
    unidades_sueltas = int(unidades_sueltas)
    espacios_por_palet = int(espacios_por_palet)
    if tipo not in {"entrada", "salida"}:
        raise ValueError("El movimiento debe ser de entrada o salida.")
    if not material:
        raise ValueError("El material es obligatorio.")
    if (
        palets < 0
        or unidades_sueltas < 0
        or unidades_por_palet < 1
    ):
        raise ValueError("Las cantidades no pueden ser negativas.")
    if espacios_por_palet < 1:
        raise ValueError("Los espacios ocupados por palet deben ser al menos 1.")
    if palets == 0 and unidades_sueltas == 0:
        raise ValueError("Indica al menos un palet o una unidad.")

    conn = get_conn()
    try:
        ubicacion = conn.execute(
            "SELECT capacidad_palets FROM almacen_ubicaciones WHERE id=? AND activa=1",
            (ubicacion_id,),
        ).fetchone()
        if not ubicacion:
            raise ValueError("La ubicacion seleccionada no esta activa.")

        stock = conn.execute(
            "SELECT id, palets, unidades_por_palet, unidades_sueltas, espacios_por_palet "
            "FROM almacen_stock "
            "WHERE ubicacion_id=? AND material=? AND codigo_material=?",
            (ubicacion_id, material, codigo_material),
        ).fetchone()
        palets_actuales = conn.execute(
            f"SELECT COALESCE(SUM({OCUPACION_POR_STOCK_SQL.format(alias='s')}), 0) "
            "FROM almacen_stock s WHERE s.ubicacion_id=?",
            (ubicacion_id,),
        ).fetchone()[0]

        if tipo == "entrada":
            if stock:
                upp = stock[2]
                nueva_ocupacion_material = _espacios_ocupados(
                    stock[1] + palets,
                    upp,
                    stock[3] + unidades_sueltas,
                    stock[4],
                )
                ocupacion_material_actual = _espacios_ocupados(
                    stock[1], upp, stock[3], stock[4]
                )
            else:
                upp = unidades_por_palet
                nueva_ocupacion_material = _espacios_ocupados(
                    palets, upp, unidades_sueltas, espacios_por_palet
                )
                ocupacion_material_actual = 0
            palets_proyectados = (
                palets_actuales - ocupacion_material_actual + nueva_ocupacion_material
            )
            if palets_proyectados > ubicacion[0]:
                raise ValueError(
                    f"La ubicacion solo admite {ubicacion[0]} espacios de palet y quedaria con "
                    f"{palets_proyectados}."
                )
            if stock:
                nuevo_palets = stock[1] + palets
                nuevo_sueltas = stock[3] + unidades_sueltas
                upp = stock[2]
                conn.execute(
                    "UPDATE almacen_stock SET palets=?, unidades_sueltas=?, actualizado=? WHERE id=?",
                    (nuevo_palets, nuevo_sueltas, ahora(), stock[0]),
                )
            else:
                upp = unidades_por_palet
                conn.execute(
                    "INSERT INTO almacen_stock "
                    "(ubicacion_id, material, codigo_material, palets, unidades_por_palet, "
                    "unidades_sueltas, espacios_por_palet, actualizado) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        ubicacion_id,
                        material,
                        codigo_material,
                        palets,
                        upp,
                        unidades_sueltas,
                        espacios_por_palet,
                        ahora(),
                    ),
                )
        else:
            if not stock:
                raise ValueError("No hay ese material en la ubicacion seleccionada.")
            upp = stock[2]
            unidades_disponibles = stock[1] * upp + stock[3]
            unidades_solicitadas = palets * upp + unidades_sueltas
            if unidades_solicitadas > unidades_disponibles:
                raise ValueError(
                    f"Solo hay {unidades_disponibles} unidades disponibles de ese material."
                )
            restantes = unidades_disponibles - unidades_solicitadas
            nuevos_palets, nuevas_sueltas = divmod(restantes, upp)
            if nuevos_palets == 0 and nuevas_sueltas == 0:
                conn.execute("DELETE FROM almacen_stock WHERE id=?", (stock[0],))
            else:
                conn.execute(
                    "UPDATE almacen_stock SET palets=?, unidades_sueltas=?, actualizado=? WHERE id=?",
                    (nuevos_palets, nuevas_sueltas, ahora(), stock[0]),
                )

        conn.execute(
            "INSERT INTO almacen_movimientos "
            "(fecha, tipo, ubicacion_id, material, codigo_material, palets, unidades_por_palet, unidades_sueltas, referencia, albaran_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ahora(), tipo, ubicacion_id, material, codigo_material, palets, unidades_por_palet, unidades_sueltas, referencia.strip(), albaran_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def transferir_material(
    ubicacion_origen_id,
    ubicacion_destino_id,
    material,
    codigo_material,
    palets,
    unidades_sueltas,
    referencia="",
):
    material = material.strip()
    codigo_material = codigo_material.strip()
    palets = int(palets)
    unidades_sueltas = int(unidades_sueltas)
    if ubicacion_origen_id == ubicacion_destino_id:
        raise ValueError("El origen y el destino deben ser ubicaciones distintas.")
    if not material:
        raise ValueError("El material es obligatorio.")
    if palets < 0 or unidades_sueltas < 0 or (palets == 0 and unidades_sueltas == 0):
        raise ValueError("Indica una cantidad valida para trasladar.")

    conn = get_conn()
    try:
        ubicaciones = conn.execute(
            "SELECT u.id, u.codigo, u.capacidad_palets, sec.almacen_id, a.nombre "
            "FROM almacen_ubicaciones u "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "JOIN almacenes a ON a.id=sec.almacen_id "
            "WHERE u.id IN (?, ?) AND u.activa=1 AND sec.activa=1",
            (ubicacion_origen_id, ubicacion_destino_id),
        ).fetchall()
        por_id = {fila[0]: fila for fila in ubicaciones}
        origen = por_id.get(ubicacion_origen_id)
        destino = por_id.get(ubicacion_destino_id)
        if not origen or not destino:
            raise ValueError("El origen o el destino no estan activos.")
        if origen[3] == destino[3]:
            raise ValueError("El traslado debe ser entre naves distintas.")

        stock_origen = conn.execute(
            "SELECT id, palets, unidades_por_palet, unidades_sueltas, espacios_por_palet "
            "FROM almacen_stock WHERE ubicacion_id=? AND material=? AND codigo_material=?",
            (ubicacion_origen_id, material, codigo_material),
        ).fetchone()
        if not stock_origen:
            raise ValueError("No hay ese material en la ubicacion de origen.")
        upp_origen = stock_origen[2]
        unidades_origen = stock_origen[1] * upp_origen + stock_origen[3]
        unidades_a_trasladar = palets * upp_origen + unidades_sueltas
        if unidades_a_trasladar <= 0 or unidades_a_trasladar > unidades_origen:
            raise ValueError(f"Solo hay {unidades_origen} unidades disponibles de ese material.")

        stock_destino = conn.execute(
            "SELECT id, palets, unidades_por_palet, unidades_sueltas, espacios_por_palet "
            "FROM almacen_stock WHERE ubicacion_id=? AND material=? AND codigo_material=?",
            (ubicacion_destino_id, material, codigo_material),
        ).fetchone()
        upp_destino = stock_destino[2] if stock_destino else upp_origen
        unidades_destino = (
            stock_destino[1] * upp_destino + stock_destino[3] if stock_destino else 0
        )
        nuevos_palets, nuevas_sueltas = divmod(
            unidades_destino + unidades_a_trasladar, upp_destino
        )
        ocupacion_destino = conn.execute(
            f"SELECT COALESCE(SUM({OCUPACION_POR_STOCK_SQL.format(alias='s')}), 0) "
            "FROM almacen_stock s WHERE s.ubicacion_id=?",
            (ubicacion_destino_id,),
        ).fetchone()[0]
        ocupacion_anterior_material = (
            _espacios_ocupados(
                stock_destino[1],
                stock_destino[2],
                stock_destino[3],
                stock_destino[4],
            )
            if stock_destino
            else 0
        )
        ocupacion_nueva_material = _espacios_ocupados(
            nuevos_palets,
            upp_destino,
            nuevas_sueltas,
            stock_destino[4] if stock_destino else stock_origen[4],
        )
        ocupacion_proyectada = (
            ocupacion_destino - ocupacion_anterior_material + ocupacion_nueva_material
        )
        if ocupacion_proyectada > destino[2]:
            raise ValueError(
                f"La ubicacion destino ({destino[1]}) no tiene capacidad para "
                "los espacios de palet trasladados."
            )

        restantes_origen = unidades_origen - unidades_a_trasladar
        palets_restantes, sueltas_restantes = divmod(restantes_origen, upp_origen)
        if restantes_origen:
            conn.execute(
                "UPDATE almacen_stock SET palets=?, unidades_sueltas=?, actualizado=? WHERE id=?",
                (palets_restantes, sueltas_restantes, ahora(), stock_origen[0]),
            )
        else:
            conn.execute("DELETE FROM almacen_stock WHERE id=?", (stock_origen[0],))

        if stock_destino:
            if stock_destino[4] != stock_origen[4]:
                raise ValueError(
                    "El material ocupa distinto numero de espacios por palet en destino. "
                    "Corrige las existencias para unificar la ocupacion antes del traslado."
                )
            conn.execute(
                "UPDATE almacen_stock SET palets=?, unidades_sueltas=?, actualizado=? WHERE id=?",
                (nuevos_palets, nuevas_sueltas, ahora(), stock_destino[0]),
            )
        else:
            conn.execute(
                "INSERT INTO almacen_stock "
                "(ubicacion_id, material, codigo_material, palets, unidades_por_palet, "
                "unidades_sueltas, espacios_por_palet, actualizado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ubicacion_destino_id,
                    material,
                    codigo_material,
                    nuevos_palets,
                    upp_destino,
                    nuevas_sueltas,
                    stock_origen[4],
                    ahora(),
                ),
            )

        fecha = ahora()
        nota = referencia.strip()
        conn.execute(
            "INSERT INTO almacen_movimientos "
            "(fecha, tipo, ubicacion_id, material, codigo_material, palets, "
            "unidades_por_palet, unidades_sueltas, referencia) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fecha,
                "traslado_salida",
                ubicacion_origen_id,
                material,
                codigo_material,
                palets,
                upp_origen,
                unidades_sueltas,
                f"A {destino[4]} / {destino[1]}" + (f" | {nota}" if nota else ""),
            ),
        )
        conn.execute(
            "INSERT INTO almacen_movimientos "
            "(fecha, tipo, ubicacion_id, material, codigo_material, palets, "
            "unidades_por_palet, unidades_sueltas, referencia) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fecha,
                "traslado_entrada",
                ubicacion_destino_id,
                material,
                codigo_material,
                palets,
                upp_origen,
                unidades_sueltas,
                f"Desde {origen[4]} / {origen[1]}" + (f" | {nota}" if nota else ""),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_movimientos(almacen_id=1, limite=100):
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT m.fecha, CASE m.tipo "
            "WHEN 'traslado_salida' THEN 'Traslado enviado' "
            "WHEN 'traslado_entrada' THEN 'Traslado recibido' "
            "WHEN 'ajuste' THEN 'Ajuste de inventario' ELSE m.tipo END, "
            "u.codigo, m.material, m.palets, "
            "m.unidades_por_palet, m.unidades_sueltas, m.referencia "
            "FROM almacen_movimientos m JOIN almacen_ubicaciones u ON u.id=m.ubicacion_id "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "WHERE sec.almacen_id=? "
            "ORDER BY m.id DESC LIMIT ?",
            (almacen_id, limite),
        ).fetchall()
    finally:
        conn.close()


def resumen_almacen(almacen_id=1):
    conn = get_conn()
    try:
        fila = conn.execute(
            "SELECT COALESCE(SUM(u.capacidad_palets), 0), COALESCE(SUM(s.palets), 0) "
            "FROM almacen_ubicaciones u "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "LEFT JOIN (SELECT ubicacion_id, "
            f"SUM({OCUPACION_POR_STOCK_SQL.format(alias='stock')}) AS palets "
            "FROM almacen_stock stock GROUP BY ubicacion_id) s ON s.ubicacion_id=u.id "
            "WHERE u.activa=1 AND sec.almacen_id=?",
            (almacen_id,),
        ).fetchone()
        return int(fila[0]), int(fila[1])
    finally:
        conn.close()


def demanda_albaranes():
    conn = get_conn()
    try:
        filas = conn.execute(
            "SELECT id, nombre, empresa, materiales, estado, fecha FROM albaranes "
            "WHERE estado IN ('entrada', 'procesando') ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()

    resultado = []
    patron = re.compile(r"^(.*?)\s*-\s*(\d+)\s+unidades?\s*$", re.IGNORECASE)
    for albaran_id, nombre, empresa, materiales, estado, fecha in filas:
        for linea in (materiales or "").splitlines():
            coincidencia = patron.match(linea.strip())
            if coincidencia:
                material, unidades = coincidencia.groups()
            else:
                material, unidades = linea.strip(), "0"
            if material:
                resultado.append(
                    {
                        "albaran_id": albaran_id,
                        "pedido": nombre,
                        "empresa": empresa,
                        "material": material.strip(),
                        "unidades": int(unidades),
                        "estado": estado,
                        "fecha": fecha,
                    }
                )
    return resultado


def _normalizar_material(material):
    return " ".join(material.casefold().split())


def clave_material_pedido(pedido):
    return (
        _normalizar_material(pedido["material"]),
        _normalizar_material(pedido.get("codigo_material", "")),
    )


def formatear_material_albaran(material, codigo_material=""):
    material = material.strip()
    codigo_material = codigo_material.strip()
    return f"{material} [Codigo: {codigo_material}]" if codigo_material else material


def analizar_materiales_albaran(materiales):
    agrupados = {}
    patron = re.compile(
        r"^(.*?)(?:\s*\[Codigo:\s*([^\]]+)\])?\s*-\s*(\d+)\s+unidades?\s*$",
        re.IGNORECASE,
    )
    for linea in (materiales or "").splitlines():
        coincidencia = patron.match(linea.strip())
        if not coincidencia:
            continue
        nombre, codigo_material, unidades = coincidencia.groups()
        nombre = nombre.strip()
        codigo_material = (codigo_material or "").strip()
        if not nombre:
            continue
        pedido = {"material": nombre, "codigo_material": codigo_material}
        clave = clave_material_pedido(pedido)
        if clave not in agrupados:
            agrupados[clave] = {**pedido, "unidades": 0}
        agrupados[clave]["unidades"] += int(unidades)
    return list(agrupados.values())


def obtener_ubicaciones_materiales(materiales):
    pedidos = [
        material if isinstance(material, dict) else {"material": material}
        for material in materiales
    ]
    claves = {
        clave_material_pedido(pedido)
        for pedido in pedidos
        if pedido["material"].strip()
    }
    resultado = {clave: [] for clave in claves}
    if not claves:
        return resultado

    conn = get_conn()
    try:
        filas = conn.execute(
            "SELECT s.material, s.codigo_material, a.nombre, sec.nombre, u.codigo, "
            "s.palets, s.unidades_por_palet, s.unidades_sueltas, s.espacios_por_palet "
            "FROM almacen_stock s "
            "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "JOIN almacenes a ON a.id=sec.almacen_id "
            "WHERE sec.activa=1 AND u.activa=1 "
            "ORDER BY CASE WHEN LOWER(TRIM(a.nombre))='nave 1' THEN 0 ELSE 1 END, "
            "a.id, sec.nombre, u.codigo, s.material, s.codigo_material"
        ).fetchall()
    finally:
        conn.close()

    for fila in filas:
        clave_material = _normalizar_material(fila[0])
        codigo_material = _normalizar_material(fila[1] or "")
        claves_coincidentes = [
            clave
            for clave in claves
            if clave[0] == clave_material and (not clave[1] or clave[1] == codigo_material)
        ]
        for clave in claves_coincidentes:
            resultado[clave].append(
                {
                    "material": fila[0],
                    "codigo_material": fila[1],
                    "nave": fila[2],
                    "seccion": fila[3],
                    "ubicacion": fila[4],
                    "palets": fila[5],
                    "unidades_por_palet": fila[6],
                    "unidades_sueltas": fila[7],
                    "unidades_disponibles": fila[5] * fila[6] + fila[7],
                    "espacios_por_palet": fila[8],
                }
            )
    return resultado


def procesar_albaran(albaran_id, observaciones, foto_preparacion, numero_serie):
    conn = get_conn()
    try:
        albaran = conn.execute(
            "SELECT materiales FROM albaranes WHERE id=? AND estado='entrada'",
            (albaran_id,),
        ).fetchone()
        if not albaran:
            raise ValueError("El albaran ya no esta pendiente de procesar.")

        pedidos = analizar_materiales_albaran(albaran[0])
        stock = conn.execute(
            "SELECT s.id, s.material, s.codigo_material, s.palets, "
            "s.unidades_por_palet, s.unidades_sueltas, u.id, u.codigo, "
            "sec.nombre, a.nombre "
            "FROM almacen_stock s "
            "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "JOIN almacenes a ON a.id=sec.almacen_id "
            "WHERE sec.activa=1 AND u.activa=1 "
            "ORDER BY CASE WHEN LOWER(TRIM(a.nombre))='nave 1' THEN 0 ELSE 1 END, "
            "a.id, sec.nombre, u.codigo, s.material, s.codigo_material, s.id"
        ).fetchall()
        stock_por_material = {}
        for fila in stock:
            clave = (
                _normalizar_material(fila[1]),
                _normalizar_material(fila[2] or ""),
            )
            stock_por_material.setdefault(clave, []).append(fila)

        descuentos = []
        faltantes = []
        for pedido in pedidos:
            clave = clave_material_pedido(pedido)
            if clave[1]:
                disponibles = stock_por_material.get(clave, [])
            else:
                disponibles = [
                    fila
                    for (nombre, _codigo), filas in stock_por_material.items()
                    if nombre == clave[0]
                    for fila in filas
                ]
            total_disponible = sum(
                fila[3] * fila[4] + fila[5] for fila in disponibles
            )
            if total_disponible < pedido["unidades"]:
                faltantes.append(
                    {
                        **pedido,
                        "disponibles": total_disponible,
                    }
                )
                continue

            por_descontar = pedido["unidades"]
            for fila in disponibles:
                disponibles_fila = fila[3] * fila[4] + fila[5]
                unidades = min(por_descontar, disponibles_fila)
                if not unidades:
                    continue
                restantes = disponibles_fila - unidades
                palets_restantes, sueltas_restantes = divmod(restantes, fila[4])
                if restantes:
                    actualizacion = conn.execute(
                        "UPDATE almacen_stock SET palets=?, unidades_sueltas=?, actualizado=? "
                        "WHERE id=? AND palets=? AND unidades_por_palet=? AND unidades_sueltas=?",
                        (
                            palets_restantes,
                            sueltas_restantes,
                            ahora(),
                            fila[0],
                            fila[3],
                            fila[4],
                            fila[5],
                        ),
                    )
                else:
                    actualizacion = conn.execute(
                        "DELETE FROM almacen_stock "
                        "WHERE id=? AND palets=? AND unidades_por_palet=? AND unidades_sueltas=?",
                        (fila[0], fila[3], fila[4], fila[5]),
                    )
                if actualizacion.rowcount != 1:
                    raise ValueError(
                        "El stock cambio mientras se procesaba el albaran. "
                        "Vuelve a intentarlo para actualizar las ubicaciones."
                    )

                palets_movimiento, sueltas_movimiento = divmod(unidades, fila[4])
                conn.execute(
                    "INSERT INTO almacen_movimientos "
                    "(fecha, tipo, ubicacion_id, material, codigo_material, palets, "
                    "unidades_por_palet, unidades_sueltas, referencia, albaran_id) "
                    "VALUES (?, 'salida', ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        ahora(),
                        fila[6],
                        fila[1],
                        fila[2],
                        palets_movimiento,
                        fila[4],
                        sueltas_movimiento,
                        f"Pedido albaran #{albaran_id} - {fila[9]} / {fila[8]}",
                        albaran_id,
                    ),
                )
                descuentos.append(
                    {
                        "material": pedido["material"],
                        "unidades": unidades,
                        "nave": fila[9],
                        "seccion": fila[8],
                        "ubicacion": fila[7],
                    }
                )
                por_descontar -= unidades
                if not por_descontar:
                    break

        observaciones_finales = observaciones.strip()
        if faltantes:
            detalle_faltantes = "; ".join(
                f"{fila['material']}: pedidos {fila['unidades']}, disponibles {fila['disponibles']}"
                for fila in faltantes
            )
            aviso = "No descontado del inventario por stock insuficiente: " + detalle_faltantes
            observaciones_finales = (
                f"{observaciones_finales}\n{aviso}".strip()
            )

        actualizacion_albaran = conn.execute(
            "UPDATE albaranes SET estado='procesando', observaciones=?, "
            "foto_preparacion=?, numero_serie=?, procesado_en=? "
            "WHERE id=? AND estado='entrada'",
            (
                observaciones_finales,
                foto_preparacion,
                numero_serie,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                albaran_id,
            ),
        )
        if actualizacion_albaran.rowcount != 1:
            raise ValueError("El albaran ya no esta pendiente de procesar.")
        conn.commit()
        return {"descuentos": descuentos, "faltantes": faltantes}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_consumos_albaran(albaran_id):
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT a.nombre, sec.nombre, u.codigo, m.material, m.codigo_material, "
            "(m.palets * m.unidades_por_palet + m.unidades_sueltas) "
            "FROM almacen_movimientos m "
            "JOIN almacen_ubicaciones u ON u.id=m.ubicacion_id "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "JOIN almacenes a ON a.id=sec.almacen_id "
            "WHERE m.albaran_id=? AND m.tipo='salida' "
            "ORDER BY a.id, sec.nombre, u.codigo, m.material",
            (albaran_id,),
        ).fetchall()
    finally:
        conn.close()
