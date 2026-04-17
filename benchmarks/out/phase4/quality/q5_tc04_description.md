# tc04 — q5

**Question:** この文書ページに含まれるすべてのテキスト情報を教えてください。タイトル、各セクションの見出しと本文、箇条書きの各項目（数値を含む）、テーブルの全セルの値、ヘッダーとフッターの内容を具体的に挙げてください。


**Describe wall_seconds:** 40.94

## Output

提供された画像に基づいて、文書ページに含まれるすべてのテキスト情報を以下にまとめます。

---

### 全体の構造情報

*   **ヘッダー:** `ACME Corp.` (左上) および `Confidential — Draft v2.1` (右上)
*   **フッター:** `Page 12` (左下) および `Last updated: 2026-03-15` (右下)

### タイトルとセクション情報

#### メインタイトル
*   **System Requirements Specification**

#### セクション見出しと本文

**Chapter 3: Non-Functional Requirements**
*   **本文:** This chapter defines the non-functional requirements (NFRs) for the ShopApp e-commerce platform. These requirements apply to the production environment running on AWS ap-northeast-1 and must be met before the GA release scheduled for 2026 Q3.

**3.1 Performance Requirements**
*   **本文:** All API endpoints must meet the following latency and throughput targets under normal operating conditions (defined as <80% CPU utilization across the ECS cluster).

    *   **箇条書き項目:**
        *   API response time (p95): <= 200 ms
        *   API response time (p99): <= 500 ms
        *   Search query throughput: >= 500 requests/sec
        *   Database query timeout: <= 3 seconds (hard limit)
        *   Page load time (LCP): <= 1.5 seconds on 4G network
        *   Batch processing (nightly): complete within 2 hours

**3.2 Availability & Reliability**
*   **本文:** The system must achieve the uptime and recovery targets listed below. Planned maintenance windows (Sunday 02:00-06:00 JST) are excluded from the uptime calculation.

### テーブル情報

**テーブル名（暗黙的）:** 要件、ターゲット、優先度を示す表

| Requirement | Target | Priority |
| :--- | :--- | :--- |
| Monthly uptime | >= 99.9% | Must |
| RTO (Recovery Time Objective) | <= 15 minutes | Must |
| RPO (Recovery Point Objective) | <= 5 minutes | Must |
| Failover (AZ-level) | Automatic | Should |
| Data backup retention | 90 days | Must |

---
