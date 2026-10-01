import re
from datetime import datetime

from utils.db import get_conn


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


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
            "COALESCE(SUM(s.palets), 0) AS palets_ocupados "
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
            "COALESCE(SUM(s.palets), 0) AS palets_ocupados "
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
            "s.unidades_sueltas, s.actualizado FROM almacen_stock s "
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
            "s.unidades_por_palet, s.unidades_sueltas "
            "FROM almacen_stock s "
            "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
            "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
            "WHERE sec.almacen_id=? AND sec.activa=1 AND u.activa=1 "
            "ORDER BY sec.nombre, u.codigo, s.material",
            (almacen_id,),
        ).fetchall()
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
                "SELECT COALESCE(SUM(s.palets), 0) "
                "FROM almacen_stock s "
                "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
                "WHERE u.seccion_id=?",
                (seccion_id,),
            ).fetchone()[0]
            if palets_actuales > capacidad_palets:
                raise ValueError(
                    f"No puedes reducir la capacidad por debajo de los "
                    f"{palets_actuales} palets que ya tiene la seccion."
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
):
    tipo = tipo.lower().strip()
    material = material.strip()
    codigo_material = codigo_material.strip()
    palets = int(palets)
    unidades_por_palet = int(unidades_por_palet)
    unidades_sueltas = int(unidades_sueltas)
    if tipo not in {"entrada", "salida"}:
        raise ValueError("El movimiento debe ser de entrada o salida.")
    if not material:
        raise ValueError("El material es obligatorio.")
    if palets < 0 or unidades_sueltas < 0 or unidades_por_palet < 1:
        raise ValueError("Las cantidades no pueden ser negativas.")
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
            "SELECT id, palets, unidades_por_palet, unidades_sueltas FROM almacen_stock "
            "WHERE ubicacion_id=? AND material=? AND codigo_material=?",
            (ubicacion_id, material, codigo_material),
        ).fetchone()
        palets_actuales = conn.execute(
            "SELECT COALESCE(SUM(palets), 0) FROM almacen_stock WHERE ubicacion_id=?",
            (ubicacion_id,),
        ).fetchone()[0]

        if tipo == "entrada":
            if palets_actuales + palets > ubicacion[0]:
                raise ValueError(
                    f"La ubicacion solo admite {ubicacion[0]} palets y quedaria con "
                    f"{palets_actuales + palets}."
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
                    "(ubicacion_id, material, codigo_material, palets, unidades_por_palet, unidades_sueltas, actualizado) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ubicacion_id, material, codigo_material, palets, upp, unidades_sueltas, ahora()),
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
            "SELECT id, palets, unidades_por_palet, unidades_sueltas "
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
            "SELECT id, palets, unidades_por_palet, unidades_sueltas "
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
            "SELECT COALESCE(SUM(palets), 0) FROM almacen_stock WHERE ubicacion_id=?",
            (ubicacion_destino_id,),
        ).fetchone()[0]
        if ocupacion_destino - (stock_destino[1] if stock_destino else 0) + nuevos_palets > destino[2]:
            raise ValueError(
                f"La ubicacion destino ({destino[1]}) no tiene capacidad para "
                "los palets trasladados."
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
            conn.execute(
                "UPDATE almacen_stock SET palets=?, unidades_sueltas=?, actualizado=? WHERE id=?",
                (nuevos_palets, nuevas_sueltas, ahora(), stock_destino[0]),
            )
        else:
            conn.execute(
                "INSERT INTO almacen_stock "
                "(ubicacion_id, material, codigo_material, palets, unidades_por_palet, "
                "unidades_sueltas, actualizado) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    ubicacion_destino_id,
                    material,
                    codigo_material,
                    nuevos_palets,
                    upp_destino,
                    nuevas_sueltas,
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
            "WHEN 'traslado_entrada' THEN 'Traslado recibido' ELSE m.tipo END, "
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
            "LEFT JOIN (SELECT ubicacion_id, SUM(palets) AS palets "
            "FROM almacen_stock GROUP BY ubicacion_id) s ON s.ubicacion_id=u.id "
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
