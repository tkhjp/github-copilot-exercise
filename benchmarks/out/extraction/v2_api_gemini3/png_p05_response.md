# v2_api_gemini3 / p05_hierarchical_drilldown.png

**Date:** 2026-04-28
**Source:** Gemini API (gemini-3-flash-preview), trial_id=v2_api_gemini3

## Output

## Slide 1

決済システム 階層ドリルダウン
env: production-apac | Owner: Platform Team | Last audit: 2026-03-15 | v2.7.3

認証
商品カタログ
在庫管理
決済コア
通知
分析
レポート
管理者UI
監査
サポート

拡大: 決済コア のサブモジュール
PG アダプタ
手数料計算
リトライ制御
ログ/監査
ハンドラ
Webhook 配信
為替換算
不正検知

設定パラメータ (12 項目)
| パラメータ | 単位 | 現行値 | 推奨値 |
| :--- | :--- | :--- | :--- |
| retry_max | 回 | 3 | 5 |
| timeout_sec | 秒 | 10 | 15 |
| idempotency_key_ttl | 時間 | 24 | 72 |
| log_retention | 日 | 30 | 180 |
| webhook_max_concurrent | 同時数 | 10 | 30 |
| fx_rate_cache_ttl | 分 | 5 | 15 |
| fraud_score_threshold | 点 | 60 | 75 |
| pg_adapter_pool_size | 接続数 | 20 | 50 |
| audit_buffer_size | MB | 16 | 64 |
| batch_settle_window | 時間 | 1 | 4 |
| alert_latency_p99 | ms | 800 | 500 |
| circuit_breaker_threshold | % | 50 | 30 |

M1 ここ拡大
M2 要見直し

Platform Docs / Last modified: 2026-04-15 / Confidential
