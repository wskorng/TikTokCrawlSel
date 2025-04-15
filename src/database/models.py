from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class CrawlerAccount:
    id: int # 自動採番
    username: str
    password: str
    proxy: Optional[str] # 未設定かもしれないので
    is_alive: bool
    last_crawled_at: Optional[datetime] # 初めてかもしれないので

@dataclass
class FavoriteAccount:
    id: int # 自動採番
    favorite_account_username: str
    crawler_account_id: Optional[int] # 未割り当てかもしれないので
    favorite_account_is_alive: bool
    crawl_priority: int
    last_crawled_at: Optional[datetime] # 初めてかもしれないので

@dataclass
class VideoHeavyRawData:
    id: Optional[int] = None  # 自動採番
    video_id: str = ""  # TikTokの動画IDそのまま
    video_url: str = ""
    video_thumbnail_url: str = ""
    video_title: str = ""
    creator_nickname: str = ""
    creator_unique_id: str = ""
    post_time_text: str = ""
    post_time: Optional[datetime] = None  # パースできないかもしれない
    audio_url: Optional[str] = None
    audio_info_text: Optional[str] = None
    audio_id: Optional[str] = None
    audio_title: Optional[str] = None
    audio_author_name: Optional[str] = None
    play_count_text: str = ""
    play_count: Optional[int] = None
    like_count_text: str = ""
    like_count: Optional[int] = None
    comment_count_text: Optional[str] = None
    comment_count: Optional[int] = None
    collect_count_text: Optional[str] = None
    collect_count: Optional[int] = None
    share_count_text: Optional[str] = None
    share_count: Optional[int] = None
    crawling_algorithm: str = ""
    crawled_at: datetime = datetime.now()

@dataclass
class VideoLightRawData:
    id: Optional[int] = None  # 自動採番
    video_url: str = ""
    video_id: str = ""  # TikTokの動画IDそのまま
    account_username: str = ""  # 動画を投稿したアカウントのユーザー名
    video_thumbnail_url: str = ""
    video_alt_info_text: str = ""  # {audio_author_name}の{audio_title}を使用して{account_nickname}が作成した{video_title}
    play_count_text: Optional[str] = None
    play_count: Optional[int] = None
    like_count_text: Optional[str] = None
    like_count: Optional[int] = None
    crawling_algorithm: str = ""
    crawled_at: datetime = datetime.now()
