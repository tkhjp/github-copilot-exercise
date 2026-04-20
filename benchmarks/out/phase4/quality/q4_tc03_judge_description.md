# tc03_judge — q4  (judgment)

**Question:** この AWS アーキテクチャ図を観察し、視覚的な手がかりを使って以下に答えてください。
図から読み取れない情報を AWS の一般的な知識で補完することは禁止します。

(1) VPC 境界（紫色の点線矩形）の内側に配置されているコンポーネントと、外側に配置されているコンポーネントを列挙してください。
(2) 図の上から下への配置順序で、トラフィックが通る階層（最上流 → 最下流）を 4 層に分けて答えてください。
(3) 図に描かれている接続線（矢印）のうち、緑色で太い線と青緑/シアンで太い線がそれぞれ何を結んでいて、どのような意味の違いがあるかを答えてください。
(4) 図の凡例（下部のボックス）に列挙されているサブネット種別は何種類あり、それぞれ何色に対応していますか？


**Describe wall_seconds:** 44.74

## Output

提供されたAWSアーキテクチャ図に基づき、視覚的な手がかりのみを用いて回答します。

**(1) VPC 境界（紫色の点線矩形）の内側に配置されているコンポーネントと、外側に配置されているコンポーネントを列挙してください。**

*   **VPC 境界（紫色の点線矩形）の内部に配置されているコンポーネント:**
    *   Route 53 DNS (AZ-a, AZ-b)
    *   CloudFront CDN
    *   S3 Static Assets
    *   ALB (AZ-a), ALB (AZ-b)
    *   NAT GW (AZ-a), NAT GW (AZ-b)
    *   ECS Fargate App Service (AZ-a), ECS Fargate App Service (AZ-b)
    *   ElasticCache Redis (AZ-a), ElasticCache Redis (AZ-b)
    *   RDS PostgreSQL Primary
    *   RDS PostgreSQL Read Replica

*   **VPC 境界（紫色の点線矩形）の外側に配置されているコンポーネント:**
    *   IAM Roles
    *   CloudWatch Logs/Metrics

**(2) 図の上から下への配置順序で、トラフィックが通る階層（最上流 → 最下流）を 4 層に分けて答えてください。**

1.  Route 53 DNS / CloudFront CDN (最も上部)
2.  ALB / NAT GW (パブリックサブネットレベルのロードバランシング/ネットワーク機能)
3.  ECS Fargate App Service / ElasticCache Redis (アプリケーション層)
4.  RDS PostgreSQL Primary / Read Replica (データ永続化層)

**(3) 図に描かれている接続線（矢印）のうち、緑色で太い線と青緑/シアンで太い線がそれぞれ何を結んでいて、どのような意味の違いがあるかを答えてください。**

*   **緑色で太い線:**
    *   ECS Fargate App Service $\leftrightarrow$ ElasticCache Redis を結んでいます。
    *   これはアプリケーション層からキャッシュ層への通信を示しています。

*   **青緑/シアンで太い線:**
    *   ALB $\rightarrow$ ECS Fargate App Service (AZ-a) および ALB $\rightarrow$ ECS Fargate App Service (AZ-b) を結んでいます。
    *   これはロードバランサーからアプリケーションインスタンスへのトラフィックのルーティングを示しています。

**(4) 図の凡例（下部のボックス）に列挙されているサブネット種別は何種類あり、それぞれ何色に対応していますか？**

凡例には以下の4種類のサブネット種別が列挙されています。

1.  Public Subnet: **青色**
2.  Private Subnet (App): **黄緑色**
3.  DB Subnet: **水色/シアンに近い色**
4.  External / DNS: **薄い灰色（または白に近い色）**
