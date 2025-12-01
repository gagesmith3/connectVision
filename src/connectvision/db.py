from dataclasses import dataclass
from typing import Optional
from loguru import logger

@dataclass
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    table: str

class MySQLClient:
    def __init__(self, cfg: MySQLConfig):
        self.cfg = cfg
        self._conn = None
        self._cursor = None
        try:
            import mysql.connector
            self._conn = mysql.connector.connect(
                host=cfg.host,
                port=cfg.port,
                user=cfg.user,
                password=cfg.password,
                database=cfg.database,
            )
            self._cursor = self._conn.cursor()
            self._ensure_table()
        except Exception as e:
            logger.warning(f"MySQL unavailable: {e}")
            self._conn = None
            self._cursor = None

    def _ensure_table(self):
        ddl = (
            f"CREATE TABLE IF NOT EXISTS `{self.cfg.table}` ("
            "id BIGINT AUTO_INCREMENT PRIMARY KEY,"
            "event_type VARCHAR(32) NOT NULL,"
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ") ENGINE=InnoDB"
        )
        self._cursor.execute(ddl)
        self._conn.commit()

    def log_event(self, event_type: str):
        if not self._cursor:
            logger.info(f"(MySQL stub) Event: {event_type}")
            return
        sql = f"INSERT INTO `{self.cfg.table}` (event_type) VALUES (%s)"
        self._cursor.execute(sql, (event_type,))
        self._conn.commit()

    def close(self):
        try:
            if self._cursor:
                self._cursor.close()
            if self._conn:
                self._conn.close()
        except Exception:
            pass
