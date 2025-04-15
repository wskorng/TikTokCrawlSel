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
from typing import Optional, List, Dict, Tuple

from ..database.models import CrawlerAccount, FavoriteAccount, VideoHeavyRawData, VideoLightRawData
from ..database.repositories import CrawlerAccountRepository, FavoriteAccountRepository, VideoRepository
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
        path = thumbnail_url
        if "?" in path:
            path = path.split("?")[0]
        file_name = path.split("/")[-1]
        if "." in file_name:
            file_name = file_name.split(".")[0]
        if "~" in file_name:
            file_name = file_name.split("~")[0]
        
        return file_name
    except Exception:
        logger.exception(f"サムネイルURLからIDの抽出に失敗: {thumbnail_url}")
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
        # 「分前」の場合
        if time_text.endswith("分前"):
            minutes = int(time_text.replace("分前", ""))
            return base_time - timedelta(minutes=minutes)

        # 「時間前」の場合
        if time_text.endswith("時間前"):
            hours = int(time_text.replace("時間前", ""))
            return base_time - timedelta(hours=hours)

        # 「日前」の場合
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
        return None


def parse_tiktok_video_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """TikTokのURLからvideo_idとaccount_usernameを抽出する
    
    Args:
        url: 解析するURL (e.g. "https://www.tiktok.com/@username/video/1234567890")
    
    Returns:
        (video_id, account_username)のタプル。解析できない場合はNone。
        例: ("1234567890", "username")
    """
    if not url:
        return None, None

    try:
        # URLからクエリパラメータを除去
        if "?" in url:
            url = url.split("?")[0]

        # URLのパスを分割
        # 例: ["https:", "", "www.tiktok.com", "@username", "video", "1234567890"]
        parts = url.split("/")
        
        # video_idは最後のセグメント
        video_id = parts[-1] if len(parts) > 0 else None
        
        # account_usernameは@から始まるセグメント
        account_username = None
        for part in parts:
            if part.startswith("@"):
                account_username = part[1:]  # @を除去
                break
        
        return video_id, account_username

    except:
        return None, None


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
        
        return None

    except:
        return None


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
        
    def start(self, crawler_account_id: Optional[int] = None): # crawler_account_id が None なら適当に持ってくる
        try:
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
        except Exception as e:
            logger.exception(f"クローラーの開始に失敗: {e}")
            self.stop()
            raise

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

    def _login(self): # TikTokにログインする
        try:
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

        except Exception:
            logger.exception(f"ログインに失敗")
            raise

    def navigate_to_user_page(self, username: str) -> bool:
        logger.debug(f"ユーザー @{username} のページに移動中...")
        try:
            self.driver.get(f"{self.BASE_URL}/@{username}")
            self._random_sleep(2.0, 4.0)
            
            # ユーザーページの読み込みを確認
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='user-post-item']"))
            )
            logger.debug(f"ユーザー @{username} のページに移動しました")
            return True
            
        except Exception:
            logger.exception(f"ユーザー @{username} のページへの移動に失敗")
            return False

    def get_video_light_like_datas_from_user_page(self, max_videos: int = 100) -> List[Dict[str, str]]:
        try:
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

                    # URLからvideo_idとaccount_usernameを抽出
                    video_id, account_username = parse_tiktok_video_url(video_url)
                    
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
                        "account_username": account_username,
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
            
        except Exception:
            logger.exception(f"動画の軽いデータの前半の取得に失敗: {len(video_elements)}件走査しました")
            return []

    def navigate_to_video_page(self, video_url: str) -> bool:
        logger.debug(f"動画ページに移動中...: {video_url}")
        try:
            # 現在のページにリンクがあればクリック、なければ直接移動
            # クリックで移動しないと、「クリエイターの動画」ではなく「関連動画」タブになる。まあそれでもクローラーは動くけど目的の動画を集めれるかと言うとね
            try:
                video_link = self.driver.find_element(By.CSS_SELECTOR, f"a[href='{video_url}'")
                video_link.click()
            except NoSuchElementException:
                self.driver.get(video_url)
            
            self._random_sleep(2.0, 4.0)
            
            # 動画の詳細情報を待機
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='user-title']"))
            )
            logger.debug(f"動画ページに移動しました: {video_url}")
            return True
            
        except Exception:
            logger.exception(f"動画ページへの移動に失敗: {video_url}")
            return False

    def get_video_heavy_data_from_video_page(self) -> Optional[Dict]:
        logger.debug(f"動画の重いデータを取得中...")
        try:
            video_url = self.driver.current_url
            account_username = self.driver.find_element(By.CSS_SELECTOR, "[data-e2e='user-title']").text
            account_nickname = self.driver.find_element(By.CSS_SELECTOR, "[data-e2e='user-subtitle']").text
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
                "account_username": account_username,
                "account_nickname": account_nickname,
                "video_title": video_title,
                "post_time_text": post_time_text,
                "audio_url": audio_url,
                "audio_info_text": audio_info_text,
                "like_count_text": like_count_text,
                "comment_count_text": comment_count_text,
                "collect_count_text": collect_count_text,
                "crawling_algorithm": "selenium-human-like-1"
            }

        except Exception:
            logger.exception(f"動画の重いデータの取得に失敗: {video_url}")
            return None
    
    def navigate_to_user_page_from_video_page(self) -> bool:
        logger.debug("動画ページの閉じるボタンをクリックしてユーザーページに戻ります...")
        try:
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
            return True
            
        except Exception:
            logger.exception(f"動画ページからユーザーページへの移動に失敗")
            return False

    def navigate_to_video_page_creator_videos_tab(self) -> bool:
        logger.debug("動画ページの「クリエイターの動画」タブに移動中...")
        try:
            # 2番目のタブ（クリエイターの動画）を待機して取得
            creator_videos_tab = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='DivTabMenuContainer'] [class*='DivTabItemContainer']:nth-child(2) [class*='DivTabItem']"))
            )
            creator_videos_tab.click()
            self._random_sleep(1.0, 2.0)
            return True
            
        except Exception:
            logger.exception(f"動画ページの「クリエイターの動画」タブへの移動に失敗")
            return False

    def get_video_light_play_datas_from_video_page_creator_videos_tab(self, max_videos: int = 100) -> List[Dict[str, str]]:
        # max_videosはあくまで目安。動画要素を取得範囲のスクロール幅をコントロールするだけで、実際に取得する動画数は制限されない
        logger.debug(f"動画の軽いデータの後半を取得中...")
        try:
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
            
        except Exception:
            logger.exception(f"動画の軽いデータの後半の取得に失敗: {len(video_elements)}件走査しました")
            return []

    def parse_and_save_video_heavy_data(self, heavy_data: Dict, thumbnail_url: str) -> bool:
        logger.debug(f"動画の重いデータをパースおよび保存中...: {heavy_data['video_url']}")
        try:
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
                account_username=heavy_data["account_username"],
                account_nickname=heavy_data["account_nickname"],
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
            
        except Exception:
            logger.exception(f"動画の重いデータのパースおよび保存に失敗: {data.video_url}")
            return False



    def parse_and_save_video_light_datas(self, light_like_datas: List[Dict], light_play_datas: List[Dict]) -> bool:
        logger.debug(f"動画の軽いデータをパースおよび保存中...")
        try:
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
                    account_username=like_data["account_username"],
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
            
        except Exception:
            logger.exception(f"動画の軽いデータのパースおよび保存に失敗")
            return False
            



    def crawl_favorite_accounts_light(self, max_videos_per_account: int = 100, max_accounts: int = 10):
        try:
            logger.info(f"クロール対象のお気に入りアカウント{max_accounts}件に対し軽いデータのクロールを行います")
            favorite_accounts = self.favorite_account_repo.get_favorite_accounts(
                self.crawler_account.id,
                limit=max_accounts
            )

            if not favorite_accounts:
                logger.info("クロール対象のアカウントが見つかりません")
                return

            # 各アカウントの動画をクロール
            for account in favorite_accounts:
                try:
                    logger.info(f"アカウント @{account.favorite_account_username} の軽いデータのクロールを開始")

                    # アカウントページに移動
                    if not self.navigate_to_user_page(account.favorite_account_username):
                        continue # これ失敗したら続行不能
                    light_like_datas = self.get_video_light_like_datas_from_user_page(max_videos_per_account)
                    if not light_like_datas:
                        continue # これ失敗したら続行不能

                    # 動画ページに移動
                    first_url = light_like_datas[0]["video_url"]
                    if not self.navigate_to_video_page(first_url):
                        continue # これ失敗したら続行不能

                    # 動画ページの「クリエイターの動画」タブに移動
                    if not self.navigate_to_video_page_creator_videos_tab():
                        continue # これ失敗したら続行不能
                    light_play_datas = self.get_video_light_play_datas_from_video_page_creator_videos_tab(max_videos_per_account+12) # ピン留めとかphoto投稿の影響でちゃんと一対一対応してるか怪しいんでね
                    
                    # 動画の基本情報を保存
                    self.parse_and_save_video_light_datas(light_like_datas, light_play_datas)

                    # アカウントの最終クロール時間を更新
                    self.favorite_account_repo.update_favorite_account_last_crawled(
                        account.favorite_account_username,
                        datetime.now()
                    )
                    logger.info(f"アカウント @{account.favorite_account_username} の軽いデータのクロールを完了しました")

                except Exception:
                    logger.exception(f"アカウント @{account.favorite_account_username} の軽いデータのクロール中に失敗")
                    continue
            
            logger.info(f"クロール対象のお気に入りアカウント{len(favorite_accounts)}件に対し軽いデータのクロールを完了しました")

        except Exception:
            logger.exception(f"軽いデータのクロール処理に失敗")
            raise


    def crawl_favorite_accounts_heavy(self, max_videos_per_account: int = 10, max_accounts: int = 10):
        try:
            logger.info(f"クロール対象のお気に入りアカウント{max_accounts}件に対し重いデータのクロールを行います")
            favorite_accounts = self.favorite_account_repo.get_favorite_accounts(
                self.crawler_account.id,
                limit=max_accounts
            )

            if not favorite_accounts:
                logger.info("クロール対象のアカウントが見つかりません")
                return

            # 各アカウントの動画をクロール
            for account in favorite_accounts:
                try:
                    logger.info(f"アカウント @{account.favorite_account_username} の重いデータのクロールを開始")

                    # 既存の動画IDを取得（既存動画チェック用）
                    existing_video_ids = self.video_repo.get_existing_heavy_data_video_ids(account.favorite_account_username)
                    logger.debug(f"既存の動画ID数: {len(existing_video_ids)}")

                    # アカウントページに移動
                    if not self.navigate_to_user_page(account.favorite_account_username):
                        continue
                    light_like_datas = self.get_video_light_like_datas_from_user_page(max_videos_per_account)
                    if not light_like_datas:
                        continue

                    for like_data in light_like_datas[:max_videos_per_account]:
                        if like_data["video_id"] in existing_video_ids:
                            break # 新着順なので今既存動画だったら次以降も既存動画

                        # 動画ページに移動
                        if not self.navigate_to_video_page(like_data["video_url"]):
                            continue # これ失敗したら続行不能
                        heavy_data = self.get_video_heavy_data_from_video_page()
                        if not heavy_data:
                            continue # これ失敗したら続行不能
                        self.parse_and_save_video_heavy_data(heavy_data, like_data["video_thumbnail_url"])
                        self._random_sleep(10.0, 20.0) # 最低限見てる感出す
                        if not self.navigate_to_user_page_from_video_page():
                            break # これ失敗したらその後も続行不能


                    # アカウントの最終クロール時間を更新
                    self.favorite_account_repo.update_favorite_account_last_crawled(
                        account.favorite_account_username,
                        datetime.now()
                    )
                    logger.info(f"アカウント @{account.favorite_account_username} の重いデータのクロールを完了しました")

                except Exception:
                    logger.exception(f"アカウント @{account.favorite_account_username} の重いデータのクロール中に失敗")
                    continue
            
            logger.info(f"クロール対象のお気に入りアカウント{len(favorite_accounts)}件に対し重いデータのクロールを完了しました")
        except Exception:
            logger.exception(f"重いデータのクロール処理に失敗")
            raise
    


def main():
    try:
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
            "--max-videos-per-account",
            type=int,
            default=50,
            help="1アカウントあたりの最大取得動画数（デフォルト: 50）"
        )
        parser.add_argument(
            "--max-accounts",
            type=int,
            default=10,
            help="クロール対象の最大アカウント数（デフォルト: 10）"
        )
        
        args = parser.parse_args()

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
            crawler.start(args.crawler_account_id)
            
            # モードに応じてクロール
            if args.mode in ["light", "both"]:
                crawler.crawl_favorite_accounts_light(
                    max_videos_per_account=args.max_videos_per_account,
                    max_accounts=args.max_accounts
                )
            
            if args.mode in ["heavy", "both"]:
                crawler.crawl_favorite_accounts_heavy(
                    max_videos_per_account=args.max_videos_per_account,
                    max_accounts=args.max_accounts
                )

            # TODO bothのとき被ってるとこ多いんで別関数で作ろう
            
        finally:
            # クローラーの停止（Seleniumのクリーンアップ）
            crawler.stop()
            
    except Exception:
        logger.exception(f"メイン処理でエラー")
        raise
    
    finally:
        # データベース接続のクリーンアップ
        db.disconnect()


if __name__ == "__main__":
    main()
