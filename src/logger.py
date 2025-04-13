import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logger(name: str) -> logging.Logger:
    """
    ロガーの設定を行う
    
    Args:
        name: ロガーの名前
    
    Returns:
        設定済みのロガーインスタンス
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # フォーマッターの作成
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # ファイルハンドラーの設定
    file_handler = RotatingFileHandler(
        'crawler.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # コンソールハンドラーの設定
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # ハンドラーの追加
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
