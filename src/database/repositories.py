from datetime import datetime
from typing import List, Optional, Set
from .database import Database
from .models import CrawlerAccount, FavoriteAccount, VideoHeavyRawData, VideoLightRawData
from ..logger import setup_logger

logger = setup_logger(__name__)

class CrawlerAccountRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_an_available_crawler_account(self) -> Optional[CrawlerAccount]:
        """利用可能なクローラーアカウントを1つ取得(使ってない順)"""
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

    def save_video_heavy_data(self, data: VideoHeavyRawData):
        """動画の詳細情報を保存"""
        query = """
            INSERT INTO video_heavy_raw_data (
                video_id, video_url, video_thumbnail_url, video_title,
                creator_nickname, creator_unique_id, post_time_text, post_time,
                audio_info_text, audio_id, audio_title, audio_author_name,
                play_count_text, play_count, like_count_text, like_count,
                comment_count_text, comment_count, collect_count_text, collect_count,
                share_count_text, share_count, crawling_algorithm, crawled_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                video_url = VALUES(video_url),
                video_thumbnail_url = VALUES(video_thumbnail_url),
                video_title = VALUES(video_title),
                creator_nickname = VALUES(creator_nickname),
                creator_unique_id = VALUES(creator_unique_id),
                post_time_text = VALUES(post_time_text),
                post_time = VALUES(post_time),
                audio_info_text = VALUES(audio_info_text),
                audio_id = VALUES(audio_id),
                audio_title = VALUES(audio_title),
                audio_author_name = VALUES(audio_author_name),
                play_count_text = VALUES(play_count_text),
                play_count = VALUES(play_count),
                like_count_text = VALUES(like_count_text),
                like_count = VALUES(like_count),
                comment_count_text = VALUES(comment_count_text),
                comment_count = VALUES(comment_count),
                collect_count_text = VALUES(collect_count_text),
                collect_count = VALUES(collect_count),
                share_count_text = VALUES(share_count_text),
                share_count = VALUES(share_count),
                crawling_algorithm = VALUES(crawling_algorithm),
                crawled_at = VALUES(crawled_at)
        """
        self.db.execute_query(query, (
            data.video_id, data.video_url, data.video_thumbnail_url, data.video_title,
            data.creator_nickname, data.creator_unique_id, data.post_time_text, data.post_time,
            data.audio_info_text, data.audio_id, data.audio_title, data.audio_author_name,
            data.play_count_text, data.play_count, data.like_count_text, data.like_count,
            data.comment_count_text, data.comment_count, data.collect_count_text, data.collect_count,
            data.share_count_text, data.share_count, data.crawling_algorithm, data.crawled_at
        ))

    def save_video_light_data(self, data: VideoLightRawData):
        """動画の基本情報を保存"""
        query = """
            INSERT INTO video_light_raw_data (
                video_id, video_url, video_thumbnail_url, video_title,
                play_count_text, like_count_text, video_alt_info_text,
                crawling_algorithm, crawled_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                video_url = VALUES(video_url),
                video_thumbnail_url = VALUES(video_thumbnail_url),
                video_title = VALUES(video_title),
                play_count_text = VALUES(play_count_text),
                like_count_text = VALUES(like_count_text),
                video_alt_info_text = VALUES(video_alt_info_text),
                crawling_algorithm = VALUES(crawling_algorithm),
                crawled_at = VALUES(crawled_at)
        """
        self.db.execute_query(query, (
            data.video_id, data.video_url, data.video_thumbnail_url, data.video_title,
            data.play_count_text, data.like_count_text, data.video_alt_info_text,
            data.crawling_algorithm, data.crawled_at
        ))

    def get_existing_video_ids(self) -> Set[str]:
        """既存の動画IDを取得"""
        query = "SELECT video_id FROM video_heavy_raw_data UNION SELECT video_id FROM video_light_raw_data"
        cursor = self.db.execute_query(query)
        rows = cursor.fetchall()
        cursor.close()
        return {row[0] for row in rows}
