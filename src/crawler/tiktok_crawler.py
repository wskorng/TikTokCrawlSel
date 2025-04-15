from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timedelta
import random
import time
from typing import Optional, List, Dict, Tuple

from ..database.models import CrawlerAccount, FavoriteUser, VideoHeavyRawData, VideoLightRawData
from ..database.repositories import CrawlerAccountRepository, FavoriteUserRepository, VideoRepository
from ..database.database import Database
from .selenium_manager import SeleniumManager
from ..logger import setup_logger

logger = setup_logger(__name__)


def extract_thumbnail_essence(thumbnail_url: str) -> str:
    """サムネイルURLから一意な識別子を抽出する
    例: https://p19-sign.tiktokcdn-us.com/obj/tos-useast5-p-0068-tx/oMnASW5J5CYEMAiRxDhIPnOAAfE1gGfD1UiBia?lk3s=81f88b70&...
    → oMnASW5J5CYEMAiRxDhIPnOAAfE1gGfD1UiBia
    """
    try:
        path = thumbnail_url.split("?")[0]
        file_name = path.split("/")[-1]
        file_name = file_name.split(".")[0]
        file_name = file_name.split("~")[0]
        return file_name
    except Exception:
        logger.warning(f"サムネイルURLからエッセンスの抽出に失敗: {thumbnail_url}", exc_info=True)
        return thumbnail_url  # 失敗した場合は元のURLを返す


def parse_tiktok_time(time_text: str, base_time: datetime) -> Optional[datetime]:
    """投稿時間のテキストを解析する
    
    Args:
        time_text: 解析する時間文字列 (e.g. "3-25", "1日前", "2時間前")
        base_time: 基準となる時刻
    
    Returns:
        解析結果の日時。解析できない場合はNone。
    """
    if not time_text:
        return None

    try:
        if time_text.endswith("秒前"):
            seconds = int(time_text.replace("秒前", ""))
            return base_time - timedelta(seconds=seconds)

        if time_text.endswith("分前"):
            minutes = int(time_text.replace("分前", ""))
            return base_time - timedelta(minutes=minutes)

        if time_text.endswith("時間前"):
            hours = int(time_text.replace("時間前", ""))
            return base_time - timedelta(hours=hours)

        if time_text.endswith("日前"):
            days = int(time_text.replace("日前", ""))
            return base_time - timedelta(days=days)

        # 「M-D」形式の場合
        if "-" in time_text and len(time_text.split("-")) == 2:
            month, day = map(int, time_text.split("-"))
            year = base_time.year
            # 月が現在より大きい場合は前年と判断
            if month > base_time.month:
                year -= 1
            return datetime(year, month, day,
                          base_time.hour, base_time.minute,
                          tzinfo=base_time.tzinfo)

        # 「YYYY-MM-DD」形式の場合
        if "-" in time_text and len(time_text.split("-")) == 3:
            year, month, day = map(int, time_text.split("-"))
            return datetime(year, month, day,
                          base_time.hour, base_time.minute,
                          tzinfo=base_time.tzinfo)

        return None

    except:
        logger.warning(f"日付文字列の解析に失敗: {time_text}", exc_info=True)
        return None


def parse_tiktok_video_url(url: str) -> Tuple[str, str]: # NOT NULL なのでエラー起きたらエラー投げる
    """TikTokのURLからvideo_idとuser_usernameを抽出する
    
    Args:
        url: 解析するURL (e.g. "https://www.tiktok.com/@username/video/1234567890")
    
    Returns:
        (video_id, user_username)のタプル。
        例: ("1234567890", "username")
    """
    try:
        path = url.split("?")[0]
        parts = path.split("/")
        video_id = parts[-1]
        user_username = parts[-3].strip("@")
        return video_id, user_username
    
    except Exception:
        logger.exception(f"URLの解析に失敗: {url}")
        raise


