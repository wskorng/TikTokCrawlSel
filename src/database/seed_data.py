from datetime import datetime
from typing import List
from .database import Database
from ..logger import setup_logger
from dotenv import load_dotenv

logger = setup_logger(__name__)

def insert_crawler_accounts(db: Database) -> List[int]:
    """クローラーアカウントのテストデータを投入"""
    crawler_accounts = [
        {
            "username": "wskorng+01@gmail.com",
            "password": "<gitwn2%W$j?H93",
            "proxy": None,
            "is_alive": True
        }
    ]
    
    crawler_account_ids = []
    for crawler_account in crawler_accounts:
        query = """
            INSERT INTO crawler_accounts (
                username, password, proxy, is_alive
            ) VALUES (
                %s, %s, %s, %s
            )
        """
        cursor = db.execute_query(
            query,
            (
                crawler_account["username"],
                crawler_account["password"],
                crawler_account["proxy"],
                crawler_account["is_alive"]
            )
        )
        crawler_account_ids.append(cursor.lastrowid)
        logger.info(f"クローラーアカウント {crawler_account['username']} を追加しました")
    
    return crawler_account_ids

def insert_favorite_accounts(db: Database, crawler_account_id: int):
    """お気に入りアカウントのテストデータを投入"""
    accounts = [
        {
            "username": "tiktok",  # TikTok公式
            "priority": 100
        },
        {
            "username": "gordonramsayofficial",  # ゴードン・ラムゼイ
            "priority": 90
        },
        {
            "username": "zachking",  # Zach King
            "priority": 80
        },
        {
            "username": "charlidamelio",  # Charli D'Amelio
            "priority": 70
        },
        {
            "username": "willsmith",  # Will Smith
            "priority": 60
        }
    ]
    
    for account in accounts:
        query = """
            INSERT INTO favorite_accounts (
                favorite_account_username,
                crawler_account_id,
                favorite_account_is_alive,
                crawl_priority
            ) VALUES (
                %s, %s, %s, %s
            )
        """
        db.execute_query(
            query,
            (
                account["username"],
                crawler_account_id,
                True,
                account["priority"]
            )
        )
        logger.info(f"お気に入りアカウント {account['username']} を追加しました（クローラーアカウントID: {crawler_account_id}）")

def insert_sample_video_data(db: Database):
    """サンプルの動画データを投入"""
    # 動画の基本情報
    desc_data = {
        "id": "7460937381265411370",
        "url": "https://www.tiktok.com/@tiktok/video/7460937381265411370",
        "account_username": "tiktok",
        "account_nickname": "TikTok",
        "title": "Our response to the Supreme Court decision.",
        "posted_at_text": "2024-01-18",
        "posted_at": datetime(2024, 1, 18),
        "crawled_at": datetime.now()
    }
    
    query = """
        INSERT INTO video_desc_raw_data (
            id, url, account_username, account_nickname,
            title, posted_at_text, posted_at, crawled_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    db.execute_query(
        query,
        (
            desc_data["id"],
            desc_data["url"],
            desc_data["account_username"],
            desc_data["account_nickname"],
            desc_data["title"],
            desc_data["posted_at_text"],
            desc_data["posted_at"],
            desc_data["crawled_at"]
        )
    )
    logger.info(f"サンプル動画データ {desc_data['id']} を追加しました")
    
    # 動画の再生数の統計情報
    play_stat_data = {
        "video_id": desc_data["id"],
        "count_text": "15.8M",
        "count": 15800000,
        "crawled_at": datetime.now()
    }
    
    query = """
        INSERT INTO video_play_stat_raw_data (
            video_id, count_text, count, crawled_at
        ) VALUES (
            %s, %s, %s, %s
        )
    """
    db.execute_query(
        query,
        (
            play_stat_data["video_id"],
            play_stat_data["count_text"],
            play_stat_data["count"],
            play_stat_data["crawled_at"]
        )
    )
    logger.info(f"サンプル再生数統計データを追加しました")

    # 動画のいいね数の統計情報
    like_stat_data = {
        "video_id": desc_data["id"],
        "count_text": "394.7K",
        "count": 394700,
        "crawled_at": datetime.now()
    }
    
    query = """
        INSERT INTO video_like_stat_raw_data (
            video_id, count_text, count, crawled_at
        ) VALUES (
            %s, %s, %s, %s
        )
    """
    db.execute_query(
        query,
        (
            like_stat_data["video_id"],
            like_stat_data["count_text"],
            like_stat_data["count"],
            like_stat_data["crawled_at"]
        )
    )
    logger.info(f"サンプルいいね数統計データを追加しました")




def main():
    """テストデータの投入を実行"""
    load_dotenv()
    db = Database()
    
    try:
        logger.info("テストデータの投入を開始します")
        
        # クローラーアカウントの投入
        crawler_account_ids = insert_crawler_accounts(db)
        if not crawler_account_ids:
            raise ValueError("クローラーアカウントの投入に失敗しました")
        
        # お気に入りアカウントの投入（最初のクローラーアカウントに紐付け）
        insert_favorite_accounts(db, crawler_account_ids[0])
        
        # サンプル動画データの投入
        insert_sample_video_data(db)
        
        logger.info("テストデータの投入が完了しました")
        
    except Exception as e:
        logger.error(f"テストデータの投入中にエラーが発生: {e}")
        raise
    finally:
        db.disconnect()

if __name__ == "__main__":
    main()
