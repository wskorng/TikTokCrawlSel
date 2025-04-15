from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from ..logger import setup_logger

logger = setup_logger(__name__)

class SeleniumManager:
    def __init__(self, proxy: str = None):
        self.driver = None
        self.proxy = proxy

    def setup_driver(self):
        try:
            options = Options()
            if self.proxy:
                options.add_argument(f'--proxy-server={self.proxy}')
            
            # その他の設定
            options.add_argument('--no-sandbox')
            options.add_argument('--use-angle=gl')
            options.add_argument('--enable-features=Vulkan')
            options.add_argument('--disable-vulkan-surface')
            options.add_argument('--enable-gpu-rasterization')
            options.add_argument('--enable-zero-copy')
            options.add_argument('--ignore-gpu-blocklist')
            options.add_argument('--enable-hardware-overlays')
            options.add_argument('--enable-features=VaapiVideoDecoder')
            options.add_argument('--start-maximized') # ウィンドウ最大じゃないとget_video_light_like_datas_from_user_pageでthumbnail_urlの取得がおかしくなるのでそれを解決できない限り変えないこと
            
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # selenium-stealthの設定を適用
            stealth(
                self.driver,
                languages=["ja-JP", "ja"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="WebKit",  # 実際の環境に合わせて更新
                renderer="WebKit WebGL",  # 実際の環境に合わせて更新
                fix_hairline=True,
            )
            
            # JavaScriptを実行してWebDriverを検出されにくくする
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            logger.info("Chromeドライバーの設定が完了しました")
            return self.driver
        
        except Exception as e:
            logger.error(f"Chromeドライバーの設定中にエラーが発生しました: {e}")
            raise

    def quit_driver(self):
        if self.driver:
            self.driver.quit()
            logger.info("Chromeドライバーを終了しました")
