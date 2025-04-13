import mysql.connector
from mysql.connector import Error
from ..config import DB_CONFIG
from ..logger import setup_logger

logger = setup_logger(__name__)

CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS crawler_accounts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        password VARCHAR(255) NOT NULL,
        proxy VARCHAR(255),
        is_alive BOOLEAN NOT NULL DEFAULT TRUE,
        last_crawled_at DATETIME,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_is_alive (is_alive),
        INDEX idx_last_crawled_at (last_crawled_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS favorite_accounts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        favorite_account_username VARCHAR(255) NOT NULL,
        crawler_account_id INT,
        favorite_account_is_alive BOOLEAN NOT NULL DEFAULT TRUE,
        crawl_priority INT NOT NULL DEFAULT 10,
        last_crawled_at DATETIME,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (crawler_account_id) REFERENCES crawler_accounts(id),
        INDEX idx_username (favorite_account_username),
        INDEX idx_crawler_account (crawler_account_id),
        INDEX idx_is_alive (favorite_account_is_alive),
        INDEX idx_priority_last_crawled (crawl_priority, last_crawled_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS video_desc_raw_data (
        id INT AUTO_INCREMENT PRIMARY KEY,  -- 自動採番
        video_id VARCHAR(255) NOT NULL UNIQUE,  -- TikTokの動画IDそのまま
        url TEXT NOT NULL,
        account_username VARCHAR(255) NOT NULL,
        account_nickname VARCHAR(255) NOT NULL,
        title TEXT NOT NULL,
        posted_at_text VARCHAR(255) NOT NULL,
        posted_at DATETIME,  -- パース失敗の可能性があるのでNULL許容
        crawled_at DATETIME NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_video_id (video_id),
        INDEX idx_account_username (account_username),
        INDEX idx_posted_at (posted_at),
        INDEX idx_crawled_at (crawled_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS video_play_stat_raw_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        video_id VARCHAR(255) NOT NULL,
        url TEXT NOT NULL,
        account_username VARCHAR(255) NOT NULL,
        count_text VARCHAR(255) NOT NULL,  -- 表示形式のままの再生数
        count INT,  -- パース後の数値
        crawled_at DATETIME NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_video_id (video_id),
        INDEX idx_account_username (account_username),
        INDEX idx_crawled_at (crawled_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS video_like_stat_raw_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        video_id VARCHAR(255) NOT NULL,
        url TEXT NOT NULL,
        account_username VARCHAR(255) NOT NULL,
        count_text VARCHAR(255) NOT NULL,  -- 表示形式のままのいいね数
        count INT,  -- パース後の数値
        crawled_at DATETIME NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_video_id (video_id),
        INDEX idx_account_username (account_username),
        INDEX idx_crawled_at (crawled_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
]

def create_database():
    """データベースを作成する"""
    try:
        # DB_CONFIGからdatabase設定を除外してコピー
        config = DB_CONFIG.copy()
        database_name = config.pop('database')
        
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # データベースが存在しない場合は作成
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name} "
                      f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.info(f"データベース {database_name} を作成しました")
        
    except Error as e:
        logger.error(f"データベース作成エラー: {e}")
        raise
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def create_tables():
    """テーブルを作成する"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        for create_table_sql in CREATE_TABLES_SQL:
            cursor.execute(create_table_sql)
            logger.info(f"テーブルを作成しました: {create_table_sql.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()}")
        
        conn.commit()
        logger.info("全てのテーブルの作成が完了しました")
        
    except Error as e:
        logger.error(f"テーブル作成エラー: {e}")
        raise
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def init_database():
    """データベースとテーブルを初期化する"""
    create_database()
    create_tables()

if __name__ == '__main__':
    init_database()
