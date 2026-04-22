# tc03_judge — copilot_png  (judgment)

**Question:** この AWS アーキテクチャ図を観察し、視覚的な手がかりを使って以下に答えてください。
図から読み取れない情報を AWS の一般的な知識で補完することは禁止します。

(1) VPC 境界（紫色の点線矩形）の内側に配置されているコンポーネントと、外側に配置されているコンポーネントを列挙してください。
(2) 図の上から下への配置順序で、トラフィックが通る階層（最上流 → 最下流）を 4 層に分けて答えてください。
(3) 図に描かれている接続線（矢印）のうち、緑色で太い線と青緑/シアンで太い線がそれぞれ何を結んでいて、どのような意味の違いがあるかを答えてください。
(4) 図の凡例（下部のボックス）に列挙されているサブネット種別は何種類あり、それぞれ何色に対応していますか？

**Source:** Microsoft Copilot web, YYYY-MM-DD, input=tests/text_vs_image/images/03_complex_arch.png

## Output

以下は **画像に描かれている情報だけ** を使って答えています。AWS の一般知識による補完は一切していません。

---

## (1) VPC 境界の内側・外側にあるコンポーネント

### 🟪 **VPC（紫の点線）“内側” にあるもの**
図の紫色の点線矩形の中に視覚的に含まれている要素のみを列挙します。

- **Public Subnet（青）**
  - ALB（Application Load Balancer）
  - NAT Gateway（NAT GW）

- **Private Subnet (App)（黄）**
  - ECS Fargate App Service
  - ElastiCache Redis

- **DB Subnet（緑）**
  - RDS PostgreSQL Primary（AZ-a）
  - RDS PostgreSQL Read Replica（AZ-b）

- **VPC CIDR: 10.0.0.0/16**（ラベルとして内側に配置）

---

### 🟪 **VPC の“外側” にあるもの**
紫の点線の外側に描かれているもののみ。

- Route 53 DNS
- CloudFront CDN
- S3 Static Assets
- IAM Roles
- CloudWatch Logs / Metrics

---

## (2) 図の上から下への 4 層構造（トラフィックの流れ順）

図の縦方向のレイアウトに基づき、上から下へ 4 層に分割すると次のようになります。

1. **外部アクセス層（最上流）**  
   - Route 53 DNS  
   - CloudFront CDN  
   - S3 Static Assets  

2. **入口 / 公開層（Public Subnet）**  
   - ALB  
   - NAT Gateway（ただし NAT GW は外部向けではなく配置上の位置として）

3. **アプリケーション層（Private Subnet App）**  
   - ECS Fargate App Service  
   - ElastiCache Redis  

4. **データベース層（DB Subnet / 最下流）**  
   - RDS PostgreSQL Primary  
   - RDS PostgreSQL Read Replica  

---

## (3) 緑色の太線と青緑/シアンの太線の違い

図に描かれている太線を **色と接続先の視覚情報だけ** で比較します。

### 🟩 **緑色の太線**
- **ECS Fargate App Service → RDS PostgreSQL Primary（AZ-a）**
- **ECS Fargate App Service → RDS PostgreSQL Read Replica（AZ-b）**

**意味（図から読み取れる範囲）**  
- 緑色は **DB との通信** を表している  
- Primary へは **Write**  
- Read Replica へは **Read**  
（図中のラベルに “Write” “Read” と明記されている）

---

### 🟦 **青緑 / シアンの太線**
- **ECS Fargate App Service → ElastiCache Redis**

**意味（図から読み取れる範囲）**  
- 青緑の線は **Redis との通信** を表している  
- ラベルに **GET / SET** と書かれているため、キャッシュ操作を示す線

---

### 🎯 **違いのまとめ（図から読み取れる範囲のみ）**
- **緑色の太線**：DB（RDS）との Read / Write  
- **青緑の太線**：Redis との GET / SET  
- 色とラベルにより、通信対象と操作内容が異なることが示されている

---

## (4) 凡例に記載されているサブネット種別と色

図下部の凡例に描かれているボックスをそのまま読み取ると、次の 3 種類です。

| サブネット種別 | 色 |
|----------------|------|
| Public Subnet | 青 |
| Private Subnet (App) | 黄 |
| DB Subnet | 緑 |

※凡例には「Cache（ピンク）」もありますが、これはサブネット種別ではなく **ElastiCache のコンポーネント色** として描かれています。

---

必要であれば、この図から読み取れる依存関係や可用性の観点での特徴なども追加で分析できます。