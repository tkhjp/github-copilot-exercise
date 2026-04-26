# v1 / pptx_response

**Date:** 2026-04-26  
**Source:** Microsoft Copilot Web, prompt_id=v1

## Output

勤怠アプリ画面レビュー  
勤怠管理 v3.2 - 田中太郎 | Screen-ID: TS-042. 

## Slide 1

勤怠アプリ画面レビュー

勤怠管理 v3.2 - 田中太郎 | Screen-ID: TS-042

勤怠管理

田中 太郎 さん

日付

出勤

退勤

実働

ステータス

2026-04-01 (水)

09:02

18:15

08:13

承認済

2026-04-02 (木)

08:58

19:40

09:42

承認待

2026-04-03 (金)

09:15

17:50

07:35

要修正

2026-04-04 (月)

09:00

18:00

08:00

承認済

エクスポート

新規追加

編集

削除

C1

承認待の行に目立つ色を付けてください

C2

実働が 8 時間未満の行に警告アイコン

C3

エクスポートボタンをもっと右に寄せる

C4

日付の曜日表示は不要 (括弧削除)

© 2026 ACME Corp. / Confidential

## Slide 2

検索画面 Before / After 比較

TICKET-8421 | Review: 2026-03-15 | 鈴木 (UX Lead)

Before (現行)

キーワード入力

検索

結果: 12 件

< 1 2 3 >

After (改修後)

キーワードまたは商品コード

検索

結果: 12 件 / 並び順: 関連度順

< 1 2 3 4 5 … 20 >

D1 入力プレースホルダーに「商品コード」追加

D2 フィルタ行が 1 行 → 3 行に拡張

D3 ページネーションに省略記号 (…) と最終ページ追加

Design Review Doc v1.2 / Internal

## Slide 3

購入フロー 5 画面操作手順

UI Build ui-v2.1 | Session timeout: 30 min | Updated 2026-04-10

S1

ログイン

メール + パスワード

S2

商品選択

カテゴリ絞込 / 3 商品サムネイル

S3

カート

2 商品、小計 ¥8,300

S4

決済

クレジットカード / PayPay / コンビニ

S5

完了

注文番号 ORD-2026-04-13579

User Research Team / Page 1 of 1

## Slide 4

2026 Q1 売上ダッシュボード (注釈付き)

Period: 2026 Q1 | Data as of 2026-03-31 23:59 JST | 次回更新: 翌営業日

月別売上 (百万円)

120

Jan

85

Feb

160

Mar

地域別売上構成

東京 45%

大阪 28%

名古屋 17%

その他 10%

売上合計

365 MJPY

前年比 +12%

新規顧客数

2,140

前年比 +8%

解約率

3.2%

前年比 -0.5pt

A1 Feb が底、Mar で V 字回復

A2 東京集中 (45%) が課題

A3 解約率改善はサポート体制強化の効果

Finance Team / Monthly Report / 2026-04 Issue

## Slide 5

決済システム 階層ドリルダウン

env: production-apac | Owner: Platform Team | Last audit: 2026-03-15

認証

商品カタログ

決済コア

通知

分析

拡大: 決済コア

PG アダプタ

手数料計算

リトライ制御

ログ/監査

設定パラメータ

パラメータ

現行値

推奨値

retry_max

3

5

timeout_sec

10

15

idempotency_key_ttl

24h

72h

log_retention

30d

180d

Platform Docs / Last modified: 2026-04-15

## Slide 6

ダッシュボード デザインレビュー (赤入れ)

PR #2847 | Figma: 1920x1080 | Weekly Design Review 2026-04-10 15:00

ダッシュボード モックアップ

ヘッダー (ロゴ + 通知)

サイドナビ (5 項目)

KPI カード (4 枚)

売上推移グラフ

最新取引テーブル

フッター (リンク)

R01

ロゴは左寄せではなく中央

R02

通知アイコンに未読バッジ追加

R03

サイドナビの配色を背景色から白背景に

R04

KPI カードは 4 枚ではなく 3 枚に減らす

R05

KPI カードのフォントサイズを大きく

R06

グラフに前年比の点線を追加

R07

グラフの凡例を右上から下に移動

R08

テーブルのゼブラストライプを薄く

R09

テーブルヘッダーは sticky に

R10

取引金額の桁区切りカンマ必須

R11

金額のマイナスは赤字

R12

フッターのリンクは 3 つまで

R13

全体的にマージンを 16px → 24px

R14

モバイル対応のブレークポイント要確認

R15

ダークモード対応は別 issue で

Design System Team / Draft v0.7

## Slide 7

混合ダッシュボードページ

Period: 2026 Q1 | Total: 365M JPY | Code: Python 3.13

地域別実績

地域

売上

成長率

顧客数

担当

東京

164M

+12%

1,240

佐藤

大阪

103M

+8%

820

鈴木

名古屋

62M

+5%

510

高橋

福岡

36M

+15%

310

田中

Weekly active users

3200

W1

3450

W2

3100

W3

3680

W4

スクリーンショット

プッシュ通知設定画面

notify.py

def send_push(user_id: str, msg: str) -> bool:

if not _is_opted_in(user_id):

return False

return _provider.send(user_id, msg)

主要メトリクス

• API レイテンシ p95 は 240ms

• エラー率 0.4% (先月比 -0.1pt)

• スパイクは水曜 14 時台

Analytics Dashboard / Confidential

## Slide 8

組織図 (3 階層 10 ノード)

Effective: 2026-04-01 | Source: HRIS 2026-03-31 | ※ 2020 年以降の社員のみ表示

山本 一郎

CEO

中村 次郎

CTO

小林 三郎

COO

加藤 四郎

CFO

伊藤 花子

Dev Manager

渡辺 梅子

Infra Manager

山田 桜子

Sales Head

佐々木 松子

Ops Head

吉田 竹子

Finance Head

井上 柳子

Legal Head

HR Org Chart / Effective 2026-04-01
