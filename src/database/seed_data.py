from datetime import datetime
from typing import List
from .database import Database
from ..logger import setup_logger
from dotenv import load_dotenv

logger = setup_logger(__name__)

# クローラーアカウントのサンプルデータを投入
# Args:
#     db: データベース接続
# Returns:
#     クローラーアカウントIDのリスト
def insert_crawler_accounts(db: Database) -> List[int]:
    crawler_accounts = [
        {
            "username": "wskorng+01@gmail.com",
            "password": "<gitwn2%W$j?H93",
            "proxy": None,
            "is_alive": True
        }
    ]
    
    crawler_account_ids = []
    for crawler_account in crawler_accounts:
        query = """
            INSERT INTO crawler_accounts (
                username, password, proxy, is_alive
            ) VALUES (
                %s, %s, %s, %s
            )
        """
        cursor = db.execute_query(
            query,
            (
                crawler_account["username"],
                crawler_account["password"],
                crawler_account["proxy"],
                crawler_account["is_alive"]
            )
        )
        crawler_account_ids.append(cursor.lastrowid)
        logger.info(f"クローラーアカウント {crawler_account['username']} を追加しました")
    
    return crawler_account_ids

# お気に入りアカウントのサンプルデータを投入
# Args:
#     db: データベース接続
#     crawler_account_id: クローラーアカウントID
#     max_users: 投入するユーザー数の上限（Noneの場合は全て）
# Returns:
#     お気に入りアカウントIDのリスト
def insert_favorite_users(db: Database, crawler_account_id: int, max_users: int = None):
    accounts = [
        {
            "username": "cutie_street",  # CUTIE STREET
            "priority": 100
        },
        {
            "username": "fukada0318",  # 深田えいみ ※3つもピン留めしてる
            "priority": 100
        },
        {
            "username": "michaeljackton.official",  # マイケル・ジャクトンのusernameに背乗りしてる謎の外人 ※3本しか動画ない
            "priority": 100
        },
        {
            "username": "123987443",  # Marina ※死んでる
            "priority": 100
        },
        {
            "username": "zachking",  # Zach King ※ 世界一再生数が多い動画がピン留めされている
            "priority": 100
        },
        {
            "username": "twice_tiktok_official",  # Twice
            "priority": 100
        },
        {
            "username": "bayashi.tiktok",  # バヤシ
            "priority": 100
        },
        {
            "username": "junya1gou",  # じゅんや
            "priority": 100
        },
        {
            "username": "kageihina",  # 景井ひな
            "priority": 100
        },
        {
            "username": "0906yu_rin",  # ゆーり(21)yuri
            "priority": 100
        },
        {
            "username": "o_jas514",  # おじゃす
            "priority": 100
        },
        {
            "username": "naenano",  # なえなの
            "priority": 100
        },
        {
            "username": "unpai3",  # うんぱい
            "priority": 100
        },
        {
            "username": "buzzmagicianshin",  # Buzz Magician Shin ※死んでる
            "priority": 100
        },
        {
            "username": "exrikariko",  # りかりこ
            "priority": 100
        },
        {
            "username": "_lisa1431_",  # 渡辺リサ
            "priority": 100
        },
        {
            "username": "maikichi0130",  # まいきち
            "priority": 100
        },
        {
            "username": "chamitan_09082424",  # ゆうちゃみ
            "priority": 100
        },
        {
            "username": "83743927",  # 西村歩乃果
            "priority": 100
        },
        {
            "username": "kiritampo",  # きりたんぽ
            "priority": 100
        },
    ]

    
    # max_usersが指定されている場合は、その数だけアカウントを選択
    target_accounts = accounts[:max_users] if max_users is not None else accounts
    
    for account in target_accounts:
        query = """
            INSERT INTO favorite_users (
                favorite_user_username,
                crawler_account_id,
                favorite_user_is_alive,
                crawl_priority
            ) VALUES (
                %s, %s, %s, %s
            )
        """
        db.execute_query(
            query,
            (
                account["username"],
                crawler_account_id,
                True,
                account["priority"]
            )
        )
    
    logger.info(f"お気に入りアカウントを{len(target_accounts)}件追加しました")

