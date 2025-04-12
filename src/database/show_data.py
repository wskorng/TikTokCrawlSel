from .database import Database
from ..logger import setup_logger
from dotenv import load_dotenv
from typing import List, Dict, Any
from tabulate import tabulate

logger = setup_logger(__name__)

def fetch_table_data(db: Database, table_name: str) -> List[Dict[str, Any]]:
    """テーブルの全データを取得"""
    query = f"SELECT * FROM {table_name}"
    db.connect()
    cursor = db.connection.cursor(dictionary=True)
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    return rows

def show_all_data():
    """全テーブルのデータを表示"""
    load_dotenv()
    db = Database()
    
    try:
        # 各テーブルのデータを取得して表示
        tables = [
            "crawler_accounts",
            "favorite_accounts",
            "video_desc_raw_data",
            "video_stat_raw_data"
        ]
        
        for table in tables:
            print(f"\n=== {table} ===")
            data = fetch_table_data(db, table)
            if data:
                print(tabulate(data, headers="keys", tablefmt="grid"))
            else:
                print("データがありません")
            
    except Exception as e:
        logger.error(f"データ取得中にエラーが発生: {e}")
        raise
    finally:
        db.disconnect()

if __name__ == "__main__":
    show_all_data()
