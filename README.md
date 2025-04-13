# TikTok Crawler

TikTok動画の再生数といいね数の推移データを収集するクローラー。約30,000動画のデータ収集を目標としています。

## 機能

- TikTok動画の基本情報の収集
  - 動画ID
  - URL
  - アカウント情報
  - タイトル
  - 投稿日時

- 動画の統計情報の収集
  - 再生数
  - いいね数

- マルチアカウント対応
  - 複数のクローラーアカウントを管理
  - アカウントの利用状況を追跡

## 環境構築

```bash
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# Windows
.\venv\Scripts\activate
# Unix/MacOS
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
```

## 環境変数の設定

`.env`ファイルを作成し、以下の環境変数を設定してください：

```
DB_HOST=localhost
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=tiktok_crawler
```

## データベース構造

### crawler_accounts: クローラーアカウント管理
- id: int (PK, 自動採番)
- username: str (クローラーのTikTokアカウント名)
- password: str (クローラーのTikTokパスワード)
- proxy: str | null (プロキシ設定、未設定の場合はnull)
- is_alive: bool (アカウントの有効性)
- last_crawled_at: datetime | null (最終クロール日時、未クロールの場合はnull)

### favorite_accounts: クロール対象アカウント管理
- id: int (PK, 自動採番)
- favorite_account_username: str (クロール対象のTikTokアカウント名)
- crawler_account_id: int | null (FK -> crawler_accounts.id、未割り当ての場合はnull)
- favorite_account_is_alive: bool (アカウントの有効性)
- crawl_priority: int (クロール優先度)
- last_crawled_at: datetime | null (最終クロール日時、未クロールの場合はnull)

### video_desc_raw_data: 動画の基本情報
- id: int (PK, 自動採番)
- video_id: str (TikTokの動画ID)
- url: str (動画のURL)
- account_username: str (投稿者のアカウント名)
- account_nickname: str (投稿者のニックネーム)
- title: str (動画のタイトル)
- posted_at_text: str (投稿日時の表示形式)
- posted_at: datetime | null (パース後の投稿日時、パース失敗時はnull)
- crawled_at: datetime (クロール日時)

### video_like_stat_raw_data: 動画のいいね数データ
- id: int (PK, 自動採番)
- video_id: str (TikTokの動画ID)
- url: str (動画のURL)
- account_username: str (投稿者のアカウント名)
- count_text: str (表示形式のままのいいね数、例: "1.5M")
- count: int | null (パース後の数値、パース失敗時はnull)
- crawled_at: datetime (クロール日時)

### video_play_stat_raw_data: 動画の再生数データ
- id: int (PK, 自動採番)
- video_id: str (TikTokの動画ID)
- url: str (動画のURL)
- account_username: str (投稿者のアカウント名)
- count_text: str (表示形式のままの再生数、例: "2.3M")
- count: int | null (パース後の数値、パース失敗時はnull)
- crawled_at: datetime (クロール日時)

## 使い方

1. データベースを初期化
```bash
python -m src.database.create_tables
```

2. テストデータを投入（オプション）
```bash
python -m src.database.seed_data
```

3. クローラーを実行
```bash
# ランダムなクローラーアカウントを使用
python -m src.crawler.tiktok_crawler

# 特定のクローラーアカウントを指定
python -m src.crawler.tiktok_crawler --account-id 1
```

## 注意事項

- 本クローラーは人間らしい動作をシミュレートし、サーバーに負荷をかけないよう配慮しています。
- クロール対象のアカウントや動画については、各サービスの利用規約やガイドラインに従ってください。
