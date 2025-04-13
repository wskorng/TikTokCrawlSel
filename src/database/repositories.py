from datetime import datetime
from typing import List, Optional, Set
from .database import Database
from .models import CrawlerAccount, FavoriteAccount, VideoDescRawData, VideoPlayStatRawData, VideoLikeStatRawData
from ..logger import setup_logger

logger = setup_logger(__name__)

class CrawlerAccountRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_an_available_crawler_account(self) -> Optional[CrawlerAccount]:
        """利用可能なクローラーアカウントを取得"""
        query = """
            SELECT id, username, password, proxy, is_alive, last_crawled_at
            FROM crawler_accounts
            WHERE is_alive = TRUE
            ORDER BY 
                CASE 
                    WHEN last_crawled_at IS NULL THEN 1
                    ELSE 0
                END DESC,
                last_crawled_at ASC
            LIMIT 1
        """
        cursor = self.db.execute_query(query)
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return None

        return CrawlerAccount(
            id=row[0],
            username=row[1],
            password=row[2],
            proxy=row[3],
            is_alive=row[4],
            last_crawled_at=row[5]
        )

    def update_crawler_account_last_crawled(self, crawler_account_id: int, last_crawled_at: datetime):
        """クローラーアカウントの最終クロール時間を更新"""
        query = """
            UPDATE crawler_accounts
            SET last_crawled_at = %s
            WHERE id = %s
        """
        self.db.execute_query(query, (last_crawled_at, crawler_account_id))


class FavoriteAccountRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_favorite_accounts(self, crawler_account_id: int, limit: int = 10) -> List[FavoriteAccount]:
        """クロール対象のお気に入りアカウントを取得"""
        query = """
            SELECT id, favorite_account_username, crawler_account_id,
                   favorite_account_is_alive, crawl_priority, last_crawled_at
            FROM favorite_accounts
            WHERE crawler_account_id = %s
            AND favorite_account_is_alive = TRUE
            ORDER BY 
                CASE 
                    WHEN last_crawled_at IS NULL THEN 1
                    ELSE 0
                END DESC,
                crawl_priority DESC,
                last_crawled_at ASC
            LIMIT %s
        """
        cursor = self.db.execute_query(query, (crawler_account_id, limit))
        rows = cursor.fetchall()
        cursor.close()

        return [
            FavoriteAccount(
                id=row[0],
                favorite_account_username=row[1],
                crawler_account_id=row[2],
                favorite_account_is_alive=row[3],
                crawl_priority=row[4],
                last_crawled_at=row[5]
            )
            for row in rows
        ]

    def update_favorite_account_last_crawled(self, username: str, last_crawled_at: datetime):
        """お気に入りアカウントの最終クロール時間を更新"""
        query = """
            UPDATE favorite_accounts
            SET last_crawled_at = %s
            WHERE favorite_account_username = %s
        """
        self.db.execute_query(query, (last_crawled_at, username))


class VideoRepository:
    def __init__(self, db: Database):
        self.db = db

    def save_video_description(self, desc: VideoDescRawData):
        """動画の説明データを保存"""
        query = """
            INSERT INTO video_desc_raw_data (
                video_id, url, account_username, account_nickname,
                title, posted_at_text, posted_at, crawled_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                url = VALUES(url),
                account_username = VALUES(account_username),
                account_nickname = VALUES(account_nickname),
                title = VALUES(title),
                posted_at_text = VALUES(posted_at_text),
                posted_at = VALUES(posted_at),
                crawled_at = VALUES(crawled_at)
        """
        self.db.execute_query(query, (
            desc.video_id, desc.url, desc.account_username, desc.account_nickname,
            desc.title, desc.posted_at_text, desc.posted_at, desc.crawled_at
        ))

    def save_video_play_stats(self, stats: VideoPlayStatRawData):
        """動画の再生数データを保存"""
        query = """
            INSERT INTO video_play_stat_raw_data (
                video_id, count_text, count, crawled_at
            ) VALUES (%s, %s, %s, %s)
        """
        self.db.execute_query(query, (
            stats.video_id, stats.count_text, stats.count, stats.crawled_at
        ))

    def save_video_like_stats(self, stats: VideoLikeStatRawData):
        """動画のいいね数データを保存"""
        query = """
            INSERT INTO video_like_stat_raw_data (
                video_id, count_text, count, crawled_at
            ) VALUES (%s, %s, %s, %s)
        """
        self.db.execute_query(query, (
            stats.video_id, stats.count_text, stats.count, stats.crawled_at
        ))

    def get_existing_video_ids(self) -> Set[str]:
        """既存の動画IDを取得"""
        query = "SELECT video_id FROM video_desc_raw_data"
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        cursor.close()
        return {row[0] for row in rows}
