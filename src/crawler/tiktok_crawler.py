from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import random
import time
from typing import Optional, List, Dict

from ..database.models import VideoDescRawData, VideoStatRawData, CrawlerAccount, FavoriteAccount
from ..database.repositories import CrawlerAccountRepository, FavoriteAccountRepository, VideoRepository
from .selenium_manager import SeleniumManager
from ..logger import setup_logger

logger = setup_logger(__name__)

class TikTokCrawler:
    BASE_URL = "https://www.tiktok.com"
    
    def __init__(self, crawler_account_repo: CrawlerAccountRepository,
                 favorite_account_repo: FavoriteAccountRepository,
                 video_repo: VideoRepository):
        """
        TikTokクローラーの初期化
        
        Args:
            crawler_account_repo: クローラーアカウントリポジトリ
            favorite_account_repo: お気に入りアカウントリポジトリ
            video_repo: 動画リポジトリ
        """
        self.crawler_account_repo = crawler_account_repo
        self.favorite_account_repo = favorite_account_repo
        self.video_repo = video_repo
        self.crawler_account: Optional[CrawlerAccount] = None
        self.selenium_manager = None
        self.driver = None
        self.wait = None
        
    def start(self):
        """クローラーを開始する"""
        try:
            # 利用可能なクローラーアカウントを取得
            self.crawler_account = self.crawler_account_repo.get_an_available_crawler_account()
            if not self.crawler_account:
                raise Exception("利用可能なクローラーアカウントが見つかりません")

            # Seleniumの設定
            self.selenium_manager = SeleniumManager(self.crawler_account.proxy)
            self.driver = self.selenium_manager.setup_driver()
            self.wait = WebDriverWait(self.driver, 60)  # タイムアウトを60秒に変更

            # ログイン
            self._login()

            # 最終クロール時間を更新
            self.crawler_account_repo.update_crawler_account_last_crawled(
                self.crawler_account.id,
                datetime.now()
            )
        except Exception as e:
            logger.error(f"クローラーの開始に失敗: {e}")
            self.stop()
            raise

    def stop(self):
        """クローラーを停止する"""
        if self.selenium_manager:
            self.selenium_manager.quit_driver()
            
    def _random_sleep(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """
        ランダムな時間待機して人間らしい動きをシミュレート
        
        Args:
            min_seconds: 最小待機時間（秒）
            max_seconds: 最大待機時間（秒）
        """
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _login(self):
        """TikTokにログインする"""
        try:
            logger.info("TikTokにログインを試みます")
            self.driver.get(f"{self.BASE_URL}/login/phone-or-email/email")
            self._random_sleep(2.0, 4.0)

            # ログインフォームの要素を待機
            username_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']"))
            )
            self._random_sleep(1.0, 2.0)

            # メールアドレスを入力
            username_input.send_keys(self.crawler_account.username)
            self._random_sleep(1.5, 2.5)

            # パスワード入力欄を探す
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_input.send_keys(self.crawler_account.password)
            self._random_sleep(1.0, 2.0)

            # ログインボタンを探してクリック
            login_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            self._random_sleep(1.0, 2.0)
            login_button.click()

            # ログイン完了を待機
            # プロフィールアイコンが表示されるまで待機
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='profile-icon']"))
            )
            logger.info("ログインに成功しました")

        except Exception as e:
            logger.error(f"ログインに失敗: {e}")
            raise

    def navigate_to_user_page(self, username: str) -> bool:
        try:
            self.driver.get(f"{self.BASE_URL}/@{username}")
            self._random_sleep(2.0, 4.0)
            
            # ユーザーページの読み込みを確認
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='user-post-item']"))
            )
            return True
            
        except Exception as e:
            logger.error(f"ユーザー {username} のページへの移動に失敗: {e}")
            return False

    def get_like_stats_from_user_page(self, max_videos: int = 50) -> List[Dict]:
        video_stats = []
        try:
            # 動画要素を取得
            video_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-e2e='user-post-item']"))
            )
            
            for video_element in video_elements[:max_videos]:
                try:
                    # 動画の基本情報を取得
                    video_link = video_element.find_element(By.TAG_NAME, "a")
                    video_url = video_link.get_attribute("href")
                    video_id = video_url.split("/")[-1]
                    
                    # いいね数を取得（表示形式のまま）
                    like_count_element = video_element.find_element(By.CSS_SELECTOR, "[data-e2e='video-views']") # video-viewsといいながらいいね数なんだよな
                    like_count_text = like_count_element.text
                    
                    video_stats.append({
                        "url": video_url,
                        "like_count_text": like_count_text
                    })
                    
                except NoSuchElementException as e:
                    logger.warning(f"動画情報の取得に失敗: {e}")
                    continue
                    
            return video_stats
            
        except Exception as e:
            logger.error(f"動画一覧の取得に失敗: {e}")
            return []

    def navigate_to_video_page(self, video_url: str) -> bool:
        try:
            self.driver.get(video_url)
            self._random_sleep(2.0, 4.0)
            
            # 動画の詳細情報を待機
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='video-title']"))
            )
            return True
            
        except Exception as e:
            logger.error(f"動画ページへの移動に失敗: {e}")
            return False

    def get_desc_from_video_page(self) -> Optional[Dict]:
        """動画ページから説明データを取得"""
        try:
            # タイトルを取得
            title = self.driver.find_element(
                By.CSS_SELECTOR, "[data-e2e='video-title']"
            ).text
            
            # 投稿日時を取得
            posted_at_text = self.driver.find_element(
                By.CSS_SELECTOR, "[data-e2e='browser-nickname'] + span"
            ).text
            
            # アカウント情報を取得
            account_username = self.driver.find_element(
                By.CSS_SELECTOR, "[data-e2e='browser-nickname']"
            ).text
            account_nickname = self.driver.find_element(
                By.CSS_SELECTOR, "[data-e2e='user-title']"
            ).text

            return {
                "title": title,
                "posted_at_text": posted_at_text,
                "account_username": account_username,
                "account_nickname": account_nickname,
                "url": self.driver.current_url,
                "id": self.driver.current_url.split("/")[-1]
            }

        except Exception as e:
            logger.error(f"動画説明の取得に失敗: {e}")
            return None

    def save_video_desc(self, desc_data: Dict):
        """動画の説明データを保存"""
        try:
            desc = VideoDescRawData(
                id=desc_data["id"],
                url=desc_data["url"],
                account_username=desc_data["account_username"],
                account_nickname=desc_data["account_nickname"],
                title=desc_data["title"],
                posted_at_text=desc_data["posted_at_text"],
                posted_at=None,  # TODO: posted_at_textのパース処理を実装
                crawled_at=datetime.now()
            )
            self.video_repo.save_video_description(desc)
            return True
        except Exception as e:
            logger.error(f"動画説明の保存に失敗: {e}")
            return False
    
    def navigate_to_video_page_creator_videos_tab(self) -> bool:
        # 「クリエイターの動画」タブをクリック
        try:
            # タブを待機
            tab = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='creator-videos-tab']"))
            )
            tab.click()
            self._random_sleep(1.0, 2.0)
            return True
            
        except Exception as e:
            logger.error(f"クリエイターの動画タブへの移動に失敗: {e}")
            return False

    def get_play_stats_from_video_page_creator_videos_tab(self, max_videos: int = 30) -> Optional[Dict]:
        video_stats = []
        try:
            # 動画要素を取得
            video_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-e2e='user-post-item']"))
            )
            
            for video_element in video_elements[:max_videos]:
                try:
                    # 動画の基本情報を取得
                    video_link = video_element.find_element(By.TAG_NAME, "a")
                    video_url = video_link.get_attribute("href")
                    video_id = video_url.split("/")[-1]
                    
                    # 再生数を取得（表示形式のまま）
                    play_count_element = video_element.find_element(By.CSS_SELECTOR, "[data-e2e='video-views']")
                    play_count_text = play_count_element.text
                    
                    video_stats.append({
                        "url": video_url,
                        "play_count_text": play_count_text
                    })
                    
                except NoSuchElementException as e:
                    logger.warning(f"動画情報の取得に失敗: {e}")
                    continue
                    
            return video_stats
            
        except Exception as e:
            logger.error(f"動画一覧の取得に失敗: {e}")
            return []

    def scroll_page(self, scroll_count: int = 3):
        """
        ページをスクロールして追加コンテンツを読み込む
        
        Args:
            scroll_count: スクロールする回数
        """
        try:
            for _ in range(scroll_count):
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                self._random_sleep(1.0, 2.0)
                
        except Exception as e:
            logger.error(f"ページのスクロールに失敗: {e}")

    def save_video_stats(self, video_like_stats: List[Dict], video_play_stats: List[Dict]):
        try:
            for video_like_stat, video_play_stat in zip(video_like_stats, video_play_stats):
                video_stat = VideoStat(
                    id=video_play_stat["url"].split("/")[-1],
                    url=video_play_stat["url"],
                    like_count_text=video_like_stat["like_count_text"],
                    play_count_text=video_play_stat["play_count_text"],
                    crawled_at=datetime.now()
                )
                self.video_repo.save_video_stat(video_stat)
        except Exception as e:
            logger.error(f"動画統計の保存に失敗: {e}")

    def crawl_about_favorite_accounts(self, max_accounts: int = 10, max_videos_per_account: int = 50):
        try:
            # クロール対象のお気に入りアカウントを取得
            favorite_accounts = self.favorite_account_repo.get_favorite_accounts(
                self.crawler_account.id,
                limit=max_accounts
            )

            if not favorite_accounts:
                logger.info("クロール対象のアカウントが見つかりません")
                return

            # 既存の動画IDを取得（重複チェック用）
            existing_video_ids = self.video_repo.get_existing_video_ids()

            # 各アカウントの動画をクロール
            for account in favorite_accounts:
                try:
                    logger.info(f"アカウント {account.favorite_account_username} のクロールを開始")

                    # アカウントページに移動
                    if not self.navigate_to_user(account.favorite_account_username):
                        continue
                    self.scroll_page(3)
                    video_like_stats = self.get_like_stats_from_user_page(max_videos_per_account)
                    if not video_like_stats:
                        continue

                    # 動画ページに移動
                    if not self.navigate_to_video_page(video_like_stats[0]["url"]):
                        continue
                    video_desc = self.get_desc_from_video_page()
                    if not video_desc:
                        continue
                    self.save_video_desc(video_desc)

                    # 動画ページの「クリエイターの動画」タブに移動
                    if not self.navigate_to_video_page_creator_videos_tab():
                        continue
                    self.scroll_page(3)
                    video_play_stats = self.get_play_stats_from_video_page_creator_videos_tab(max_videos_per_account)
                    if not video_play_stats:
                        continue

                    # アカウントの最終クロール時間を更新
                    self.favorite_account_repo.update_favorite_account_last_crawled(
                        account.favorite_account_username,
                        datetime.now()
                    )

                except Exception as e:
                    logger.error(f"アカウント {account.favorite_account_username} のクロール中にエラー: {e}")
                    continue

        except Exception as e:
            logger.error(f"クロール処理でエラー: {e}")
            raise


def main():
    try:
        # データベース接続の初期化
        db = Database()
        
        # 各リポジトリの初期化
        crawler_account_repo = CrawlerAccountRepository(db)
        favorite_account_repo = FavoriteAccountRepository(db)
        video_repo = VideoRepository(db)
        
        # クローラーの初期化
        crawler = TikTokCrawler(
            crawler_account_repo=crawler_account_repo,
            favorite_account_repo=favorite_account_repo,
            video_repo=video_repo
        )
        
        try:
            # クローラーを開始（Selenium初期化とログイン）
            crawler.start()
            
            # お気に入りアカウントのクロール
            crawler.crawl_about_favorite_accounts()
            
        finally:
            # クローラーの停止（Seleniumのクリーンアップ）
            crawler.stop()
            
    except Exception as e:
        logger.error(f"メイン処理でエラー: {e}")
        raise
    
    finally:
        # データベース接続のクリーンアップ
        db.close()


if __name__ == "__main__":
    main()
