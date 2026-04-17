# tc01 — q8

**Question:** このスライドに含まれる情報をすべて教えてください。フローチャートの各ステップ、棒グラフの月別値、地域別売上テーブルの Tokyo の Mar と Total、コード中の関数シグネチャ、フッター注釈を具体的に挙げてください。


**Describe wall_seconds:** 44.23

## Output

提供された画像のスライドに含まれる情報は以下の通りです。

### 1. フローチャート（Order Flow）
注文の流れを示すフローチャートは以下の3つのステップで構成されています。
* **Receive Order** (注文の受信) $\rightarrow$ **Validate Payment** (支払いの検証) $\rightarrow$ **Ship Product** (製品の出荷)

### 2. 棒グラフ（Monthly Revenue (MJPY)）
月別の収益を示す棒グラフの値は以下の通りです。
* **Jan (1月):** 120 MJPY
* **Feb (2月):** 85 MJPY
* **Mar (3月):** 160 MJPY
* **Apr (4月):** 140 MJPY

### 3. 地域別売上テーブル（Regional Sales (MJPY)）
地域ごとの月別売上を示すテーブルです。特に指定された値は以下の通りです。
* **Tokyo の Mar (3月):** 160 MJPY
* **Tokyo の Total (合計):** 365 MJPY

### 4. コード中の関数シグネチャ（`quarterly_total.py`）
コードブロックに含まれる主要な関数のシグネチャは以下の通りです。
```python
def quarterly_total(region: str) -> int:
    # ... (中略)
    return data['Jan'] + data['Feb'] + data['Mar']

total = quarterly_total('Tokyo')
```
**関数シグネチャ:** `quarterly_total(region: str) -> int`

### 5. フッター注釈（Footer Annotation）
スライドの最下部にあるフッターには以下の記述があります。
* **Q1 total revenue: 975 million JPY. Mar was the strongest month across all regions.**