# サンプル動画データの投入
def insert_sample_video_data(db: Database):
    # 重いデータ（詳細情報）
    heavy_data = {
        "video_id": "7483836569720245511",
        "video_url": "https://www.tiktok.com/@cutie_street/video/7483836569720245511",
        "user_username": "cutie_street",
        "user_nickname": "CUTIE STREET",
        "video_thumbnail_url": "https://p16-sign-va.tiktokcdn.com/obj/tos-maliva-p-0068/oQC3BSkCEfDFLKAEbAEQgANNBAKPDYwAfC7bAa",
        "video_title": "Our response to the Supreme Court decision.",
        "post_time_text": "2024-01-18",
        "post_time": datetime(2024, 1, 18),
        "audio_url": "https://www.tiktok.com/music/%E3%81%8B%E3%82%8F%E3%81%84%E3%81%84%E3%81%A0%E3%81%91%E3%81%98%E3%82%83%E3%81%A0%E3%82%81%E3%81%A7%E3%81%99%E3%81%8B-1%E3%82%B5%E3%83%93-7408694581557004305",
        "audio_info_text": "Original Sound - CUTIE STREET",
        "audio_id": "7408694581557004305",
        "audio_title": "かわいいだけじゃだめですか？ - 1サビ",
        "audio_author_name": "CUTIE STREET",
        "play_count_text": "5M",
        "play_count": 5000000,
        "like_count_text": "307.3K",
        "like_count": 307300,
        "comment_count_text": "1907",
        "comment_count": 1907,
        "collect_count_text": "1.1K",
        "collect_count": 1100,
        "share_count_text": None,
        "share_count": None,
        "crawled_at": datetime.now(),
        "crawling_algorithm": "selenium-human-like-1"
    }
    
    query = """
        INSERT INTO video_heavy_raw_data (
            video_id, video_url, user_username, user_nickname,
            video_thumbnail_url, video_title, post_time_text, post_time,
            audio_url, audio_info_text, audio_id, audio_title, audio_author_name,
            play_count_text, play_count, like_count_text, like_count,
            comment_count_text, comment_count, collect_count_text, collect_count,
            share_count_text, share_count, crawled_at, crawling_algorithm
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    db.execute_query(
        query,
        (
            heavy_data["video_id"],
            heavy_data["video_url"],
            heavy_data["user_username"],
            heavy_data["user_nickname"],
            heavy_data["video_thumbnail_url"],
            heavy_data["video_title"],
            heavy_data["post_time_text"],
            heavy_data["post_time"],
            heavy_data["audio_url"],
            heavy_data["audio_info_text"],
            heavy_data["audio_id"],
            heavy_data["audio_title"],
            heavy_data["audio_author_name"],
            heavy_data["play_count_text"],
            heavy_data["play_count"],
            heavy_data["like_count_text"],
            heavy_data["like_count"],
            heavy_data["comment_count_text"],
            heavy_data["comment_count"],
            heavy_data["collect_count_text"],
            heavy_data["collect_count"],
            heavy_data["share_count_text"],
            heavy_data["share_count"],
            heavy_data["crawled_at"],
            heavy_data["crawling_algorithm"]
        )
    )
    logger.info(f"サンプル重いデータ {heavy_data['video_id']} を追加しました")
    
    # 軽いデータ（基本情報）
    light_data = {
        "video_id": heavy_data["video_id"],
        "video_url": heavy_data["video_url"],
        "user_username": heavy_data["user_username"],
        "video_thumbnail_url": heavy_data["video_thumbnail_url"],
        "video_alt_info_text": f"{heavy_data['audio_author_name']}の{heavy_data['audio_title']}を使用して{heavy_data['user_nickname']}が作成した{heavy_data['video_title']}",
        "play_count_text": heavy_data["play_count_text"],
        "play_count": heavy_data["play_count"],
        "like_count_text": heavy_data["like_count_text"],
        "like_count": heavy_data["like_count"],
        "crawled_at": datetime.now(),
        "crawling_algorithm": "selenium-human-like-1"
    }
    
    query = """
        INSERT INTO video_light_raw_data (
            video_id, video_url, user_username, video_thumbnail_url,
            video_alt_info_text, play_count_text, play_count,
            like_count_text, like_count, crawled_at, crawling_algorithm
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    db.execute_query(
        query,
        (
            light_data["video_id"],
            light_data["video_url"],
            light_data["user_username"],
            light_data["video_thumbnail_url"],
            light_data["video_alt_info_text"],
            light_data["play_count_text"],
            light_data["play_count"],
            light_data["like_count_text"],
            light_data["like_count"],
            light_data["crawled_at"],
            light_data["crawling_algorithm"]
        )
    )
    logger.info(f"サンプル軽いデータを追加しました")




# テストデータの投入を実行
# Args:
#     max_users: 投入するお気に入りユーザー数の上限（Noneの場合は全て）
def main(max_users: int = None):
    load_dotenv()
    with Database() as db:
        logger.info("テストデータの投入を開始します")
        
        # クローラーアカウントの投入
        crawler_account_ids = insert_crawler_accounts(db)
        if not crawler_account_ids:
            raise ValueError("クローラーアカウントの投入に失敗しました")
        
        # お気に入りアカウントの投入（最初のクローラーアカウントに紐付け）
        insert_favorite_users(db, crawler_account_ids[0], max_users)
        
        # サンプル動画データの投入
        insert_sample_video_data(db)
        
        logger.info("テストデータの投入が完了しました")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="テストデータを投入します")
    parser.add_argument("--max-users", type=int, help="投入するお気に入りユーザー数の上限（指定がない場合は全て）")
    
    args = parser.parse_args()
    main(max_users=args.max_users)
