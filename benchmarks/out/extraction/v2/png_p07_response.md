# v2 / png_p07

**Date:** 2026-04-26  
**Source:** Microsoft Copilot Web, prompt_id=v2

## Output

### 書き起こし

混合ダッシュボードページ

2026 Q1  
合計 144M JPY  
Code: Python 3.13.1  
Source: BI Snapshot 2026-04-15

地域別実績

地域 | 売上 | 成長率 | 顧客数 | 担当 | 顧客率 | 新規 | 再購入率 | 平均単価
東京 | 164M | +12% | 1,240 | 佐藤 | 1.4% | +182 | 62% | 8,400
大阪 | 103M | +8% | 820 | 鈴木 | 1.8% | +96 | 58% | 7,900
名古屋 | 80M | +5% | 640 | 田中 | 1.6% | +48 | 55% | 7,500
札幌 | 28M | +9% | 240 | 渡辺 | 2.4% | +24 | 52% | 6,800
仙台 | 21M | +11% | 190 | 伊藤 | 1.9% | +22 | 57% | 7,100
広島 | 18M | +6% | 160 | 小林 | 2.0% | +14 | 54% | 6,900
高松 | 12M | +18% | 110 | 中村 | 1.3% | +20 | 63% | 7,300

Weekly active users 8週

W1: 3200  
W2: 3450  
W3: 3100  
W4: 3680  
W5: 3920  
W6: 3520  
W7: 3850  
W8: 4100

スクリーンショット

プッシュ通知設定画面 (iOS / Android 両対応) / 設定 v3.4.2

notify.py
```  
from typing import Optional  
from .retry import retry  

@retry(tries=3, delay=2)  
async def send_push(  
    user_id: str,  
    msg: str,  
    *,  
    priority: int = 5,  
) -> bool:  
    if not _is_opted_in(user_id):  
        return False  
    try:  
        return await _provider.send(user_id, msg, priority)  
    except ProviderTimeout:  
        return False  
```

主要メトリクス

API レイテンシ p95 は 240ms  
エラー率 0.4% (先月比 -0.1pt)  
スパイクは水曜 14 時台  
DAU 30k / MAU 145k  
解約率 月次 1.8%  
ARPU 3,200 円  
インシデント Q1 で 2 件 (P3 のみ)  
次回リリース 2026-04-30
