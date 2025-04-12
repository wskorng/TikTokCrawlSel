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
class MovieDescRawData:
    id: str  # TikTokの動画IDそのまま
    url: str
    account_username: str
    account_nickname: str
    title: str
    posted_at_text: str
    posted_at: Optional[datetime] # パースできないかもしれないので
    crawled_at: datetime

@dataclass
class MovieStatRawData:
    id: int # 自動採番
    movie_id: str
    play_count_text: Optional[str] # 片方しかとれないかもしれないので
    play_count: Optional[int] # パースできないかもしれないので
    like_count_text: Optional[str] # 片方しかとれないかもしれないので
    like_count: Optional[int] # パースできないかもしれないので
    crawled_at: datetime
