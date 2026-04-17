# tc01 — q5

**Question:** このスライドに含まれる情報をすべて教えてください。フローチャートの各ステップ、棒グラフの月別値、地域別売上テーブルの Tokyo の Mar と Total、コード中の関数シグネチャ、フッター注釈を具体的に挙げてください。


**Describe wall_seconds:** 27.26

## Output

提供された画像のスライドに含まれる情報は以下の通りです。

### 1. フローチャートの各ステップ (Order Flow)
フローチャートは「Order Flow」として示されており、以下の3つのステップで構成されています。
1. **Receive Order**
2. **Validate Payment**
3. **Ship Product**

### 2. 棒グラフの月別値 (Monthly Revenue - MJPY)
棒グラフ（Monthly Revenue (MJPY)）から読み取れる各月の売上値は以下の通りです。
* **Jan:** 120
* **Feb:** 85
* **Mar:** 160
* **Apr:** 140

### 3. 地域別売上テーブルの Tokyo の Mar と Total
「Regional Sales (MJPY)」テーブルから、**Tokyo** の値は以下の通りです。
* **Mar:** 160
* **Total:** 365

### 4. コード中の関数シグネチャ
コードブロック（`quarterly_total.py`）に含まれる関数のシグネチャは以下の通りです。
```python
def quarterly_total(region: str) -> int:
    # ... (中略)
    return data['Jan'] + data['Feb'] + data['Mar']
```

### 5. フッター注釈
スライドの最下部にあるフッター注釈は以下の通りです。
**Q1 total revenue: 975 million JPY. Mar was the strongest month across all regions.**
