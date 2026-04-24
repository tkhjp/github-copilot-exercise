"""Canonical spec for the 8 extraction test patterns (P1-P8).

Single source of truth: PIL renderer, python-pptx renderer, and the ground-truth
YAML emitter all consume this same dict. Edit here to change content; regenerate
artifacts with `python tests/text_vs_image/extraction/generate_extraction.py`.

Schema (each pattern):
  id:           "p01".."p08"
  title:        日本語 slide title
  pattern_name: short english label for debugging/logging
  description:  1-sentence human hint about the pattern
  facts:        list of {id, text} — the verbatim ground truth; fact.id starts
                with "{pid}_f" (e.g. "p01_f01"), fact.text is what Copilot
                must reproduce to earn a `present` verdict
  layout:       free-form dict consumed by renderers (shapes, positions, text);
                renderers define their own keys inside this dict
"""
from __future__ import annotations

from typing import Any


SPEC: dict[str, dict[str, Any]] = {
    "p01": {
        "id": "p01",
        "title": "勤怠アプリ画面レビュー",
        "pattern_name": "ui_callouts",
        "description": "アプリ画面 SS + 赤い矢印 4 本 + 吹き出し注釈 4 個",
        "layout": {
            "app_title": "勤怠管理",
            "header_user": "田中 太郎 さん",
            "table_header": ["日付", "出勤", "退勤", "実働", "ステータス"],
            "table_rows": [
                ["2026-04-01 (水)", "09:02", "18:15", "08:13", "承認済"],
                ["2026-04-02 (木)", "08:58", "19:40", "09:42", "承認待"],
                ["2026-04-03 (金)", "09:15", "17:50", "07:35", "要修正"],
                ["2026-04-04 (月)", "09:00", "18:00", "08:00", "承認済"],
            ],
            "buttons": ["エクスポート", "新規追加", "編集", "削除"],
            "callouts": [
                ("C1", "承認待の行に目立つ色を付けてください"),
                ("C2", "実働が 8 時間未満の行に警告アイコン"),
                ("C3", "エクスポートボタンをもっと右に寄せる"),
                ("C4", "日付の曜日表示は不要 (括弧削除)"),
            ],
            "subtitle": '勤怠管理 v3.2 - 田中太郎 | Screen-ID: TS-042',
            "footer": '© 2026 ACME Corp. / Confidential',
        },
        "facts": [
            {"id": "p01_f01", "text": "画面タイトルは「勤怠管理」"},
            {"id": "p01_f02", "text": "ログインユーザー表示は「田中 太郎 さん」"},
            {"id": "p01_f03", "text": "テーブルの列は 日付 / 出勤 / 退勤 / 実働 / ステータス"},
            {"id": "p01_f04", "text": "2026-04-01 (水) の出勤は 09:02"},
            {"id": "p01_f05", "text": "2026-04-01 (水) の退勤は 18:15"},
            {"id": "p01_f06", "text": "2026-04-01 (水) の実働は 08:13"},
            {"id": "p01_f07", "text": "2026-04-01 (水) のステータスは「承認済」"},
            {"id": "p01_f08", "text": "2026-04-02 (木) の実働は 09:42"},
            {"id": "p01_f09", "text": "2026-04-02 (木) のステータスは「承認待」"},
            {"id": "p01_f10", "text": "2026-04-03 (金) のステータスは「要修正」"},
            {"id": "p01_f11", "text": "2026-04-03 (金) の実働は 07:35"},
            {"id": "p01_f12", "text": "2026-04-04 (月) のステータスは「承認済」"},
            {"id": "p01_f13", "text": "ボタンは エクスポート / 新規追加 / 編集 / 削除 の 4 つ"},
            {"id": "p01_f14", "text": "変更要求 1: 承認待の行に目立つ色を付ける"},
            {"id": "p01_f15", "text": "変更要求 2: 実働が 8 時間未満の行に警告アイコン"},
            {"id": "p01_f16", "text": "変更要求 3: エクスポートボタンをもっと右に寄せる"},
            {"id": "p01_f17", "text": "変更要求 4: 日付の曜日表示 (括弧付き) は不要"},
            {"id": "p01_f18", "text": "吹き出しは赤色、番号 C1〜C4"},
            {"id": "p01_f19", "text": "画面は 4 行分のデータを表示"},
            {"id": "p01_f20", "text": "日付は 2026-04-01 から 2026-04-04 の連続日付 (土日除く)"},
            {"id": "p01_f21", "text": "スライド上部 (タイトル直下) の小さいメタ情報行: 勤怠管理 v3.2 - 田中太郎 | Screen-ID: TS-042"},
            {"id": "p01_f22", "text": "スライド下部のフッター: © 2026 ACME Corp. / Confidential"},
        ],
    },
    "p02": {
        "id": "p02",
        "title": "検索画面 Before / After 比較",
        "pattern_name": "before_after",
        "description": "旧/新の検索画面 SS を並べ、差分を赤矢印 3 本で指示",
        "layout": {
            "before": {
                "title": "Before (現行)",
                "search_placeholder": "キーワード入力",
                "button": "検索",
                "filter_rows": 1,
                "result_count_label": "結果: 12 件",
                "pagination": "< 1 2 3 >",
            },
            "after": {
                "title": "After (改修後)",
                "search_placeholder": "キーワードまたは商品コード",
                "button": "検索",
                "filter_rows": 3,
                "result_count_label": "結果: 12 件 / 並び順: 関連度順",
                "pagination": "< 1 2 3 4 5 … 20 >",
            },
            "diffs": [
                ("D1", "入力プレースホルダーに「商品コード」追加"),
                ("D2", "フィルタ行が 1 行 → 3 行に拡張"),
                ("D3", "ページネーションに省略記号 (…) と最終ページ追加"),
            ],
            "subtitle": 'TICKET-8421 | Review: 2026-03-15 | 鈴木 (UX Lead)',
            "footer": 'Design Review Doc v1.2 / Internal',
        },
        "facts": [
            {"id": "p02_f01", "text": "左側は「Before (現行)」、右側は「After (改修後)」"},
            {"id": "p02_f02", "text": "Before の検索プレースホルダーは「キーワード入力」"},
            {"id": "p02_f03", "text": "After の検索プレースホルダーは「キーワードまたは商品コード」"},
            {"id": "p02_f04", "text": "両方に「検索」ボタンがある"},
            {"id": "p02_f05", "text": "Before のフィルタは 1 行"},
            {"id": "p02_f06", "text": "After のフィルタは 3 行"},
            {"id": "p02_f07", "text": "Before の結果表示は「結果: 12 件」"},
            {"id": "p02_f08", "text": "After の結果表示は「結果: 12 件 / 並び順: 関連度順」"},
            {"id": "p02_f09", "text": "Before のページネーションは < 1 2 3 >"},
            {"id": "p02_f10", "text": "After のページネーションは < 1 2 3 4 5 … 20 >"},
            {"id": "p02_f11", "text": "差分 D1: プレースホルダーに「商品コード」追加"},
            {"id": "p02_f12", "text": "差分 D2: フィルタ 1 行 → 3 行"},
            {"id": "p02_f13", "text": "差分 D3: ページネーションに省略記号と最終ページ"},
            {"id": "p02_f14", "text": "差分矢印は赤色、番号 D1〜D3"},
            {"id": "p02_f15", "text": "差分矢印は Before/After 両側の対応要素を指している"},
            {"id": "p02_f16", "text": "両画面とも同じ結果件数 (12 件) を示している"},
            {"id": "p02_f17", "text": "スライドには Before と After の 2 つの画面が並んでいる"},
            {"id": "p02_f18", "text": "スライド上部 (タイトル直下) の小さいメタ情報行: TICKET-8421 | Review: 2026-03-15 | 鈴木 (UX Lead)"},
            {"id": "p02_f19", "text": "スライド下部のフッター: Design Review Doc v1.2 / Internal"},
        ],
    },
    "p03": {
        "id": "p03",
        "title": "購入フロー 5 画面操作手順",
        "pattern_name": "process_flow",
        "description": "ログイン→商品選択→カート→決済→完了 の 5 画面 SS を番号付き矢印で連結",
        "layout": {
            "steps": [
                ("S1", "ログイン", "メール + パスワード"),
                ("S2", "商品選択", "カテゴリ絞込 / 3 商品サムネイル"),
                ("S3", "カート", "2 商品、小計 ¥8,300"),
                ("S4", "決済", "クレジットカード / PayPay / コンビニ"),
                ("S5", "完了", "注文番号 ORD-2026-04-13579"),
            ],
            "subtitle": 'UI Build ui-v2.1 | Session timeout: 30 min | Updated 2026-04-10',
            "footer": 'User Research Team / Page 1 of 1',
        },
        "facts": [
            {"id": "p03_f01", "text": "5 画面の操作フローを示している"},
            {"id": "p03_f02", "text": "Step 1: ログイン画面"},
            {"id": "p03_f03", "text": "Step 1 の入力項目は「メール + パスワード」"},
            {"id": "p03_f04", "text": "Step 2: 商品選択画面"},
            {"id": "p03_f05", "text": "Step 2 にカテゴリ絞込がある"},
            {"id": "p03_f06", "text": "Step 2 には 3 商品のサムネイルが表示されている"},
            {"id": "p03_f07", "text": "Step 3: カート画面"},
            {"id": "p03_f08", "text": "カート内は 2 商品"},
            {"id": "p03_f09", "text": "カートの小計は ¥8,300"},
            {"id": "p03_f10", "text": "Step 4: 決済画面"},
            {"id": "p03_f11", "text": "決済方法はクレジットカード / PayPay / コンビニの 3 種"},
            {"id": "p03_f12", "text": "Step 5: 完了画面"},
            {"id": "p03_f13", "text": "注文番号は ORD-2026-04-13579"},
            {"id": "p03_f14", "text": "各画面間は番号付き矢印 S1→S2→S3→S4→S5 で連結"},
            {"id": "p03_f15", "text": "矢印は左から右への単方向"},
            {"id": "p03_f16", "text": "ステップ番号は S1 から S5 まで"},
            {"id": "p03_f17", "text": "スライド上部 (タイトル直下) の小さいメタ情報行: UI Build ui-v2.1 | Session timeout: 30 min | Updated 2026-04-10"},
            {"id": "p03_f18", "text": "スライド下部のフッター: User Research Team / Page 1 of 1"},
        ],
    },
    "p04": {
        "id": "p04",
        "title": "2026 Q1 売上ダッシュボード (注釈付き)",
        "pattern_name": "dashboard_annotated",
        "description": "棒グラフ + 円グラフ + KPI カード 3 枚 + 解釈吹き出し 3 個",
        "layout": {
            "bar_chart": {
                "title": "月別売上 (百万円)",
                "data": [("Jan", 120), ("Feb", 85), ("Mar", 160)],
            },
            "pie_chart": {
                "title": "地域別売上構成",
                "data": [("東京", 45), ("大阪", 28), ("名古屋", 17), ("その他", 10)],
            },
            "kpi_cards": [
                ("売上合計", "365 MJPY", "前年比 +12%"),
                ("新規顧客数", "2,140", "前年比 +8%"),
                ("解約率", "3.2%", "前年比 -0.5pt"),
            ],
            "annotations": [
                ("A1", "Feb が底、Mar で V 字回復"),
                ("A2", "東京集中 (45%) が課題"),
                ("A3", "解約率改善はサポート体制強化の効果"),
            ],
            "subtitle": 'Period: 2026 Q1 | Data as of 2026-03-31 23:59 JST | 次回更新: 翌営業日',
            "footer": 'Finance Team / Monthly Report / 2026-04 Issue',
        },
        "facts": [
            {"id": "p04_f01", "text": "棒グラフのタイトルは「月別売上 (百万円)」"},
            {"id": "p04_f02", "text": "Jan の売上は 120 (百万円)"},
            {"id": "p04_f03", "text": "Feb の売上は 85 (百万円)"},
            {"id": "p04_f04", "text": "Mar の売上は 160 (百万円)"},
            {"id": "p04_f05", "text": "円グラフのタイトルは「地域別売上構成」"},
            {"id": "p04_f06", "text": "東京が 45%"},
            {"id": "p04_f07", "text": "大阪が 28%"},
            {"id": "p04_f08", "text": "名古屋が 17%"},
            {"id": "p04_f09", "text": "その他が 10%"},
            {"id": "p04_f10", "text": "KPI: 売上合計 365 MJPY、前年比 +12%"},
            {"id": "p04_f11", "text": "KPI: 新規顧客数 2,140、前年比 +8%"},
            {"id": "p04_f12", "text": "KPI: 解約率 3.2%、前年比 -0.5pt"},
            {"id": "p04_f13", "text": "注釈 A1: Feb が底、Mar で V 字回復"},
            {"id": "p04_f14", "text": "注釈 A2: 東京集中 (45%) が課題"},
            {"id": "p04_f15", "text": "注釈 A3: 解約率改善はサポート体制強化の効果"},
            {"id": "p04_f16", "text": "注釈は 3 個 (A1-A3)"},
            {"id": "p04_f17", "text": "棒グラフ・円グラフ・KPI カードの 3 ブロック構成"},
            {"id": "p04_f18", "text": "KPI カードは 3 枚"},
            {"id": "p04_f19", "text": "スライド上部 (タイトル直下) の小さいメタ情報行: Period: 2026 Q1 | Data as of 2026-03-31 23:59 JST | 次回更新: 翌営業日"},
            {"id": "p04_f20", "text": "スライド下部のフッター: Finance Team / Monthly Report / 2026-04 Issue"},
        ],
    },
    "p05": {
        "id": "p05",
        "title": "決済システム 階層ドリルダウン",
        "pattern_name": "hierarchical_drilldown",
        "description": "上: システム全体 5 モジュール / 下: 決済コアモジュール拡大 + 設定パラメータ表",
        "layout": {
            "top_level_modules": [
                "認証",
                "商品カタログ",
                "決済コア",
                "通知",
                "分析",
            ],
            "highlighted_module": "決済コア",
            "zoom_submodules": [
                "PG アダプタ",
                "手数料計算",
                "リトライ制御",
                "ログ/監査",
            ],
            "config_table": {
                "columns": ["パラメータ", "現行値", "推奨値"],
                "rows": [
                    ["retry_max", "3", "5"],
                    ["timeout_sec", "10", "15"],
                    ["idempotency_key_ttl", "24h", "72h"],
                    ["log_retention", "30d", "180d"],
                ],
            },
            "subtitle": 'env: production-apac | Owner: Platform Team | Last audit: 2026-03-15',
            "footer": 'Platform Docs / Last modified: 2026-04-15',
        },
        "facts": [
            {"id": "p05_f01", "text": "上段のシステム全体図にモジュールが 5 つ配置されている"},
            {"id": "p05_f02", "text": "モジュール: 認証 / 商品カタログ / 決済コア / 通知 / 分析"},
            {"id": "p05_f03", "text": "下段で決済コアモジュールが拡大表示されている"},
            {"id": "p05_f04", "text": "決済コアのサブモジュールは 4 つ"},
            {"id": "p05_f05", "text": "サブモジュール: PG アダプタ / 手数料計算 / リトライ制御 / ログ/監査"},
            {"id": "p05_f06", "text": "設定パラメータ表の列は パラメータ / 現行値 / 推奨値"},
            {"id": "p05_f07", "text": "retry_max は現行 3、推奨 5"},
            {"id": "p05_f08", "text": "timeout_sec は現行 10、推奨 15"},
            {"id": "p05_f09", "text": "idempotency_key_ttl は現行 24h、推奨 72h"},
            {"id": "p05_f10", "text": "log_retention は現行 30d、推奨 180d"},
            {"id": "p05_f11", "text": "設定パラメータ表は 4 行"},
            {"id": "p05_f12", "text": "上段から下段への拡大関係 (ドリルダウン) が矢印で示されている"},
            {"id": "p05_f13", "text": "上段の 5 モジュール中、拡大対象は決済コアのみ"},
            {"id": "p05_f14", "text": "すべての推奨値は現行値より大きい方向への変更"},
            {"id": "p05_f15", "text": "階層は 2 段 (全体 → 特定モジュール)"},
            {"id": "p05_f16", "text": "スライド上部 (タイトル直下) の小さいメタ情報行: env: production-apac | Owner: Platform Team | Last audit: 2026-03-15"},
            {"id": "p05_f17", "text": "スライド下部のフッター: Platform Docs / Last modified: 2026-04-15"},
        ],
    },
    "p06": {
        "id": "p06",
        "title": "ダッシュボード デザインレビュー (赤入れ)",
        "pattern_name": "review_comments",
        "description": "ダッシュボードモック 1 枚 + 番号付き赤コメント 15 個 + 指示線",
        "layout": {
            "mockup_sections": [
                "ヘッダー (ロゴ + 通知)",
                "サイドナビ (5 項目)",
                "KPI カード (4 枚)",
                "売上推移グラフ",
                "最新取引テーブル",
                "フッター (リンク)",
            ],
            "comments": [
                ("R01", "ロゴは左寄せではなく中央"),
                ("R02", "通知アイコンに未読バッジ追加"),
                ("R03", "サイドナビの配色を背景色から白背景に"),
                ("R04", "KPI カードは 4 枚ではなく 3 枚に減らす"),
                ("R05", "KPI カードのフォントサイズを大きく"),
                ("R06", "グラフに前年比の点線を追加"),
                ("R07", "グラフの凡例を右上から下に移動"),
                ("R08", "テーブルのゼブラストライプを薄く"),
                ("R09", "テーブルヘッダーは sticky に"),
                ("R10", "取引金額の桁区切りカンマ必須"),
                ("R11", "金額のマイナスは赤字"),
                ("R12", "フッターのリンクは 3 つまで"),
                ("R13", "全体的にマージンを 16px → 24px"),
                ("R14", "モバイル対応のブレークポイント要確認"),
                ("R15", "ダークモード対応は別 issue で"),
            ],
            "subtitle": 'PR #2847 | Figma: 1920x1080 | Weekly Design Review 2026-04-10 15:00',
            "footer": 'Design System Team / Draft v0.7',
        },
        "facts": [
            {"id": "p06_f01", "text": "モックアップにはヘッダー / サイドナビ / KPI カード / 売上推移グラフ / 最新取引テーブル / フッターの 6 セクション"},
            {"id": "p06_f02", "text": "赤コメントは 15 個 (R01-R15)"},
            {"id": "p06_f03", "text": "R01: ロゴは左寄せではなく中央"},
            {"id": "p06_f04", "text": "R02: 通知アイコンに未読バッジ追加"},
            {"id": "p06_f05", "text": "R03: サイドナビの配色を背景色から白背景に"},
            {"id": "p06_f06", "text": "R04: KPI カードは 4 枚ではなく 3 枚に減らす"},
            {"id": "p06_f07", "text": "R05: KPI カードのフォントサイズを大きく"},
            {"id": "p06_f08", "text": "R06: グラフに前年比の点線を追加"},
            {"id": "p06_f09", "text": "R07: グラフの凡例を右上から下に移動"},
            {"id": "p06_f10", "text": "R08: テーブルのゼブラストライプを薄く"},
            {"id": "p06_f11", "text": "R09: テーブルヘッダーは sticky に"},
            {"id": "p06_f12", "text": "R10: 取引金額の桁区切りカンマ必須"},
            {"id": "p06_f13", "text": "R11: 金額のマイナスは赤字"},
            {"id": "p06_f14", "text": "R12: フッターのリンクは 3 つまで"},
            {"id": "p06_f15", "text": "R13: 全体的にマージンを 16px → 24px"},
            {"id": "p06_f16", "text": "R14: モバイル対応のブレークポイント要確認"},
            {"id": "p06_f17", "text": "R15: ダークモード対応は別 issue で"},
            {"id": "p06_f18", "text": "コメントは赤色の番号付き吹き出しで表示"},
            {"id": "p06_f19", "text": "指示線が対象要素と各コメントを結んでいる"},
            {"id": "p06_f20", "text": "スライド上部 (タイトル直下) の小さいメタ情報行: PR #2847 | Figma: 1920x1080 | Weekly Design Review 2026-04-10 15:00"},
            {"id": "p06_f21", "text": "スライド下部のフッター: Design System Team / Draft v0.7"},
        ],
    },
    "p07": {
        "id": "p07",
        "title": "混合ダッシュボードページ",
        "pattern_name": "mixed_dashboard",
        "description": "1 枚に表 + 棒グラフ + SS + コード片 + 箇条書きが散在",
        "layout": {
            "table": {
                "title": "地域別実績",
                "columns": ["地域", "売上", "成長率", "顧客数", "担当"],
                "rows": [
                    ["東京", "164M", "+12%", "1,240", "佐藤"],
                    ["大阪", "103M", "+8%", "820", "鈴木"],
                    ["名古屋", "62M", "+5%", "510", "高橋"],
                    ["福岡", "36M", "+15%", "310", "田中"],
                ],
            },
            "bar_chart": {
                "title": "Weekly active users",
                "data": [("W1", 3200), ("W2", 3450), ("W3", 3100), ("W4", 3680)],
            },
            "screenshot_caption": "プッシュ通知設定画面",
            "code_snippet": {
                "filename": "notify.py",
                "lines": [
                    "def send_push(user_id: str, msg: str) -> bool:",
                    "    if not _is_opted_in(user_id):",
                    "        return False",
                    "    return _provider.send(user_id, msg)",
                ],
            },
            "bullets": [
                "API レイテンシ p95 は 240ms",
                "エラー率 0.4% (先月比 -0.1pt)",
                "スパイクは水曜 14 時台",
            ],
            "subtitle": 'Period: 2026 Q1 | Total: 365M JPY | Code: Python 3.13',
            "footer": 'Analytics Dashboard / Confidential',
        },
        "facts": [
            {"id": "p07_f01", "text": "地域別実績表の列は 地域 / 売上 / 成長率 / 顧客数 / 担当"},
            {"id": "p07_f02", "text": "東京: 売上 164M、成長率 +12%、顧客数 1,240、担当 佐藤"},
            {"id": "p07_f03", "text": "大阪: 売上 103M、成長率 +8%、顧客数 820、担当 鈴木"},
            {"id": "p07_f04", "text": "名古屋: 売上 62M、成長率 +5%、顧客数 510、担当 高橋"},
            {"id": "p07_f05", "text": "福岡: 売上 36M、成長率 +15%、顧客数 310、担当 田中"},
            {"id": "p07_f06", "text": "棒グラフのタイトルは「Weekly active users」"},
            {"id": "p07_f07", "text": "W1: 3200"},
            {"id": "p07_f08", "text": "W2: 3450"},
            {"id": "p07_f09", "text": "W3: 3100"},
            {"id": "p07_f10", "text": "W4: 3680"},
            {"id": "p07_f11", "text": "スクリーンショットのキャプションは「プッシュ通知設定画面」"},
            {"id": "p07_f12", "text": "コード片のファイル名は notify.py"},
            {"id": "p07_f13", "text": "関数名は send_push"},
            {"id": "p07_f14", "text": "関数引数は user_id: str, msg: str"},
            {"id": "p07_f15", "text": "戻り値型は bool"},
            {"id": "p07_f16", "text": "_is_opted_in チェックがある"},
            {"id": "p07_f17", "text": "_provider.send を呼び出している"},
            {"id": "p07_f18", "text": "箇条書き: API レイテンシ p95 は 240ms"},
            {"id": "p07_f19", "text": "箇条書き: エラー率 0.4% (先月比 -0.1pt)"},
            {"id": "p07_f20", "text": "箇条書き: スパイクは水曜 14 時台"},
            {"id": "p07_f21", "text": "1 枚に表・棒グラフ・スクショ・コード・箇条書きの 5 種要素"},
            {"id": "p07_f22", "text": "スライド上部 (タイトル直下) の小さいメタ情報行: Period: 2026 Q1 | Total: 365M JPY | Code: Python 3.13"},
            {"id": "p07_f23", "text": "スライド下部のフッター: Analytics Dashboard / Confidential"},
        ],
    },
    "p08": {
        "id": "p08",
        "title": "組織図 (3 階層 10 ノード)",
        "pattern_name": "org_chart",
        "description": "3 階層の組織図 + 各ノードに氏名・役職・顔写真風サムネ",
        "layout": {
            "nodes": [
                # (id, level, name, role, parent)
                ("N01", 1, "山本 一郎", "CEO", None),
                ("N02", 2, "中村 次郎", "CTO", "N01"),
                ("N03", 2, "小林 三郎", "COO", "N01"),
                ("N04", 2, "加藤 四郎", "CFO", "N01"),
                ("N05", 3, "伊藤 花子", "Dev Manager", "N02"),
                ("N06", 3, "渡辺 梅子", "Infra Manager", "N02"),
                ("N07", 3, "山田 桜子", "Sales Head", "N03"),
                ("N08", 3, "佐々木 松子", "Ops Head", "N03"),
                ("N09", 3, "吉田 竹子", "Finance Head", "N04"),
                ("N10", 3, "井上 柳子", "Legal Head", "N04"),
            ],
            "subtitle": 'Effective: 2026-04-01 | Source: HRIS 2026-03-31 | ※ 2020 年以降の社員のみ表示',
            "footer": 'HR Org Chart / Effective 2026-04-01',
        },
        "facts": [
            {"id": "p08_f01", "text": "組織図は 3 階層"},
            {"id": "p08_f02", "text": "全ノード数は 10"},
            {"id": "p08_f03", "text": "第 1 階層: 山本 一郎 / CEO (1 名)"},
            {"id": "p08_f04", "text": "第 2 階層は 3 名: CTO / COO / CFO"},
            {"id": "p08_f05", "text": "CTO は 中村 次郎"},
            {"id": "p08_f06", "text": "COO は 小林 三郎"},
            {"id": "p08_f07", "text": "CFO は 加藤 四郎"},
            {"id": "p08_f08", "text": "第 3 階層は 6 名"},
            {"id": "p08_f09", "text": "CTO 配下: 伊藤 花子 (Dev Manager)、渡辺 梅子 (Infra Manager)"},
            {"id": "p08_f10", "text": "COO 配下: 山田 桜子 (Sales Head)、佐々木 松子 (Ops Head)"},
            {"id": "p08_f11", "text": "CFO 配下: 吉田 竹子 (Finance Head)、井上 柳子 (Legal Head)"},
            {"id": "p08_f12", "text": "各ノードには顔写真風のサムネイルが付いている"},
            {"id": "p08_f13", "text": "第 2 階層の 3 名は全員 CEO 直下"},
            {"id": "p08_f14", "text": "ノード間は線 (組織構造線) で結ばれている"},
            {"id": "p08_f15", "text": "役職 Dev Manager / Infra Manager / Sales Head / Ops Head / Finance Head / Legal Head の 6 種が第 3 階層"},
            {"id": "p08_f16", "text": "スライド上部 (タイトル直下) の小さいメタ情報行: Effective: 2026-04-01 | Source: HRIS 2026-03-31 | ※ 2020 年以降の社員のみ表示"},
            {"id": "p08_f17", "text": "スライド下部のフッター: HR Org Chart / Effective 2026-04-01"},
        ],
    },
}


from pathlib import Path
import yaml


def emit_ground_truth_yaml(out_path: Path) -> None:
    """Write the public-facing GT for every pattern to `out_path`.

    The YAML schema matches what `judge_extraction.py` expects:
      {pattern_id: {id, title, pattern_name, description, facts: [{id, text}, ...]}}

    The `layout` field is intentionally excluded — it is an internal artifact
    for the renderers and must not leak into the judge's ground truth (otherwise
    the judge would reward verbatim reproduction of layout metadata, not the
    content that a reader of the image would actually see).
    """
    public: dict[str, dict[str, Any]] = {}
    for pid, data in SPEC.items():
        public[pid] = {
            "id": data["id"],
            "title": data["title"],
            "pattern_name": data["pattern_name"],
            "description": data["description"],
            "facts": [{"id": f["id"], "text": f["text"]} for f in data["facts"]],
        }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(public, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
