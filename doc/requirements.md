# 作りたいもの
tiktok動画の再生数推移のビッグデータ

# プロパティ
右辺はTikTokApiでの属性名
- 必須:
    - URL = url
        - ユーザー情報 = author.uniqueId + author.nickname
        - ID = id
    - タイトル = desc
    - 投稿日時 = createTime (日付だけでも可)
    - 再生数 = stats.playCount の推移
- かなり欲しい
    - いいね数 = stats.diggCount の推移
    - コメント数 = stats.commentCount の推移
    - 共有数 = stats.shareCount の推移
    - 保存数 = stats.collectCount の推移
- どうせなら取っときたい
    動画時間 = duration
    カバー画像 = cover
    音声ID= music.id
    音声タイトル = music.title
    音声アーティスト名 = music.authorName

# 量
- 推移を長くても1日間隔で取得
- 30000動画くらい追いたいかな？

# chrome上でスクレイピングできる情報
## ユーザーページ
例: .\page_sample\tiktok.user.3.html
### 20個ほど出てくる`<div class="css-1uqux2o-DivItemContainerV2 e19c29qe7">` あるいは `<div data-e2e="user-post-item"`
- 新着順
- スクロールすれば無限に出てくる
- 取れる情報: url, サムネリンク, いいね数, alt情報
    - alt情報 = {音声アーティスト名}の{音声タイトル}を使用して{投稿者のnickname}が作成した{動画タイトル}
    - これら+再生数 を「軽いデータ」と呼ぶことにします

## 動画ページ
例: .\page_sample\tiktok.video.3.html
### 現在見ている動画について
- 取れる情報: url, 投稿者のusername, 投稿者のnickname, 投稿日, 動画タイトル, 音声情報, いいね数, コメント数, 保存数
    - 音声情報 = {音声タイトル} - {音声アーティスト名}
    - これら+再生数 を「重いデータ」と呼ぶことにします

### 20個ほど出てくる`<div class="css-1uqux2o-DivItemContainerV2 e19c29qe7">` あるいは `<div data-e2e="user-post-item"`
ユーザーページのものと同じ。

## 動画ページの「クリエイターの動画」欄
例: .\page_sample\tiktok.video.3.tab.html
### 20個ほど出てくる`<div class="css-eqiq8z-DivItemContainer eadndt66">`
- 新着順ではあるが、どの期間かは変動する(古い動画をクリックすると最新6件見えないとかある)(一番新しい動画ならちゃんと新着順かな？)
- スクロールすれば無限に出てくる(たまに18件くらいで止まることある。謎)
- 取れる情報: サムネリンク, 再生数
    - カーソルを合わせると飛べるようになる
        - んだけどその状態をDevToolsのソース+F8で検証しても飛び先のurlがわからなかったんでむずい！
        - そのたび動画ロードするから通信やばいしやめとくか
        - サムネリンクがuser-post-itemと一緒なんでそこでマージしようぜ
            - この部分だけスクロールしてもuser-post-itemは増えないんで、マージ対象が必ずしも見つかるかと言うとって感じだが

### 20個ほど出てくる`<div class="css-1uqux2o-DivItemContainerV2 e19c29qe7">` あるいは `<div data-e2e="user-post-item"`
ユーザーページのものと同じ。

## 動画ページに直打ちでアクセスした場合
例: .\page_sample\tiktok.video.5 jikauti UNIVERSAL_DATA.json
- `<script id="UNIVERSAL_DATA_FOR_REHYDRATION" type="application/json">`内の`"webapp.video-detail"`に重いデータ全部載ってる



## chrome上のスクレイピングで人間らしい動きを再現
これが収集できるので
- ユーザーページ: `[url]`
- ユーザーページ: `[(url, サムネリンク, いいね数, alt情報)]` (軽いデータ前半)
- 動画ページ `(url, 投稿者のusername, 投稿者のnickname, 投稿日, 動画タイトル, 音声情報, いいね数, コメント数, 保存数)` (重いデータ)
- 動画ページ(クリエイターの動画を開いた状態): `[(サムネリンク, 再生数)]` (軽いデータ後半)

こういう移動のみに制限し
- 任意のページ -(urlアクセス)-> ユーザーページ
- ユーザーページ -(サムネをクリック)-> 動画ページのうち最新のもの
- 動画ページ -(「クリエイターの動画」をクリック)-> 動画ページのクリエイターの動画を開いた状態
- 動画ページ -(左上のバツボタンをクリック)-> ユーザーページ
- 動画ページのクリエイターの動画を開いた状態 -(左上のバツボタンをクリック)-> ユーザーページ
※動画ページのクリエイターの動画を開いた状態から別の動画に飛んだほうが自然だけどその要素を見つけるのが難しい

