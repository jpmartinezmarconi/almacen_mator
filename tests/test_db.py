import sqlite3
import unittest
import warnings

import pandas as pd

from utils.db import PostgresConnection


class PostgresConnectionTest(unittest.TestCase):
    def test_pandas_read_sql_query_with_empty_and_populated_results(self):
        raw_connection = sqlite3.connect(":memory:")
        self.addCleanup(raw_connection.close)
        raw_connection.execute(
            "CREATE TABLE equipos (id INTEGER, nombre TEXT, cantidad INTEGER, "
            "numero_serie TEXT, seccion TEXT, fecha_alta TEXT)"
        )
        connection = PostgresConnection(raw_connection)
        query = (
            "SELECT id, nombre, cantidad, numero_serie, seccion, fecha_alta "
            "FROM equipos ORDER BY id DESC"
        )

        for rows in ([], [(1, "Equipo", 2, "S1", "A", "2026-11-25")]):
            with self.subTest(rows=rows):
                if rows:
                    raw_connection.executemany("INSERT INTO equipos VALUES (?, ?, ?, ?, ?, ?)", rows)
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
                    result = pd.read_sql_query(query, connection)
                self.assertEqual(
                    list(result.columns),
                    ["id", "nombre", "cantidad", "numero_serie", "seccion", "fecha_alta"],
                )
                self.assertEqual(list(result.itertuples(index=False, name=None)), rows)


if __name__ == "__main__":
    unittest.main()
