# TikTok Crawler

TikTok動画の再生数推移データを収集するクローラー

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

- crawler_accounts: クローラーアカウント管理
- favorite_accounts: クロール対象アカウント管理
- movie_desc_raw_data: 動画の基本情報
- movie_stat_raw_data: 動画の統計情報
