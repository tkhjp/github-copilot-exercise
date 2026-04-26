# v1 / png_p07_response

**Date:** 2026-04-24  
**Source:** Microsoft Copilot Web, prompt_id=v1

## Output

混合ダッシュボードページ

2026 Q1 | Total: 365M JPY | Code: Python 3.13

地域別実績
| 地域 | 売上 | 成長率 | 顧客数 | 担当 |
|------|------|--------|--------|------|
| 東京 | 164M | +12% | 1,240 | 佐藤 |
| 大阪 | 103M | +8% | 820 | 鈴木 |
| 名古屋 | 62M | +5% | 510 | 高橋 |
| 福岡 | 36M | +15% | 310 | 田中 |

週間アクティブユーザー
W1: 3200
W2: 3450
W3: 3100
W4: 3680

プッシュ通知設定画面 (Push notification settings screen)

notify.py
```
def send_push(user_id: str, msg: str) -> bool:
    if not _is_opted_in(user_id):
        return False
    return _provider.send(user_id, msg)
```

主要メトリクス
API レイテンシ p95 は 240ms
エラー率 0.4% (先月比 -0.1pt)
スパイクは水曜 14 時台
