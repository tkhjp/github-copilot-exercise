# tc04 — q8

**Question:** この文書ページに含まれるすべてのテキスト情報を教えてください。タイトル、各セクションの見出しと本文、箇条書きの各項目（数値を含む）、テーブルの全セルの値、ヘッダーとフッターの内容を具体的に挙げてください。


**Describe wall_seconds:** 59.18

## Output

提供された画像に基づき、文書ページに含まれるすべてのテキスト情報を以下に詳細に記述します。

---

### ヘッダー情報
*   **左上:** ACME Corp.
*   **右上:** Confidential — Draft v2.1

### タイトルとセクション見出し

**メインタイトル:**
System Requirements Specification

**章の見出し:**
Chapter 3: Non-Functional Requirements

**セクション見出し:**
3.1 Performance Requirements
3.2 Availability & Reliability

### 本文（段落テキスト）

*   **Chapter 3 の本文:** This chapter defines the non-functional requirements (NFRs) for the ShopApp e-commerce platform. These requirements apply to the production environment running on AWS ap-northeast-1 and must be met before the GA release scheduled for 2026 Q3.
*   **3.1 Performance Requirements の本文:** All API endpoints must meet the following latency and throughput targets under normal operating conditions (defined as <80% CPU utilization across the ECS cluster).
*   **3.2 Availability & Reliability の本文:** The system must achieve the uptime and recovery targets listed below. Planned maintenance windows (Sunday 02:00-06:00 JST) are excluded from the uptime calculation.

### 箇条書き（リスト項目）

**セクション 3.1 Performance Requirements 内の箇条書き:**
*   API response time (p95): < 200 ms
*   API response time (p99): < 500 ms
*   Search query throughput: >= 500 requests/sec
*   Database query timeout: 3 seconds (hard limit)
*   Page load time (LCP): <= 1.5 seconds on 4G network
*   Batch processing (nightly): complete within 2 hours

### テーブル情報

**テーブル名（暗黙的）:** Availability & Reliability Targets
| Requirement | Target | Priority |
| :--- | :--- | :--- |
| Monthly uptime | >= 99.9% | Must |
| RTO (Recovery Time Objective) | <= 15 minutes | Must |
| RPO (Recovery Point Objective) | <= 5 minutes | Must |
| Failover (AZ-level) | Automatic | Should |
| Data backup retention | 90 days | Must |

### フッター情報
*   **左下:** Page 12
*   **右下:** Last updated: 2026-03-15
