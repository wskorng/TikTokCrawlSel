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
class VideoDescRawData:
    id: int  # 自動採番
    video_id: str  # TikTokの動画IDそのまま
    url: str
    account_username: str
    account_nickname: str
    title: str
    posted_at_text: str
    posted_at: Optional[datetime] # パースできないかもしれないので
    crawled_at: datetime

@dataclass
class VideoPlayStatRawData:
    id: int # 自動採番
    video_id: str
    count_text: str # 表示形式のままの再生数
    count: Optional[int] # パース後の数値
    crawled_at: datetime

@dataclass
class VideoLikeStatRawData:
    id: int # 自動採番
    video_id: str
    count_text: str # 表示形式のままのいいね数
    count: Optional[int] # パース後の数値
    crawled_at: datetime
