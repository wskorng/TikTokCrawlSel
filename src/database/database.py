import mysql.connector
from mysql.connector import Error
from typing import Optional
from ..config import DB_CONFIG
from ..logger import setup_logger

logger = setup_logger(__name__)

class Database:
    def __init__(self):
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            logger.info("データベースに接続しました")
        except Error as e:
            logger.error(f"データベース接続エラー: {e}")
            raise

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("データベース接続を閉じました")

    def get_connection(self):
        if not self.connection or not self.connection.is_connected():
            self.connect()
        return self.connection

    def execute_query(self, query: str, params: Optional[tuple] = None):
        try:
            cursor = self.get_connection().cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            return cursor
        except Error as e:
            logger.error(f"クエリ実行エラー: {e}")
            self.connection.rollback()
            raise
