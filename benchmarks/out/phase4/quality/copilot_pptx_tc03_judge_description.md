# tc03_judge — copilot_pptx  (judgment)

**Question:** この AWS アーキテクチャ図を観察し、視覚的な手がかりを使って以下に答えてください。
図から読み取れない情報を AWS の一般的な知識で補完することは禁止します。

(1) VPC 境界（紫色の点線矩形）の内側に配置されているコンポーネントと、外側に配置されているコンポーネントを列挙してください。
(2) 図の上から下への配置順序で、トラフィックが通る階層（最上流 → 最下流）を 4 層に分けて答えてください。
(3) 図に描かれている接続線（矢印）のうち、緑色で太い線と青緑/シアンで太い線がそれぞれ何を結んでいて、どのような意味の違いがあるかを答えてください。
(4) 図の凡例（下部のボックス）に列挙されているサブネット種別は何種類あり、それぞれ何色に対応していますか？

**Source:** Microsoft Copilot web, YYYY-MM-DD, input=tests/text_vs_image/inputs/03_complex_arch.pptx

## Output

了解したよ、kuanghuan。  
アップロードされた **アーキテクチャ図そのものだけ** を根拠に、視覚的に読み取れる情報だけで 4 問に答えるね。  
（引用文は図に実際に書かれているテキストから抜き出しているよ）

---

## (1) VPC 境界（紫色の点線）**内側**と**外側**のコンポーネント

### 🟪 **VPC 内側（紫色の点線矩形の中）**
図の中に明確に描かれている要素のみ：

- **Public Subnet（左右 2 つ）**  
  図には *「Public Subnet」* と明記されている 
  - ALB (AZ-a)  
  - ALB (AZ-b)  
  - NAT GW (AZ-a)  
  - NAT GW (AZ-b)

- **Private Subnet (App)（左右 2 つ）**  
  図には *「Private Subnet (App)」* と明記されている 
  - ECS Fargate App Service (AZ-a)  
  - ECS Fargate App Service (AZ-b)  
  - ElastiCache Redis（左右に 1 つずつ）

- **DB Subnet（左右 2 つ）**  
  図には *「DB Subnet」* と明記されている 
  - RDS PostgreSQL Primary  
  - RDS PostgreSQL Read Replica

---

### 🟦 **VPC 外側（紫色の点線の外）**
図の外側に配置されているもの：

- Route 53（DNS）  
- CloudFront（CDN）  
- S3（Static Assets）  
- IAM（Roles）  
- CloudWatch（Logs/Metrics）

これらは図の上部にあり、VPC 枠の外に描かれている。

---

## (2) 図の上から下への **4 層のトラフィック階層**

図の縦方向のレイアウトに従うと、明確に 4 つの層に分かれている。

### **① External / DNS / CDN 層（最上流）**
- Route 53  
- CloudFront  
- S3  
図の最上部に並んでいる。  
引用：*「Route 53」「CloudFront」「S3」* 

---

### **② Public Subnet（入口層）**
- ALB（AZ-a / AZ-b）  
- NAT GW（AZ-a / AZ-b）  
図の中央上部に配置されている。

---

### **③ Private Subnet (App)（アプリケーション層）**
- ECS Fargate App Service（左右）  
- ElastiCache Redis（左右）  
引用：*「ECS Fargate App Service」「ElastiCache Redis」* 

---

### **④ DB Subnet（データベース層・最下流）**
- RDS PostgreSQL Primary  
- RDS PostgreSQL Read Replica  
引用：*「RDS PostgreSQL Primary」「RDS PostgreSQL Read Replica」* 

---

## (3) 緑色の太線と青緑/シアンの太線の違い

図に描かれている線の意味を、**線の色とラベル**だけから読み取る。

### 🟩 **緑色の太線**
- **ECS Fargate App Service → RDS PostgreSQL Primary / Read Replica**
- ラベル：  
  - Primary へは *「write」*  
  - Read Replica へは *「read-only」*

引用：  
*「write」「read-only」* と線の上に明記されている 

➡ **意味：アプリから DB への読み書き通信を示す線**

---

### 🟦 **青緑/シアンの太線**
- **ECS Fargate App Service → ElastiCache Redis**
- ラベル：  
  - *「GET/SET」*

引用：  
*「GET/SET」* と線の上に明記されている 

➡ **意味：アプリから Redis へのキャッシュ操作（GET/SET）を示す線**

---

### 🔍 **違いのまとめ**
| 線の色 | 接続先 | ラベル | 意味 |
|-------|--------|--------|------|
| 緑 | RDS Primary / Read Replica | write / read-only | DB への読み書き |
| 青緑/シアン | ElastiCache Redis | GET/SET | キャッシュ操作 |

---

## (4) 図の凡例にあるサブネット種別と色

図の下部に凡例があり、そこにサブネット種別と色が示されている。

引用：  
凡例には *「Public Subnet」「Private Subnet (App)」「DB Subnet」* が色付きで並んでいる 

### **凡例にあるサブネット種別は 3 種類**
1. **Public Subnet**  
   - 色：青系（図中の Public Subnet と同じ色）

2. **Private Subnet (App)**  
   - 色：黄色系

3. **DB Subnet**  
   - 色：緑系

---

## 必要なら、同じ図を使って「可用性」「冗長性」「ボトルネック」などの観点でも分析できるよ。  
次に深掘りしたいポイントはある？