def parse_tiktok_number(text: str) -> Optional[int]:
    """TikTok形式の数値文字列を解析する
    
    Args:
        text: 解析する文字列 (e.g. "1,234", "1.5K", "3.78M")
    
    Returns:
        解析結果の整数値。解析できない場合はNone。
        "1,234" -> 1234
        "1.5K" -> 1500
        "3.78M" -> 3780000
    """
    if not text:
        return None

    try:
        # カンマを削除
        text = text.replace(",", "")

        # 単位がない場合はそのまま整数変換
        if text.replace(".", "").isdigit():
            return int(float(text))

        # 単位ごとの倍率
        multipliers = {
            "K": 1000,       # 千
            "M": 1000000,    # 百万
            "G": 1000000000, # 十億
            "B": 1000000000  # 十億
        }

        # 最後の文字を単位として取得
        unit = text[-1].upper()
        if unit in multipliers:
            # 数値部分を取得して浮動小数点に変換
            number = float(text[:-1])
            # 倍率をかけて整数化
            return int(number * multipliers[unit])
        
        raise ValueError(f"数値文字列の解析に失敗: {text}")

    except:
        logger.warning(f"数値文字列の解析に失敗: {text}")
        return None


class TikTokCrawler:
    BASE_URL = "https://www.tiktok.com"
    
    def __init__(self, crawler_account_repo: CrawlerAccountRepository,
                 favorite_user_repo: FavoriteUserRepository,
                 video_repo: VideoRepository):
        """
        TikTokクローラーの初期化
        
        Args:
            crawler_account_repo: クローラーアカウントリポジトリ
            favorite_user_repo: お気に入りアカウントリポジトリ
            video_repo: 動画リポジトリ
        """
        self.crawler_account_repo = crawler_account_repo
        self.favorite_user_repo = favorite_user_repo
        self.video_repo = video_repo
        self.crawler_account: Optional[CrawlerAccount] = None
        self.selenium_manager = None
        self.driver = None
        self.wait = None
        
    def start(self, crawler_account_id: Optional[int] = None): # crawler_account_id が None なら適当に持ってくる
        # クローラーアカウントを取得
        if crawler_account_id is not None:
            self.crawler_account = self.crawler_account_repo.get_crawler_account_by_id(crawler_account_id)
            if not self.crawler_account:
                raise Exception(f"指定されたクローラーアカウント（ID: {crawler_account_id}）が見つかりません")
        else:
            self.crawler_account = self.crawler_account_repo.get_an_available_crawler_account()
            if not self.crawler_account:
                raise Exception("利用可能なクローラーアカウントがありません")

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

    def stop(self):
        if self.selenium_manager:
            self.selenium_manager.quit_driver()
            
    def _random_sleep(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        time.sleep(random.uniform(min_seconds, max_seconds))

    def scroll_page(self, scroll_count: int = 3):
        """Window全体をスクロールする"""
        try:
            for _ in range(scroll_count):
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                self._random_sleep(3.0, 4.0) # TODO ここちゃんと画像表示をwaitすればthumbnail問題治るんじゃね
                
        except Exception:
            logger.exception(f"ページのスクロールに失敗")
            raise
    
    def scroll_element(self, element_selector: str, scroll_count: int = 3):
        """特定の要素内をスクロールする"""
        try:
            for _ in range(scroll_count):
                # 要素を取得
                element = self.driver.find_element(By.CSS_SELECTOR, element_selector)
                
                # 要素の現在の高さを取得
                current_height = self.driver.execute_script(
                    "return arguments[0].scrollHeight;",
                    element
                )
                
                # 要素を下にスクロール
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight;",
                    element
                )
                
                # スクロール後に少し待機
                self._random_sleep(2.0, 3.0)
                
                # 新しい高さを取得
                new_height = self.driver.execute_script(
                    "return arguments[0].scrollHeight;",
                    element
                )
                
                # 高さが変わっていない場合は、もうスクロールできない
                if new_height == current_height:
                    break
                    
        except Exception:
            logger.exception(f"要素のスクロールに失敗: {element_selector}")
            raise

    def _login(self): # TikTokにログインする
        logger.info("TikTokにログイン中...")
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


    class UserNotFoundException(Exception):
        """ユーザーが見つからない（アカウントが削除されている等）場合の例外"""
        pass

    def navigate_to_user_page(self, username: str):
        logger.debug(f"ユーザー @{username} のページに移動中...")
        self.driver.get(f"{self.BASE_URL}/@{username}")
        self._random_sleep(2.0, 4.0)

        # まずページのタイトルを確認
        title = self.driver.title
        if title.startswith("このアカウントは見つかりませんでした。"):
            logger.warning(f"ユーザー @{username} は存在しません。データベースのis_aliveをFalseに更新します。")
            self.favorite_user_repo.update_favorite_user_is_alive(username, False)
            raise self.UserNotFoundException(f"ユーザー @{username} は存在しません")
        
        # ユーザーページの読み込みを確認
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='user-post-item']"))
        )
        logger.debug(f"ユーザー @{username} のページに移動しました")
            

    def get_video_light_like_datas_from_user_page(self, max_videos: int = 100) -> List[Dict[str, str]]:
        logger.debug(f"動画の軽いデータの前半を取得中...")
        video_stats = []
        # 動画要素を取得
        self.scroll_page(max_videos // 16)
        video_elements = self.wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-e2e='user-post-item']"))
        )

        logger.debug(f"{len(video_elements)}件走査します")
        for video_element in video_elements[:max_videos]:
            try:
                # 動画のURLを取得
                video_link = video_element.find_element(By.TAG_NAME, "a")
                video_url = video_link.get_attribute("href")
                
                # 写真投稿の場合はスキップ
                if "/photo/" in video_url:
                    continue

                # URLからvideo_idとuser_usernameを抽出
                video_id, user_username = parse_tiktok_video_url(video_url)
                
                # サムネイル画像と動画の代替テキストを取得
                thumbnail_element = video_element.find_element(By.CSS_SELECTOR, "img")
                thumbnail_url = thumbnail_element.get_attribute("src") # 50件中16件くらい src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" になって後半とのマージができなくなる問題があったけど、画面最大化してスクロールの時間ちょっと伸ばしたら治った
                video_alt_info_text = thumbnail_element.get_attribute("alt")
                
                # いいね数を取得（表示形式のまま）
                like_count_element = video_element.find_element(By.CSS_SELECTOR, "[data-e2e='video-views']") # video-viewsといいながらいいね数
                like_count_text = like_count_element.text
                
                video_stats.append({
                    "video_url": video_url,
                    "video_id": video_id,
                    "user_username": user_username,
                    "video_thumbnail_url": thumbnail_url,
                    "video_alt_info_text": video_alt_info_text,
                    "like_count_text": like_count_text,
                    "crawling_algorithm": "selenium-human-like-1"
                })
                
            except NoSuchElementException:
                logger.warning(f"動画の軽いデータの前半の取得のうち1件に失敗", exc_info=True)
                continue
        
        logger.debug(f"動画の軽いデータの前半を取得しました: {len(video_stats)}件")
        return video_stats


    def navigate_to_video_page(self, video_url: str, link_should_be_in_page: bool = True):
        logger.debug(f"動画ページに移動中...: {video_url}")

        if link_should_be_in_page:
            try:
                video_link = self.driver.find_element(By.CSS_SELECTOR, f"a[href='{video_url}'")
                video_link.click()
            except NoSuchElementException:
                logger.warning(f"動画ページへのリンクが見つからなかったので直接アクセスします: {video_url}")
                self.driver.get(video_url)
        else:
            self.driver.get(video_url)
        
        self._random_sleep(2.0, 4.0)
        
        # 動画の詳細情報を待機
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='user-title']"))
        )
        logger.debug(f"動画ページに移動しました: {video_url}")


    def get_video_heavy_data_from_video_page(self) -> Dict[str, str]:
        logger.debug(f"動画の重いデータを取得中...")
    
        video_url = self.driver.current_url
        user_username = self.driver.find_element(By.CSS_SELECTOR, "[data-e2e='user-title']").text
        user_nickname = self.driver.find_element(By.CSS_SELECTOR, "[data-e2e='user-subtitle']").text
        video_title = self.driver.find_element(By.CSS_SELECTOR, "[data-e2e='browse-video-desc']").text
        post_time_text = self.driver.find_element(By.CSS_SELECTOR, "[data-e2e='browser-nickname'] span:last-child").text
        audio_url = self.driver.find_element(By.CSS_SELECTOR, "[data-e2e='browse-music'] a").get_attribute("href")
        audio_info_text = self.driver.find_element(By.CSS_SELECTOR, "[data-e2e='browse-music'] .css-pvx3oa-DivMusicText").text
        like_count_text = self.driver.find_element(By.CSS_SELECTOR, "strong[data-e2e='browse-like-count']").text
        comment_count_text = self.driver.find_element(By.CSS_SELECTOR, "strong[data-e2e='browse-comment-count']").text
        collect_count_text = self.driver.find_element(By.CSS_SELECTOR, "strong[data-e2e='undefined-count']").text
        
        logger.debug(f"動画の重いデータを取得しました: {video_url}")

        return {
            "video_url": video_url,
            "user_username": user_username,
            "user_nickname": user_nickname,
            "video_title": video_title,
            "post_time_text": post_time_text,
            "audio_url": audio_url,
            "audio_info_text": audio_info_text,
            "like_count_text": like_count_text,
            "comment_count_text": comment_count_text,
            "collect_count_text": collect_count_text,
            "crawling_algorithm": "selenium-human-like-1"
        }

    
    def navigate_to_user_page_from_video_page(self):
        logger.debug("動画ページの閉じるボタンをクリックしてユーザーページに戻ります...")

        close_button = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='browse-close']"))
        )
        close_button.click()
        self._random_sleep(1.0, 2.0)
        
        # ユーザーページの動画一覧が表示されるまで待機
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='user-post-item']"))
        )
        logger.debug("ユーザーページに戻りました")


    def navigate_to_video_page_creator_videos_tab(self):
        logger.debug("動画ページの「クリエイターの動画」タブに移動中...")
        
        # 2番目のタブ（クリエイターの動画）を待機して取得
        creator_videos_tab = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='DivTabMenuContainer'] [class*='DivTabItemContainer']:nth-child(2) [class*='DivTabItem']"))
        )
        creator_videos_tab.click()
        self._random_sleep(1.0, 2.0)
        logger.debug("動画ページの「クリエイターの動画」タブに移動しました")


    def get_video_light_play_datas_from_video_page_creator_videos_tab(self, max_videos: int = 100) -> List[Dict[str, str]]:
        # max_videosはあくまで目安。動画要素を取得範囲のスクロール幅をコントロールするだけで、実際に取得する動画数は制限されない
        logger.debug(f"動画の軽いデータの後半を取得中...")

        video_stats = []
        # クリエイターの動画一覧をスクロール
        self.scroll_element("div[class*='css-1xyzrsf-DivVideoListContainer e1o3lsy81']", max_videos // 12)
        video_elements = self.wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[class='css-eqiq8z-DivItemContainer eadndt66']"))
        )

        logger.debug(f"{len(video_elements)}件走査します")
        for video_element in video_elements:
            try:
                # サムネイル画像を取得
                thumbnail_element = video_element.find_element(By.CSS_SELECTOR, "img[class*='ImgCover']")
                thumbnail_url = thumbnail_element.get_attribute("src")
                
                # 再生数を取得（表示形式のまま）
                play_count_element = video_element.find_element(By.CSS_SELECTOR, "div[class*='DivPlayCount']")
                play_count_text = play_count_element.text
                
                video_stats.append({
                    "video_thumbnail_url": thumbnail_url,
                    "play_count_text": play_count_text
                })
                # logger.debug(f"動画の再生数情報を取得: {thumbnail_url} -> {play_count_text}")
                
            except NoSuchElementException:
                logger.warning(f"動画の軽いデータの後半の取得のうち1件に失敗", exc_info=True)
                continue
        
        logger.debug(f"動画の軽いデータの後半を取得しました: {len(video_stats)}件")
        return video_stats


    def parse_and_save_video_heavy_data(self, heavy_data: Dict, thumbnail_url: str):
        logger.debug(f"動画の重いデータをパースおよび保存中...: {heavy_data['video_url']}")

        video_id, _ = parse_tiktok_video_url(heavy_data["video_url"])

        # audio_info_textから音声情報を抽出
        audio_title = None
        audio_author_name = None
        if heavy_data.get("audio_info_text"):
            parts = heavy_data["audio_info_text"].split(" - ")
            if len(parts) >= 2:
                # 最後の部分をaudio_author_nameとし、それ以外を全てaudio_titleとする
                audio_author_name = parts[-1]
                audio_title = " - ".join(parts[:-1])

        post_time = parse_tiktok_time(heavy_data.get("post_time_text"), datetime.now())

        data = VideoHeavyRawData(
            id=None,
            video_url=heavy_data["video_url"],
            video_id=video_id,
            user_username=heavy_data["user_username"],
            user_nickname=heavy_data["user_nickname"],
            video_thumbnail_url=thumbnail_url,
            video_title=heavy_data["video_title"],
            post_time_text=heavy_data.get("post_time_text"),
            post_time=post_time,
            audio_url=heavy_data.get("audio_url"),
            audio_info_text=heavy_data.get("audio_info_text"),
            audio_id=None,  # ここでは取得できない(できるかも)
            audio_title=audio_title,
            audio_author_name=audio_author_name,
            play_count_text=None,  # ここでは取得できない
            play_count=None,  # ここでは取得できない
            like_count_text=heavy_data.get("like_count_text"),
            like_count=parse_tiktok_number(heavy_data.get("like_count_text")),
            comment_count_text=heavy_data.get("comment_count_text"),
            comment_count=parse_tiktok_number(heavy_data.get("comment_count_text")),
            collect_count_text=heavy_data.get("collect_count_text"),
            collect_count=parse_tiktok_number(heavy_data.get("collect_count_text")),
            share_count_text=None,  # ここでは取得できない
            share_count=None,  # ここでは取得できない
            crawled_at=datetime.now(),
            crawling_algorithm=heavy_data["crawling_algorithm"]
        )
        
        self.video_repo.save_video_heavy_data(data)
        logger.info(f"動画の重いデータをパースおよび保存しました: {data.video_url}")
        return True


    def parse_and_save_video_light_datas(self, light_like_datas: List[Dict], light_play_datas: List[Dict]):
        logger.debug(f"動画の軽いデータをパースおよび保存中...")

        # サムネイルURLのエッセンスをキーに、再生数をマッピング
        play_count_map = {}
        for play_data in light_play_datas:
            thumbnail_essence = extract_thumbnail_essence(play_data["video_thumbnail_url"])
            play_count_map[thumbnail_essence] = play_data["play_count_text"]
        
        # いいね数データを処理し、再生数を追加
        play_count_not_found = 0
        for like_data in light_like_datas:
            thumbnail_essence = extract_thumbnail_essence(like_data["video_thumbnail_url"])
            play_count_text = play_count_map.get(thumbnail_essence)
            if not play_count_text:
                play_count_not_found += 1

            data = VideoLightRawData(
                id=None,
                video_url=like_data["video_url"],
                video_id=like_data["video_id"],
                user_username=like_data["user_username"],
                video_thumbnail_url=like_data["video_thumbnail_url"],
                video_alt_info_text=like_data["video_alt_info_text"],
                play_count_text=play_count_text,
                play_count=parse_tiktok_number(play_count_text),
                like_count_text=like_data["like_count_text"],
                like_count=parse_tiktok_number(like_data["like_count_text"]),
                crawling_algorithm=like_data["crawling_algorithm"],
                crawled_at=datetime.now()
            )

            # logger.debug(f"動画の軽いデータを保存します: {data.video_id} -> {data.play_count}, {data.like_count}")
            self.video_repo.save_video_light_data(data)
            
            logger.info(f"動画の軽いデータをパースおよび保存しました: {len(light_like_datas)}件、うちplay_count_textが取れなかったもの: {play_count_not_found}件")
            return True


    def crawl_user_light(self, user: FavoriteUser, max_videos: int = 100):
        logger.info(f"ユーザー @{user.favorite_user_username} の軽いデータのクロールを開始")

        self.navigate_to_user_page(user.favorite_user_username)
        light_like_datas = self.get_video_light_like_datas_from_user_page(max_videos)

        first_url = light_like_datas[0]["video_url"]
        self.navigate_to_video_page(first_url)
        light_play_datas = self.get_video_light_play_datas_from_video_page_creator_videos_tab(max_videos+12) # ピン留めとかphoto投稿の影響でちゃんと一対一対応してるか怪しいんでね
        
        self.parse_and_save_video_light_datas(light_like_datas, light_play_datas)

        self.favorite_user_repo.update_favorite_user_last_crawled(
            user.favorite_user_username,
            datetime.now()
        )
        logger.info(f"ユーザー @{user.favorite_user_username} の軽いデータのクロールを完了しました")


    def crawl_favorite_users_light(self, max_videos_per_user: int = 100, max_users: int = 10):
        logger.info(f"クロール対象のお気に入りアカウント{max_users}件に対し軽いデータのクロールを行います")
        favorite_users = self.favorite_user_repo.get_favorite_users(
            self.crawler_account.id,
            limit=max_users
        )

        for user in favorite_users:
            try:
                self.crawl_user_light(user, max_videos_per_user)
            except Exception:
                logger.exception(f"ユーザー @{user.favorite_user_username} の軽いデータのクロール中に失敗")
                continue
            
        logger.info(f"クロール対象のお気に入りアカウント{len(favorite_users)}件に対し軽いデータのクロールを完了しました")


    def crawl_user_heavy(self, user: FavoriteUser, max_videos: int = 100):
        logger.info(f"ユーザー @{user.favorite_user_username} の重いデータのクロールを開始")

        self.navigate_to_user_page(user.favorite_user_username)
        light_like_datas = self.get_video_light_like_datas_from_user_page(max_videos)

        logger.info(f"新着動画 {len(light_like_datas)}件に対し重いデータのクロールを行います")
        for light_like_data in light_like_datas:
            try:
                self.navigate_to_video_page(light_like_data["video_url"])
                try:
                    heavy_data = self.get_video_heavy_data_from_video_page()
                    self.parse_and_save_video_heavy_data(heavy_data, light_like_data["video_thumbnail_url"])
                    self._random_sleep(10.0, 20.0) # こんくらいは見たほうがいいんじゃないかな未検証だけど
                except Exception:
                    logger.exception(f"動画ページを開いた状態でエラーが発生しました。動画ページを閉じてユーザーページに戻ります。")
                    raise
                finally:
                    self.navigate_to_user_page_from_video_page()
            except Exception:
                logger.exception(f"動画 {light_like_data['video_url']} の重いデータのクロール中に失敗。継続します")
                continue

        self.favorite_user_repo.update_favorite_user_last_crawled(
            user.favorite_user_username,
            datetime.now()
        )
        logger.info(f"ユーザー @{user.favorite_user_username} の重いデータのクロールを完了しました")


    def crawl_favorite_users_heavy(self, max_videos_per_user: int = 10, max_users: int = 10):
        logger.info(f"クロール対象のお気に入りアカウント{max_users}件に対し重いデータのクロールを行います")
        favorite_users = self.favorite_user_repo.get_favorite_users(
            self.crawler_account.id,
            limit=max_users
        )

        for user in favorite_users:
            try:
                self.crawl_user_heavy(user, max_videos_per_user)
            except Exception:
                logger.exception(f"ユーザー @{user.favorite_user_username} の重いデータのクロール中に失敗。継続します")
                continue
        
        logger.info(f"クロール対象のお気に入りアカウント{len(favorite_users)}件に対し重いデータのクロールを完了しました")
    


