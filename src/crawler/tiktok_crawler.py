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

from ..database.models import MovieDescRawData, MovieStatRawData
from .selenium_manager import SeleniumManager
from ..logger import setup_logger

logger = setup_logger(__name__)

class TikTokCrawler:
    BASE_URL = "https://www.tiktok.com"
    
    def __init__(self, username: str, password: str, proxy: Optional[str] = None):
        """
        TikTokクローラーの初期化
        
        Args:
            username: TikTokアカウントのユーザー名
            password: TikTokアカウントのパスワード
            proxy: プロキシ設定（オプション）
        """
        self.username = username
        self.password = password
        self.selenium_manager = SeleniumManager(proxy)
        self.driver = None
        self.wait = None
        
    def start(self):
        """クローラーを開始する"""
        try:
            self.driver = self.selenium_manager.setup_driver()
            self.wait = WebDriverWait(self.driver, 10)
            self._login()
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
            username_input.send_keys(self.username)
            self._random_sleep(1.5, 2.5)

            # パスワード入力欄を探す
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_input.send_keys(self.password)
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

    def navigate_to_user(self, username: str) -> bool:
        """
        指定したユーザーのプロフィールページに移動
        
        Args:
            username: 移動先のユーザー名
            
        Returns:
            bool: 移動に成功したかどうか
        """
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

    def get_user_videos(self, max_videos: int = 50) -> List[Dict]:
        """
        現在のユーザーページから動画情報を収集
        
        Args:
            max_videos: 収集する最大動画数
            
        Returns:
            List[Dict]: 収集した動画情報のリスト
        """
        videos = []
        try:
            # 動画要素を取得
            video_elements = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-e2e='user-post-item']"))
            )
            
            for video in video_elements[:max_videos]:
                try:
                    # 動画の基本情報を取得
                    video_link = video.find_element(By.TAG_NAME, "a")
                    video_url = video_link.get_attribute("href")
                    video_id = video_url.split("/")[-1]
                    
                    # 再生数を取得（表示形式のまま）
                    play_count_element = video.find_element(By.CSS_SELECTOR, "[data-e2e='video-views']")
                    play_count_text = play_count_element.text
                    
                    videos.append({
                        "url": video_url,
                        "id": video_id,
                        "play_count_text": play_count_text
                    })
                    
                except NoSuchElementException as e:
                    logger.warning(f"動画情報の取得に失敗: {e}")
                    continue
                    
            return videos
            
        except Exception as e:
            logger.error(f"動画一覧の取得に失敗: {e}")
            return []

    def get_video_details(self, video_url: str) -> Optional[Dict]:
        """
        個別の動画ページから詳細情報を収集
        
        Args:
            video_url: 動画のURL
            
        Returns:
            Optional[Dict]: 収集した動画の詳細情報
        """
        try:
            self.driver.get(video_url)
            self._random_sleep(2.0, 4.0)
            
            # 動画の詳細情報を待機
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='video-title']"))
            )
            
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
            
            # いいね数を取得
            like_count_text = self.driver.find_element(
                By.CSS_SELECTOR, "[data-e2e='like-count']"
            ).text
            
            return {
                "title": title,
                "posted_at_text": posted_at_text,
                "account_username": account_username,
                "account_nickname": account_nickname,
                "like_count_text": like_count_text
            }
            
        except Exception as e:
            logger.error(f"動画詳細の取得に失敗: {e}")
            return None

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
