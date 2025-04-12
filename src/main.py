import os
from datetime import datetime
from typing import List, Dict
import random
from dotenv import load_dotenv

from .crawler.tiktok_crawler import TikTokCrawler
from .database.database import Database
from .database.models import (
    CrawlerAccount,
    FavoriteAccount,
    MovieDescRawData,
    MovieStatRawData
)
from .logger import setup_logger

logger = setup_logger(__name__)

def get_active_crawler_account(db: Database) -> CrawlerAccount:
    """アクティブなクローラーアカウントを取得"""
    query = """
        SELECT id, username, password, proxy, is_alive, last_crawled_at
        FROM crawler_accounts
        WHERE is_alive = TRUE
        ORDER BY last_crawled_at ASC NULLS FIRST
        LIMIT 1
    """
    cursor = db.execute_query(query)
    result = cursor.fetchone()
    if not result:
        raise ValueError("利用可能なクローラーアカウントが見つかりません")
    
    return CrawlerAccount(
        id=result[0],
        username=result[1],
        password=result[2],
        proxy=result[3],
        is_alive=result[4],
        last_crawled_at=result[5]
    )

def get_target_accounts(db: Database, limit: int = 5) -> List[FavoriteAccount]:
    """クロール対象のアカウントを取得"""
    query = """
        SELECT id, favorite_account_username, crawler_account_id,
               favorite_account_is_alive, crawl_priority, last_crawled_at
        FROM favorite_accounts
        WHERE favorite_account_is_alive = TRUE
        ORDER BY 
            CASE 
                WHEN last_crawled_at IS NULL THEN 1
                ELSE 0
            END DESC,
            crawl_priority DESC,
            last_crawled_at ASC
        LIMIT %s
    """
    cursor = db.execute_query(query, (limit,))
    results = cursor.fetchall()
    
    return [
        FavoriteAccount(
            id=row[0],
            favorite_account_username=row[1],
            crawler_account_id=row[2],
            favorite_account_is_alive=row[3],
            crawl_priority=row[4],
            last_crawled_at=row[5]
        )
        for row in results
    ]

def save_movie_desc(db: Database, data: Dict):
    """動画の基本情報を保存"""
    query = """
        INSERT INTO movie_desc_raw_data (
            id, url, account_username, account_nickname,
            title, posted_at_text, posted_at, crawled_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE
            account_username = VALUES(account_username),
            account_nickname = VALUES(account_nickname),
            title = VALUES(title),
            posted_at_text = VALUES(posted_at_text),
            posted_at = VALUES(posted_at),
            crawled_at = VALUES(crawled_at)
    """
    db.execute_query(
        query,
        (
            data["id"], data["url"], data["account_username"],
            data["account_nickname"], data["title"],
            data["posted_at_text"], data.get("posted_at"),
            datetime.now()
        )
    )

def save_movie_stat(db: Database, data: Dict):
    """動画の統計情報を保存"""
    query = """
        INSERT INTO movie_stat_raw_data (
            movie_id, play_count_text, play_count,
            like_count_text, like_count, crawled_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        )
    """
    db.execute_query(
        query,
        (
            data["id"], data.get("play_count_text"),
            data.get("play_count"), data.get("like_count_text"),
            data.get("like_count"), datetime.now()
        )
    )

def update_crawler_account(db: Database, account_id: int):
    """クローラーアカウントの最終クロール時刻を更新"""
    query = """
        UPDATE crawler_accounts
        SET last_crawled_at = %s
        WHERE id = %s
    """
    db.execute_query(query, (datetime.now(), account_id))

def update_favorite_account(db: Database, account_id: int):
    """お気に入りアカウントの最終クロール時刻を更新"""
    query = """
        UPDATE favorite_accounts
        SET last_crawled_at = %s
        WHERE id = %s
    """
    db.execute_query(query, (datetime.now(), account_id))

def main():
    """メイン処理"""
    load_dotenv()
    db = Database()
    
    try:
        # アクティブなクローラーアカウントを取得
        crawler_account = get_active_crawler_account(db)
        logger.info(f"クローラーアカウント {crawler_account.username} を使用します")
        
        # クローラーを初期化
        crawler = TikTokCrawler(
            username=crawler_account.username,
            password=crawler_account.password,
            proxy=crawler_account.proxy
        )
        crawler.start()
        
        # クロール対象のアカウントを取得
        target_accounts = get_target_accounts(db)
        logger.info(f"{len(target_accounts)}件のターゲットアカウントを取得しました")
        
        for target in target_accounts:
            try:
                # ユーザーページに移動
                if not crawler.navigate_to_user(target.favorite_account_username):
                    continue
                
                # 動画一覧を取得
                videos = crawler.get_user_videos()
                logger.info(f"{len(videos)}件の動画を見つけました")
                
                for video in videos:
                    try:
                        # 動画の詳細情報を取得
                        details = crawler.get_video_details(video["url"])
                        if not details:
                            continue
                            
                        # 基本情報と統計情報を結合
                        video_data = {
                            **video,
                            **details
                        }
                        
                        # データベースに保存
                        save_movie_desc(db, video_data)
                        save_movie_stat(db, video_data)
                        
                    except Exception as e:
                        logger.error(f"動画 {video['url']} の処理中にエラー: {e}")
                        continue
                
                # クロール完了を記録
                update_favorite_account(db, target.id)
                
            except Exception as e:
                logger.error(f"アカウント {target.favorite_account_username} の処理中にエラー: {e}")
                continue
            
        # クローラーアカウントの使用を記録
        update_crawler_account(db, crawler_account.id)
        
    except Exception as e:
        logger.error(f"クロール処理でエラーが発生: {e}")
        
    finally:
        if 'crawler' in locals():
            crawler.stop()

if __name__ == "__main__":
    main()
