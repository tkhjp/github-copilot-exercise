# tc01 — q4

**Question:** このスライドに含まれる情報をすべて教えてください。フローチャートの各ステップ、棒グラフの月別値、地域別売上テーブルの Tokyo の Mar と Total、コード中の関数シグネチャ、フッター注釈を具体的に挙げてください。


**Describe wall_seconds:** 27.06

## Output

提供された画像のスライドに含まれる情報は以下の通りです。

### 1. フローチャートの各ステップ (Order Flow)
フローチャートは「Order Flow」として示されており、以下の3つのステップで構成されています。
1. **Receive Order** (注文の受信)
2. **Validate Payment** (支払いの検証)
3. **Ship Product** (製品の出荷)

### 2. 棒グラフの月別値 (Monthly Revenue - MJPY)
「Monthly Revenue (MJPY)」の棒グラフから読み取れる各月の売上（概算）は以下の通りです。
* **Jan (1月):** 約 120
* **Feb (2月):** 約 85
* **Mar (3月):** 約 160
* **Apr (4月):** 約 140

### 3. 地域別売上テーブルの Tokyo の Mar と Total
「Regional Sales (MJPY)」のテーブルから、Tokyo のデータは以下の通りです。
* **Tokyo の Mar (3月):** 160
* **Tokyo の Total (合計):** 365

### 4. コード中の関数シグネチャ
コードブロック（`quarterly_total.py`）に含まれる関数のシグネチャは以下の通りです。
* `def quarterly_total(region: str) -> int:`

### 5. フッター注釈
スライドの最下部にあるフッターには、以下の注釈が記載されています。
* **Q1 total revenue: 975 million JPY. Mar was the strongest month across all regions.** (第1四半期の総売上高は9億7500万円でした。3月は全地域で最も好調な月でした。)
