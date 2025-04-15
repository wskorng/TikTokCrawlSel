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
    # 重いデータ（詳細情報）
    heavy_data = {
        "video_id": "7460937381265411370",
        "video_url": "https://www.tiktok.com/@tiktok/video/7460937381265411370",
        "account_username": "tiktok",
        "account_nickname": "TikTok",
        "video_thumbnail_url": "https://p16-sign-va.tiktokcdn.com/obj/tos-maliva-p-0068/oQC3BSkCEfDFLKAEbAEQgANNBAKPDYwAfC7bAa",
        "video_title": "Our response to the Supreme Court decision.",
        "post_time_text": "2024-01-18",
        "post_time": datetime(2024, 1, 18),
        "audio_info_text": "Original Sound - TikTok",
        "audio_id": "7460937394724155178",
        "audio_title": "Original Sound",
        "audio_author_name": "TikTok",
        "play_count_text": "15.8M",
        "play_count": 15800000,
        "like_count_text": "394.7K",
        "like_count": 394700,
        "comment_count_text": "10.2K",
        "comment_count": 10200,
        "collect_count_text": "5.1K",
        "collect_count": 5100,
        "share_count_text": "2.3K",
        "share_count": 2300,
        "crawled_at": datetime.now(),
        "crawling_algorithm": "selenium-human-like-1"
    }
    
    query = """
        INSERT INTO video_heavy_raw_data (
            video_id, video_url, account_username, account_nickname,
            video_thumbnail_url, video_title, post_time_text, post_time,
            audio_info_text, audio_id, audio_title, audio_author_name,
            play_count_text, play_count, like_count_text, like_count,
            comment_count_text, comment_count, collect_count_text, collect_count,
            share_count_text, share_count, crawled_at, crawling_algorithm
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    db.execute_query(
        query,
        (
            heavy_data["video_id"],
            heavy_data["video_url"],
            heavy_data["account_username"],
            heavy_data["account_nickname"],
            heavy_data["video_thumbnail_url"],
            heavy_data["video_title"],
            heavy_data["post_time_text"],
            heavy_data["post_time"],
            heavy_data["audio_info_text"],
            heavy_data["audio_id"],
            heavy_data["audio_title"],
            heavy_data["audio_author_name"],
            heavy_data["play_count_text"],
            heavy_data["play_count"],
            heavy_data["like_count_text"],
            heavy_data["like_count"],
            heavy_data["comment_count_text"],
            heavy_data["comment_count"],
            heavy_data["collect_count_text"],
            heavy_data["collect_count"],
            heavy_data["share_count_text"],
            heavy_data["share_count"],
            heavy_data["crawled_at"],
            heavy_data["crawling_algorithm"]
        )
    )
    logger.info(f"サンプル重いデータ {heavy_data['video_id']} を追加しました")
    
    # 軽いデータ（基本情報）
    light_data = {
        "video_id": heavy_data["video_id"],
        "video_url": heavy_data["video_url"],
        "account_username": heavy_data["account_username"],
        "video_thumbnail_url": heavy_data["video_thumbnail_url"],
        "video_alt_info_text": f"{heavy_data['audio_author_name']}の{heavy_data['audio_title']}を使用して{heavy_data['account_nickname']}が作成した{heavy_data['video_title']}",
        "play_count_text": heavy_data["play_count_text"],
        "play_count": heavy_data["play_count"],
        "like_count_text": heavy_data["like_count_text"],
        "like_count": heavy_data["like_count"],
        "crawled_at": datetime.now(),
        "crawling_algorithm": "selenium-human-like-1"
    }
    
    query = """
        INSERT INTO video_light_raw_data (
            video_id, video_url, account_username, video_thumbnail_url,
            video_alt_info_text, play_count_text, play_count,
            like_count_text, like_count, crawled_at, crawling_algorithm
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    db.execute_query(
        query,
        (
            light_data["video_id"],
            light_data["video_url"],
            light_data["account_username"],
            light_data["video_thumbnail_url"],
            light_data["video_alt_info_text"],
            light_data["play_count_text"],
            light_data["play_count"],
            light_data["like_count_text"],
            light_data["like_count"],
            light_data["crawled_at"],
            light_data["crawling_algorithm"]
        )
    )
    logger.info(f"サンプル軽いデータを追加しました")




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