def main():
    # コマンドライン引数の処理
    import argparse
    parser = argparse.ArgumentParser(description="TikTok動画データ収集クローラー")
    
    # 必須の引数
    parser.add_argument(
        "mode",
        choices=["light", "heavy", "both"],
        help="クロールモード。light: 軽いデータのみ、heavy: 重いデータのみ、both: 両方"
    )
    
    # オプションの引数
    parser.add_argument(
        "--crawler-account-id",
        type=int,
        help="使用するクローラーアカウントのID"
    )
    parser.add_argument(
        "--max-videos-per-user",
        type=int,
        default=50,
        help="1アカウントあたりの最大取得動画数（デフォルト: 50）"
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=10,
        help="クロール対象の最大アカウント数（デフォルト: 10）"
    )
    
    args = parser.parse_args()

    # データベース接続の初期化
    db = Database()
    
    try:
        # 各リポジトリの初期化
        crawler_account_repo = CrawlerAccountRepository(db)
        favorite_user_repo = FavoriteUserRepository(db)
        video_repo = VideoRepository(db)
            
        # クローラーの初期化
        crawler = TikTokCrawler(
            crawler_account_repo=crawler_account_repo,
            favorite_user_repo=favorite_user_repo,
            video_repo=video_repo
        )
    
        try:
            # クローラーを開始（Selenium初期化とログイン）
            crawler.start(args.crawler_account_id)
            
            # モードに応じてクロール
            if args.mode in ["light", "both"]:
                crawler.crawl_favorite_users_light(
                    max_videos_per_user=args.max_videos_per_user,
                    max_users=args.max_users
                )
            
            if args.mode in ["heavy", "both"]:
                crawler.crawl_favorite_users_heavy(
                    max_videos_per_user=args.max_videos_per_user,
                    max_users=args.max_users
                )

            # TODO bothのとき被ってるとこ多いんで別関数で作ろう
                  
        except Exception:
            logger.exception(f"クローラー起動状態でエラーが発生しました。クローラーを停止します。")
            raise
        
        finally:
            # クローラーの停止（Seleniumのクリーンアップ）
            crawler.stop()

    except Exception:
        logger.exception(f"DB接続状態でエラーが発生しました。DB接続を切断します。")
        raise
        
    finally:
        # データベース接続のクリーンアップ
        db.disconnect()


if __name__ == "__main__":
    main()
