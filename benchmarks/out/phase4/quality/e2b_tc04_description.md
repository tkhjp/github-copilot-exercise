# tc04 — e2b

**Question:** この文書ページに含まれるすべてのテキスト情報を教えてください。タイトル、各セクションの見出しと本文、箇条書きの各項目（数値を含む）、テーブルの全セルの値、ヘッダーとフッターの内容を具体的に挙げてください。


**Describe wall_seconds:** 17.72

## Output

提供された画像に基づいて、ページに含まれるすべてのテキスト情報を以下にまとめます。

---

### タイトル・主要な見出し

*   **System Requirements Specification** (章の見出し)
*   **3.1 Performance Requirements**
*   **3.2 Availability & Reliability**

### 本文と箇条書き

#### 3.1 Performance Requirements の本文
> This chapter defines the non-functional requirements (NFRs) for the ShopApp e-commerce platform. These requirements apply to the production environment running on AWS ap-southeast-1 and must be met before the GA release scheduled for 2026Q3.

#### 3.1 Performance Requirements の箇条書き
*   API response time (p95): $\le 200 \text{ ms}$
*   Search query throughput: $\ge 500 \text{ requests/sec}$
*   Database query timeout: $\le 5 \text{ seconds (hard limit)}$
*   Page load time (LCP): $\le 1.5 \text{ seconds on 4G network}$
*   Batch processing (nightly): complete within 2 hours

#### 3.2 Availability & Reliability の本文
> The system must achieve the uptime and recovery targets listed below. Planned maintenance windows (Sunday 02:00-06:00 JST) are excluded from the uptime calculation.

#### 3.2 Availability & Reliability のテーブル（要求事項、ターゲット、優先度）

| Requirement | Target | Priority |
| :--- | :--- | :--- |
| Monthly uptime | $\ge 99.9\%$ | Must |
| RTO (Recovery Time Objective) | $\le 15 \text{ minutes}$ | Must |
| RPO (Recovery Point Objective) | $\le 5 \text{ minutes}$ | Must |
| Failover (AZ-level) | Automatic | Should |
| Data backup retention | $90 \text{ days}$ | Must |

### ヘッダーとフッター

*   **ヘッダー/その他:**
    *   `ACME Corp.`
    *   `Confidential — Draft v2.1`
*   **フッター:**
    *   `Page 12`
    *   `Last updated: 2026-03-15`

---