こういうステップでクロールしよう
- ユーザーページで新着動画のurlを収集
- ユーザーページで軽いデータ前半を収集
- 最も新しい動画ページで軽いデータ後半を収集
- 軽いデータ前半と軽いデータ後半をマージ
- 新着動画について重いデータを収集

reCAPTCHA的なの出たら検知して対応するのも要るわな それか出たら閉じて別のアカウント別のプロキシで再開でもいいけど



# DB構造
### crawler_accounts: クローラーアカウント管理
- id: int (PK, 自動採番)
- username: str (クローラーのTikTokアカウント名)
- password: str (クローラーのTikTokパスワード)
- proxy: str | null (プロキシ設定、未設定の場合はnull)
- is_alive: bool (Index, アカウントの有効性)
- last_crawled_at: datetime | null (Index, 最終クロール日時、未クロールの場合はnull)

### favorite_accounts: クロール対象アカウント管理
- id: int (PK, 自動採番)
- favorite_account_username: str (クロール対象のTikTokアカウント名)
- crawler_account_id: int | null (FK -> crawler_accounts.id、未割り当ての場合はnull)
- favorite_account_is_alive: bool (Index, アカウントの有効性)
- crawl_priority: int (Index, クロール優先度)
- last_crawled_at: datetime | null (Index, 最終クロール日時、未クロールの場合はnull)

### video_heavy_raw_data: 動画の重いデータ
- id: int (PK, 自動採番)
- video_url: str (動画URL)
- video_id: str (Index, 動画ID)
- account_username: str (Index, 投稿者のusername)
- account_nickname: str (投稿者のnickname)
- video_thumbnail_url: str (動画のサムネイルURL)
- video_title: str (動画のタイトル)
- post_time_text: str | null (投稿日時)
- post_time: datetime | null (Index)
- audio_url: str | null (音声URL)
- audio_info_text: str | null (音声情報 = {音声タイトル} - {音声アーティスト名})
- audio_id: str | null (音声ID)
- audio_title: str | null (音声タイトル)
- audio_author_name: str | null (音声アーティスト名)
- play_count_text: str | null (再生数)
- play_count: int | null
- like_count_text: str | null (いいね数)
- like_count: int | null
- comment_count_text: str | null (コメント数)
- comment_count: int | null
- collect_count_text: str | null (保存数)
- collect_count: int | null
- share_count_text: str | null (シェア数)
- share_count: int | null
- crawled_at: datetime (Index, クロール日時)
- crawling_algorithm: str (クロールアルゴリズム "tiktokapi":tiktokapiで収集 "selenium-direct":直接アクセス "selenium-human-like-1":今回実装する人間らしい動きでアクセス)(今後別のアルゴリズム(もっと精巧な人間アピだの人気順だのandroidエミュだの)でやる場合別名にしてね)
crawling_algorithm次第で得られる情報が異なるので、こんだけ列増やしてnull許容する必要がある

### video_light_raw_data: 動画の軽いデータ
- id: int (PK, 自動採番)
- video_url: str (動画URL)
- video_id: str (Index, 動画ID)
- account_username: str (Index, 投稿者のusername)
- video_thumbnail_url: str (動画のサムネイルURL)
- video_alt_info_text: str (alt情報)
- play_count_text: str | null (再生数)
- play_count: int | null
- like_count_text: str | null (いいね数)
- like_count: int | null
- crawled_at: datetime (Index, クロール日時)
- crawling_algorithm: str (クロールアルゴリズム "tiktokapi":tiktokapiで収集 "selenium-human-like-1":今回実装する人間らしい動きでアクセス)(今後別のアルゴリズム(もっと精巧な人間アピだの人気順だのandroidエミュだの)でやる場合別名にしてね)
マージできなかった軽いデータ後半を捨てるか、video_url,video_id,account_username抜きでvideo_thumbnail_urlをキーにアクセスできると主張し保存するか問題がある。まあ捨てていいと思うけど


# TODO
- 428行目問題
    - audio_info_text の取得に失敗したあと、無限に動画ページへの移動に失敗する
    - if not heavy_data: continue の際ちゃんとユーザーページに戻るfinallyがあれば無限に失敗はしないかと
    - ただaudio_info_text の取得に失敗することがあるバグは残るしいつ再現されるやら
    - ログ: issue_20250415_1.log

- アカウント消えてたときの処置
    - ちゃんと「このユーザーは消えました」的なの出るから、それ見つけて分岐させましょう
    - ログ: issue_20250415_2.log

- thumbnail_url が 時折無を表すgifになる問題
    - やっぱマウスオーバーでリンク出せないもんかね
    - しっかり画像ロードされるの確認してスクロールしかないかね

- 日前 がパースできない問題

# そのうちやること
- 既存システムに統合
    - db構造変わるぞ～
    - 特に2週間以上古い動画を見捨てる件
        - うちは2週間と言わず最新100本くらい集めてDBに突っ込むんで、不要データの削除は別プロセスでやることにします