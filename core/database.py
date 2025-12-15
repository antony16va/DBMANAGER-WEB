"""
Módulo centralizado para conexiones a base de datos PostgreSQL
"""
import psycopg2
from typing import Optional, Tuple


class DatabaseConnection:
    """Gestor de conexiones a PostgreSQL reutilizable"""

    def __init__(self, host: str, port: str, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.conn: Optional[psycopg2.extensions.connection] = None
        self.cursor: Optional[psycopg2.extensions.cursor] = None

    def connect(self) -> bool:
        """Establece conexión a la base de datos"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.conn.autocommit = False
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            raise ConnectionError(f"Error al conectar a PostgreSQL: {e}")

    def disconnect(self):
        """Cierra la conexión a la base de datos"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def commit(self):
        """Confirma transacción"""
        if self.conn:
            self.conn.commit()

    def rollback(self):
        """Revierte transacción"""
        if self.conn:
            self.conn.rollback()

    def __enter__(self):
        """Soporte para context manager"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierre automático al salir del contexto"""
        if exc_type:
            self.rollback()
        self.disconnect()
