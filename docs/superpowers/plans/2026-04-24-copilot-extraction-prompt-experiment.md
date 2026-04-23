# Copilot Extraction Prompt Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the test corpus and evaluation pipeline for the Copilot verbatim-extraction prompt experiment, so the user can iterate on prompts via Copilot Web and get per-slide recall+hallucination scores.

**Architecture:** A single canonical spec file (`extraction_spec.py`) drives three parallel emitters (PIL for PNG, python-pptx for PPTX, yaml dump for GT). The Gemini judge from `phase4_quality_eval.py` is reused for recall scoring, plus a new hallucination-detection prompt. A per-prompt evaluation script consumes Copilot Web responses (MD files) and writes scores; a report script aggregates across prompts.

**Tech Stack:** Python 3.13 (pyenv), python-pptx 1.0.2, Pillow, PyYAML, google-genai (Gemini 2.5 Flash), pytest 8+, python-dotenv.

**Spec:** [docs/superpowers/specs/2026-04-24-copilot-extraction-prompt-design.md](../specs/2026-04-24-copilot-extraction-prompt-design.md)

---

## File Structure

**New source files** (all under `tests/text_vs_image/extraction/`):
- `extraction_spec.py` — canonical dict spec for 8 patterns (P1–P8)
- `generate_extraction.py` — PIL + python-pptx renderers + YAML emitter + CLI main
- `judge_extraction.py` — Copilot response → Gemini judge → per-slide scores
- `extraction_report.py` — cross-prompt comparison report (Markdown, Japanese)
- `README.md` — user workflow (日本語)
- `__init__.py` — empty, marks directory as module

**New test files** (pytest discoverable under `tests/`):
- `tests/text_vs_image/extraction/test_extraction_spec.py`
- `tests/text_vs_image/extraction/test_generate_extraction.py`
- `tests/text_vs_image/extraction/test_judge_extraction.py`

**Generated artifacts** (committed once so diffs are reviewable):
- `tests/text_vs_image/extraction/extraction_test.pptx` (1 file, 8 slides)
- `tests/text_vs_image/extraction/p01_ui_callouts.png` … `p08_org_chart.png` (8 PNGs)
- `tests/text_vs_image/extraction/ground_truth.yaml`

**Reused existing code** (imported, not modified):
- `tests/text_vs_image/phase4_quality_eval.py` — `JUDGE_PROMPT_EXTRACTION`, `judge_with_gemini`, `extract_json`, `_mode_and_agreement`, `_stdev`, `SCORE_MAP`
- `tests/text_vs_image/judge_pasted_descriptions.py` — reference pattern for "read MD → judge → scores.json"

**Runtime output** (gitignored, written by `judge_extraction.py`):
- `benchmarks/out/extraction/{prompt_id}/` — one dir per prompt trial, with pasted responses + scores

---

## Task 1: Scaffold directory + canonical spec for all 8 patterns

**Files:**
- Create: `tests/text_vs_image/extraction/__init__.py`
- Create: `tests/text_vs_image/extraction/extraction_spec.py`
- Create: `tests/text_vs_image/extraction/test_extraction_spec.py`

- [ ] **Step 1: Create empty `__init__.py`**

```bash
mkdir -p tests/text_vs_image/extraction
touch tests/text_vs_image/extraction/__init__.py
```

- [ ] **Step 2: Write the failing test first**

Create `tests/text_vs_image/extraction/test_extraction_spec.py`:

```python
"""Structural tests for the extraction_spec canonical dict."""
from __future__ import annotations

import pytest

from tests.text_vs_image.extraction import extraction_spec as spec_mod


EXPECTED_IDS = ["p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"]


def test_spec_has_all_8_patterns():
    assert list(spec_mod.SPEC.keys()) == EXPECTED_IDS


@pytest.mark.parametrize("pid", EXPECTED_IDS)
def test_pattern_has_required_fields(pid):
    p = spec_mod.SPEC[pid]
    assert p["id"] == pid
    assert isinstance(p["title"], str) and p["title"]
    assert isinstance(p["pattern_name"], str) and p["pattern_name"]
    assert isinstance(p["facts"], list) and len(p["facts"]) >= 15, \
        f"{pid} should have at least 15 GT facts, got {len(p['facts'])}"
    for f in p["facts"]:
        assert set(f.keys()) >= {"id", "text"}, f"{pid}/{f} missing id or text"
        assert f["id"].startswith(pid + "_f"), f"fact id must start with {pid}_f"


def test_fact_ids_are_unique_within_pattern():
    for pid, p in spec_mod.SPEC.items():
        ids = [f["id"] for f in p["facts"]]
        assert len(ids) == len(set(ids)), f"{pid} has duplicate fact ids"


def test_total_fact_count_is_in_expected_range():
    # Spec section 2.2 says ~225 total; allow 180-280 band for minor drift.
    total = sum(len(p["facts"]) for p in spec_mod.SPEC.values())
    assert 180 <= total <= 280, f"total facts {total} outside [180, 280]"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
python -m pytest tests/text_vs_image/extraction/test_extraction_spec.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tests.text_vs_image.extraction.extraction_spec'`

- [ ] **Step 4: Write the spec skeleton + P1 data**

Create `tests/text_vs_image/extraction/extraction_spec.py`:

```python
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
        ],
    },
    # P2-P8 filled in steps 5-7 below.
}
```

- [ ] **Step 5: Add P2-P4 spec entries**

Append to `extraction_spec.py` inside the `SPEC` dict (before the closing `}`):

```python
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
        ],
    },
```

- [ ] **Step 6: Add P5-P6 spec entries**

Append to `extraction_spec.py` inside the `SPEC` dict:

```python
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
        ],
    },
```

- [ ] **Step 7: Add P7-P8 spec entries**

Append to `extraction_spec.py` inside the `SPEC` dict, and close the top-level dict:

```python
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
        ],
    },
}
```

- [ ] **Step 8: Run test to verify it passes**

```bash
python -m pytest tests/text_vs_image/extraction/test_extraction_spec.py -v
```

Expected: PASS all 4 tests (test_spec_has_all_8_patterns, test_pattern_has_required_fields [parametrized 8x], test_fact_ids_are_unique_within_pattern, test_total_fact_count_is_in_expected_range).

- [ ] **Step 9: Commit**

```bash
git add tests/text_vs_image/extraction/__init__.py \
        tests/text_vs_image/extraction/extraction_spec.py \
        tests/text_vs_image/extraction/test_extraction_spec.py
git commit -m "feat(extraction): add canonical spec for 8 patterns (P1-P8)"
```

---

## Task 2: Ground-truth YAML emitter

**Files:**
- Modify: `tests/text_vs_image/extraction/extraction_spec.py` (add `emit_ground_truth_yaml()`)
- Modify: `tests/text_vs_image/extraction/test_extraction_spec.py` (add emitter tests)

- [ ] **Step 1: Write the failing test first**

Append to `test_extraction_spec.py`:

```python
import yaml
from pathlib import Path


def test_emit_ground_truth_yaml_round_trips(tmp_path: Path):
    out = tmp_path / "gt.yaml"
    spec_mod.emit_ground_truth_yaml(out)
    loaded = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    assert set(loaded.keys()) == {"p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"}
    # Each pattern has id, title, pattern_name, facts
    for pid, data in loaded.items():
        assert data["id"] == pid
        assert isinstance(data["facts"], list)
        assert all({"id", "text"} <= set(f) for f in data["facts"])


def test_emit_ground_truth_yaml_preserves_fact_order(tmp_path: Path):
    out = tmp_path / "gt.yaml"
    spec_mod.emit_ground_truth_yaml(out)
    loaded = yaml.safe_load(out.read_text(encoding="utf-8"))
    for pid, data in loaded.items():
        spec_ids = [f["id"] for f in spec_mod.SPEC[pid]["facts"]]
        yaml_ids = [f["id"] for f in data["facts"]]
        assert spec_ids == yaml_ids
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/text_vs_image/extraction/test_extraction_spec.py::test_emit_ground_truth_yaml_round_trips -v
```

Expected: FAIL — `AttributeError: module ... has no attribute 'emit_ground_truth_yaml'`

- [ ] **Step 3: Implement the emitter**

Append to `extraction_spec.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/text_vs_image/extraction/test_extraction_spec.py -v
```

Expected: PASS (new + existing tests).

- [ ] **Step 5: Commit**

```bash
git add tests/text_vs_image/extraction/extraction_spec.py \
        tests/text_vs_image/extraction/test_extraction_spec.py
git commit -m "feat(extraction): emit ground-truth YAML from canonical spec"
```

---

## Task 3: PIL rendering scaffold + shared helpers + P1 renderer

**Files:**
- Create: `tests/text_vs_image/extraction/generate_extraction.py`
- Create: `tests/text_vs_image/extraction/test_generate_extraction.py`

**Reference:** Mirror the coding style of [tests/text_vs_image/generate_test_images.py:319-477](../../../tests/text_vs_image/generate_test_images.py#L319) (the `make_ui_change_rfp` function) and its helpers `_font`, `_bold_font`, `_mono_font`, `_text_size`, `_arrow`, `_draw_callout`.

- [ ] **Step 1: Write the failing integration test first**

Create `tests/text_vs_image/extraction/test_generate_extraction.py`:

```python
"""Smoke tests for the extraction material generator.

These do NOT verify visual correctness — that must be eyeballed. They verify:
- Files are created at expected paths
- PNGs are valid images with expected dimensions
- PPTX has 8 slides
- Each PNG contains the slide title as visible text (via structural checks where possible)
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from tests.text_vs_image.extraction import generate_extraction as g


EXPECTED_PNG_NAMES = [
    "p01_ui_callouts.png",
    "p02_before_after.png",
    "p03_process_flow.png",
    "p04_dashboard_annotated.png",
    "p05_hierarchical_drilldown.png",
    "p06_review_comments.png",
    "p07_mixed_dashboard.png",
    "p08_org_chart.png",
]

CANVAS_W, CANVAS_H = 1600, 900  # All PNGs share the same aspect ratio so Copilot gets uniform framing.


@pytest.mark.parametrize("pid", ["p01"])  # Extended to p01-p08 after each renderer lands.
def test_render_png_produces_valid_image(tmp_path: Path, pid: str):
    out_path = tmp_path / f"{pid}.png"
    g.render_png(pid, out_path)
    assert out_path.exists(), f"{pid} PNG was not created"
    with Image.open(out_path) as img:
        assert img.size == (CANVAS_W, CANVAS_H), f"{pid} PNG size {img.size} != expected {(CANVAS_W, CANVAS_H)}"
        assert img.format == "PNG"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/text_vs_image/extraction/test_generate_extraction.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tests.text_vs_image.extraction.generate_extraction'`

- [ ] **Step 3: Create generate_extraction.py scaffold with shared PIL helpers**

Create `tests/text_vs_image/extraction/generate_extraction.py`:

```python
#!/usr/bin/env python
"""Generate PPTX + 8 PNGs + ground_truth.yaml for the extraction prompt experiment.

Single command produces all artifacts consumed by Copilot Web trials:

    python tests/text_vs_image/extraction/generate_extraction.py

All content flows from `extraction_spec.SPEC`. To change a slide, edit the spec
and re-run this script.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from tests.text_vs_image.extraction.extraction_spec import SPEC, emit_ground_truth_yaml


ROOT = Path(__file__).resolve().parent
CANVAS_W, CANVAS_H = 1600, 900

# Shared visual palette (kept deliberately muted so callouts stand out).
COLORS = {
    "bg":          "#ffffff",
    "card_bg":     "#f9fafb",
    "card_border": "#d1d5db",
    "text":        "#111827",
    "muted":       "#6b7280",
    "header_bg":   "#1e293b",
    "header_text": "#ffffff",
    "primary":     "#2563eb",
    "primary_dk":  "#1e40af",
    "success":     "#16a34a",
    "warn":        "#e67e22",
    "danger":      "#dc2626",
    "danger_bg":   "#fef2f2",
    "danger_text": "#991b1b",
    "grid":        "#e5e7eb",
}


def _font(size: int) -> ImageFont.ImageFont:
    """Load a Japanese-capable font. Falls back gracefully if unavailable."""
    for path in [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _bold_font(size: int) -> ImageFont.ImageFont:
    for path in [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",  # same TTC as _font; index 1 is bold on macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size, index=1 if path.endswith(".ttc") else 0)
        except OSError:
            continue
    return _font(size)


def _mono_font(size: int) -> ImageFont.ImageFont:
    for path in ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf"]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _tsize(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _arrow(draw: ImageDraw.ImageDraw, p1, p2, color="black", width=2, head=12):
    draw.line([p1, p2], fill=color, width=width)
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    a1 = (p2[0] - head * math.cos(ang - math.radians(22)),
          p2[1] - head * math.sin(ang - math.radians(22)))
    a2 = (p2[0] - head * math.cos(ang + math.radians(22)),
          p2[1] - head * math.sin(ang + math.radians(22)))
    draw.polygon([p2, a1, a2], fill=color)


def _draw_screenshot_card(
    draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], *,
    title: str | None = None, title_font=None, body_font=None,
):
    """Draw a 'screenshot card' rectangle with an optional title bar and muted border.
    Body content is drawn by the caller by reading the spec and calling further primitives.
    """
    x1, y1, x2, y2 = rect
    draw.rectangle([x1, y1, x2, y2], fill=COLORS["card_bg"], outline=COLORS["card_border"], width=2)
    if title:
        tf = title_font or _bold_font(14)
        draw.rectangle([x1, y1, x2, y1 + 32], fill=COLORS["header_bg"])
        draw.text((x1 + 12, y1 + 8), title, fill=COLORS["header_text"], font=tf)


def _draw_callout(
    draw: ImageDraw.ImageDraw, *,
    box_rect: tuple[int, int, int, int],
    label: str,
    text: str,
    target: tuple[int, int],
    font=None,
    color=COLORS["danger"],
    fill=COLORS["danger_bg"],
    text_color=COLORS["danger_text"],
):
    """Red callout box with label (e.g. 'C1') + text + leader line to target point."""
    x1, y1, x2, y2 = box_rect
    draw.rectangle([x1, y1, x2, y2], fill=fill, outline=color, width=2)
    f = font or _bold_font(13)
    draw.text((x1 + 10, y1 + 8), f"{label} {text}", fill=text_color, font=f)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    _arrow(draw, (cx, cy), target, color=color, width=2, head=10)


def _new_canvas() -> Image.Image:
    return Image.new("RGB", (CANVAS_W, CANVAS_H), COLORS["bg"])


def _draw_slide_title(draw: ImageDraw.ImageDraw, title: str, subtitle: str | None = None) -> int:
    """Draw the slide title bar; return y-offset where body content can start."""
    draw.text((32, 22), title, fill=COLORS["text"], font=_bold_font(26))
    if subtitle:
        draw.text((32, 60), subtitle, fill=COLORS["muted"], font=_font(14))
    draw.line([(32, 86), (CANVAS_W - 32, 86)], fill=COLORS["grid"], width=2)
    return 100  # body starts here


# --- Per-pattern renderers (p01-p08). Each reads SPEC[pid]['layout'] and draws to an Image. ---

def render_p01(out_path: Path) -> None:
    """P1: UI/画面レビュー型 — 勤怠アプリ画面 SS + 赤矢印 4 本 + 吹き出し 4 個."""
    spec = SPEC["p01"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Screenshot card (left ~60% of canvas).
    card = (40, body_y + 10, 1000, body_y + 700)
    _draw_screenshot_card(draw, card, title=layout["app_title"])
    # Header inside card: user name (right-aligned inside header bar).
    hdr_user_w, _ = _tsize(draw, layout["header_user"], _font(13))
    draw.text((card[2] - hdr_user_w - 14, body_y + 18), layout["header_user"],
              fill=COLORS["header_text"], font=_font(13))

    # Table (5 columns, 4 rows).
    tbl_x1, tbl_y1 = card[0] + 24, body_y + 60
    tbl_x2 = card[2] - 24
    col_widths = [190, 110, 110, 110, 140]
    row_h = 42
    # Header row
    hx = tbl_x1
    for header in layout["table_header"]:
        draw.rectangle([hx, tbl_y1, hx + col_widths[layout["table_header"].index(header)], tbl_y1 + row_h],
                       fill=COLORS["grid"], outline=COLORS["card_border"])
        draw.text((hx + 10, tbl_y1 + 12), header, fill=COLORS["text"], font=_bold_font(14))
        hx += col_widths[layout["table_header"].index(header)]
    # Data rows
    for r, row in enumerate(layout["table_rows"]):
        ry = tbl_y1 + row_h * (r + 1)
        rx = tbl_x1
        for ci, val in enumerate(row):
            draw.rectangle([rx, ry, rx + col_widths[ci], ry + row_h],
                           fill=COLORS["bg"], outline=COLORS["card_border"])
            draw.text((rx + 10, ry + 12), val, fill=COLORS["text"], font=_font(13))
            rx += col_widths[ci]
    # Action buttons
    btn_y = tbl_y1 + row_h * (len(layout["table_rows"]) + 1) + 24
    bx = tbl_x1
    for label in layout["buttons"]:
        w, _ = _tsize(draw, label, _bold_font(13))
        bw = w + 24
        draw.rectangle([bx, btn_y, bx + bw, btn_y + 32],
                       fill=COLORS["primary"], outline=COLORS["primary_dk"], width=2)
        draw.text((bx + 12, btn_y + 7), label, fill=COLORS["header_text"], font=_bold_font(13))
        bx += bw + 10

    # 4 red callouts on the right ~35% of canvas, each pointing at a region in the card.
    # Target coordinates are approximate anchors inside the card for each callout.
    targets = [
        (tbl_x1 + 600, tbl_y1 + row_h * 2 + row_h // 2),  # C1: row 2 (承認待)
        (tbl_x1 + 480, tbl_y1 + row_h * 3 + row_h // 2),  # C2: row 3 (要修正)
        (tbl_x1 + 80, btn_y + 16),                        # C3: エクスポートボタン
        (tbl_x1 + 90, tbl_y1 + 12),                       # C4: 日付列ヘッダ
    ]
    for i, (label, text) in enumerate(layout["callouts"]):
        bx1 = 1040
        by1 = body_y + 20 + i * 170
        _draw_callout(draw, box_rect=(bx1, by1, bx1 + 520, by1 + 110),
                      label=label, text=text, target=targets[i])

    img.save(out_path, "PNG")


def render_png(pid: str, out_path: Path) -> None:
    """Dispatch table mapping pattern id → per-pattern renderer."""
    renderers = {
        "p01": render_p01,
        # p02..p08 added in later tasks.
    }
    if pid not in renderers:
        raise NotImplementedError(f"render_png not yet implemented for {pid}")
    renderers[pid](out_path)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/text_vs_image/extraction/test_generate_extraction.py -v
```

Expected: PASS for p01 only.

- [ ] **Step 5: Visual sanity check**

```bash
python -c "
from pathlib import Path
from tests.text_vs_image.extraction.generate_extraction import render_png
out = Path('/tmp/p01_sanity.png')
render_png('p01', out)
print(f'wrote {out} ({out.stat().st_size} bytes)')
"
open /tmp/p01_sanity.png
```

Expected: A single PNG showing a slide with title "勤怠アプリ画面レビュー", a screenshot card on the left with a 5-column table of 4 rows + 4 action buttons, and 4 red callout boxes on the right with leader arrows pointing into the table/buttons. Text must be readable; Japanese characters must render correctly.

- [ ] **Step 6: Commit**

```bash
git add tests/text_vs_image/extraction/generate_extraction.py \
        tests/text_vs_image/extraction/test_generate_extraction.py
git commit -m "feat(extraction): PIL renderer + P1 (UI callouts) slide"
```

---

## Task 4: PIL renderers for P2-P4

**Files:**
- Modify: `tests/text_vs_image/extraction/generate_extraction.py` (add `render_p02`, `render_p03`, `render_p04` + update dispatch table)
- Modify: `tests/text_vs_image/extraction/test_generate_extraction.py` (extend parametrize)

- [ ] **Step 1: Extend the test parametrize to cover p02-p04**

In `test_generate_extraction.py`, change the `@pytest.mark.parametrize` line:

```python
@pytest.mark.parametrize("pid", ["p01", "p02", "p03", "p04"])
```

- [ ] **Step 2: Run test to verify p02-p04 fail**

```bash
python -m pytest tests/text_vs_image/extraction/test_generate_extraction.py -v
```

Expected: FAIL with `NotImplementedError: render_png not yet implemented for p02` (and p03, p04).

- [ ] **Step 3: Implement render_p02 (Before/After)**

Add to `generate_extraction.py` (after `render_p01`):

```python
def render_p02(out_path: Path) -> None:
    """P2: Before/After 比較 — 2 つの検索画面 SS を左右並べて差分矢印 3 本."""
    spec = SPEC["p02"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Two screenshot cards side by side.
    gap = 40
    card_w = (CANVAS_W - 3 * gap) // 2
    before = (gap, body_y + 10, gap + card_w, body_y + 660)
    after = (2 * gap + card_w, body_y + 10, 2 * gap + 2 * card_w, body_y + 660)

    for card, side_key in [(before, "before"), (after, "after")]:
        s = layout[side_key]
        _draw_screenshot_card(draw, card, title=s["title"])
        # Search bar
        sx1, sy = card[0] + 24, card[1] + 60
        draw.rectangle([sx1, sy, card[2] - 140, sy + 36],
                       fill=COLORS["bg"], outline=COLORS["card_border"], width=2)
        draw.text((sx1 + 10, sy + 10), s["search_placeholder"], fill=COLORS["muted"], font=_font(13))
        # Search button
        draw.rectangle([card[2] - 130, sy, card[2] - 24, sy + 36],
                       fill=COLORS["primary"], outline=COLORS["primary_dk"], width=2)
        bw, _ = _tsize(draw, s["button"], _bold_font(13))
        draw.text((card[2] - 77 - bw // 2, sy + 10), s["button"],
                  fill=COLORS["header_text"], font=_bold_font(13))
        # Filter rows (small boxes)
        fy = sy + 60
        for _i in range(s["filter_rows"]):
            draw.rectangle([sx1, fy, card[2] - 24, fy + 28],
                           fill=COLORS["card_bg"], outline=COLORS["card_border"])
            fy += 36
        # Results label
        draw.text((sx1, fy + 20), s["result_count_label"], fill=COLORS["text"], font=_font(13))
        # Pagination
        draw.text((sx1, fy + 60), s["pagination"], fill=COLORS["text"], font=_bold_font(14))

    # 3 red diff arrows with labels D1..D3. Targets: placeholder (both sides), filter area, pagination.
    diff_targets = [
        ((before[0] + 80, body_y + 86), (after[0] + 80, body_y + 86)),
        ((before[0] + 80, body_y + 140), (after[0] + 80, body_y + 180)),
        ((before[0] + 200, body_y + 520), (after[0] + 300, body_y + 520)),
    ]
    for i, (label, text) in enumerate(layout["diffs"]):
        y = CANVAS_H - 220 + i * 60
        # Label box below the cards
        draw.rectangle([40, y, 280, y + 44], fill=COLORS["danger_bg"], outline=COLORS["danger"], width=2)
        draw.text((50, y + 12), f"{label} {text}", fill=COLORS["danger_text"], font=_bold_font(13))
        # Short arrows from label to both before and after targets
        for target in diff_targets[i]:
            _arrow(draw, (280, y + 22), target, color=COLORS["danger"], width=2, head=10)

    img.save(out_path, "PNG")
```

- [ ] **Step 4: Implement render_p03 (Process Flow)**

Add to `generate_extraction.py`:

```python
def render_p03(out_path: Path) -> None:
    """P3: 工程フロー型 — 5 画面 SS を番号付き矢印で連結."""
    spec = SPEC["p03"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # 5 mini screenshots in a single row, connected by arrows.
    steps = layout["steps"]
    n = len(steps)
    margin = 40
    gap = 48
    card_w = (CANVAS_W - 2 * margin - (n - 1) * gap) // n
    card_h = 400
    y1 = body_y + 120
    y2 = y1 + card_h
    for i, (label, step_title, step_desc) in enumerate(steps):
        x1 = margin + i * (card_w + gap)
        x2 = x1 + card_w
        _draw_screenshot_card(draw, (x1, y1, x2, y2), title=step_title)
        # Body of card: wrap step_desc
        draw.text((x1 + 12, y1 + 48), step_desc, fill=COLORS["text"], font=_font(13))
        # Step label above card
        draw.rectangle([x1 + card_w // 2 - 24, y1 - 40, x1 + card_w // 2 + 24, y1 - 8],
                       fill=COLORS["primary"], outline=COLORS["primary_dk"], width=2)
        lw, _ = _tsize(draw, label, _bold_font(16))
        draw.text((x1 + card_w // 2 - lw // 2, y1 - 33), label,
                  fill=COLORS["header_text"], font=_bold_font(16))
        # Arrow to next card
        if i < n - 1:
            _arrow(draw, (x2 + 4, (y1 + y2) // 2),
                   (x2 + gap - 4, (y1 + y2) // 2),
                   color=COLORS["text"], width=3, head=14)

    img.save(out_path, "PNG")
```

- [ ] **Step 5: Implement render_p04 (Dashboard annotated)**

Add to `generate_extraction.py`:

```python
def render_p04(out_path: Path) -> None:
    """P4: ダッシュボード + 解釈注釈 — 棒 + 円 + KPI 3 + 吹き出し 3."""
    spec = SPEC["p04"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Bar chart (top-left)
    bx1, by1 = 40, body_y + 40
    bx2, by2 = 640, by1 + 300
    _draw_screenshot_card(draw, (bx1, by1, bx2, by2), title=layout["bar_chart"]["title"])
    bars = layout["bar_chart"]["data"]
    max_v = max(v for _, v in bars)
    chart_top = by1 + 60
    chart_bot = by2 - 40
    chart_left = bx1 + 40
    chart_right = bx2 - 20
    draw.line([(chart_left, chart_bot), (chart_right, chart_bot)], fill=COLORS["text"], width=2)
    draw.line([(chart_left, chart_top), (chart_left, chart_bot)], fill=COLORS["text"], width=2)
    bar_area_w = chart_right - chart_left - 40
    bar_w = bar_area_w // (len(bars) * 2)
    for i, (lbl, v) in enumerate(bars):
        x = chart_left + 20 + i * (bar_w * 2)
        h = int((v / max_v) * (chart_bot - chart_top - 20))
        draw.rectangle([x, chart_bot - h, x + bar_w, chart_bot], fill=COLORS["primary"])
        draw.text((x, chart_bot - h - 18), str(v), fill=COLORS["text"], font=_font(12))
        draw.text((x + bar_w // 4, chart_bot + 6), lbl, fill=COLORS["text"], font=_font(12))

    # Pie chart (top-right) — rendered as wedges
    cx, cy, r = 1080, by1 + 160, 100
    pie = layout["pie_chart"]
    _draw_screenshot_card(draw, (800, by1, CANVAS_W - 40, by2), title=pie["title"])
    total = sum(v for _, v in pie["data"])
    start_angle = -90
    palette = [COLORS["primary"], COLORS["success"], COLORS["warn"], COLORS["muted"]]
    for i, (label, v) in enumerate(pie["data"]):
        sweep = (v / total) * 360
        draw.pieslice([cx - r, cy - r, cx + r, cy + r],
                      start=start_angle, end=start_angle + sweep,
                      fill=palette[i % len(palette)], outline=COLORS["bg"], width=2)
        # Label with % outside the wedge
        mid = math.radians(start_angle + sweep / 2)
        lx = cx + int((r + 30) * math.cos(mid))
        ly = cy + int((r + 30) * math.sin(mid))
        draw.text((lx - 20, ly - 8), f"{label} {v}%", fill=COLORS["text"], font=_font(12))
        start_angle += sweep

    # KPI cards (3 cards across bottom)
    kpi_y1 = by2 + 30
    kpi_y2 = kpi_y1 + 160
    kpi_w = (CANVAS_W - 2 * 40 - 2 * 20) // 3
    for i, (kpi_label, kpi_val, kpi_sub) in enumerate(layout["kpi_cards"]):
        kx1 = 40 + i * (kpi_w + 20)
        kx2 = kx1 + kpi_w
        _draw_screenshot_card(draw, (kx1, kpi_y1, kx2, kpi_y2))
        draw.text((kx1 + 16, kpi_y1 + 16), kpi_label, fill=COLORS["muted"], font=_bold_font(14))
        draw.text((kx1 + 16, kpi_y1 + 48), kpi_val, fill=COLORS["text"], font=_bold_font(28))
        draw.text((kx1 + 16, kpi_y1 + 100), kpi_sub, fill=COLORS["success"], font=_font(13))

    # 3 interpretive callouts on the right margin, each with a label (A1..A3)
    for i, (label, text) in enumerate(layout["annotations"]):
        ay = kpi_y2 + 20 + i * 44
        draw.rectangle([40, ay, CANVAS_W - 40, ay + 36],
                       fill=COLORS["danger_bg"], outline=COLORS["danger"], width=1)
        draw.text((52, ay + 8), f"{label} {text}", fill=COLORS["danger_text"], font=_bold_font(13))

    img.save(out_path, "PNG")
```

- [ ] **Step 6: Register p02-p04 in the dispatch table**

In `generate_extraction.py`, update the `render_png` function:

```python
def render_png(pid: str, out_path: Path) -> None:
    renderers = {
        "p01": render_p01,
        "p02": render_p02,
        "p03": render_p03,
        "p04": render_p04,
    }
    if pid not in renderers:
        raise NotImplementedError(f"render_png not yet implemented for {pid}")
    renderers[pid](out_path)
```

- [ ] **Step 7: Run tests to verify all pass**

```bash
python -m pytest tests/text_vs_image/extraction/test_generate_extraction.py -v
```

Expected: PASS for p01-p04.

- [ ] **Step 8: Visual sanity check all three**

```bash
python -c "
from pathlib import Path
from tests.text_vs_image.extraction.generate_extraction import render_png
for pid in ['p02', 'p03', 'p04']:
    render_png(pid, Path(f'/tmp/{pid}_sanity.png'))
    print(f'wrote /tmp/{pid}_sanity.png')
"
open /tmp/p02_sanity.png /tmp/p03_sanity.png /tmp/p04_sanity.png
```

Expected:
- `p02_sanity.png`: two search-UI cards side-by-side with 3 red D1-D3 labels at the bottom pointing up into both sides
- `p03_sanity.png`: 5 step cards in a row (ログイン, 商品選択, カート, 決済, 完了) with arrows between them; step labels S1-S5 above each card
- `p04_sanity.png`: bar chart top-left (Jan/Feb/Mar), pie chart top-right (4 wedges), 3 KPI cards middle, 3 red callout rows at bottom (A1-A3)

- [ ] **Step 9: Commit**

```bash
git add tests/text_vs_image/extraction/generate_extraction.py \
        tests/text_vs_image/extraction/test_generate_extraction.py
git commit -m "feat(extraction): PIL renderers for P2-P4 (before/after, process flow, dashboard)"
```

---

## Task 5: PIL renderers for P5-P8

**Files:**
- Modify: `tests/text_vs_image/extraction/generate_extraction.py`
- Modify: `tests/text_vs_image/extraction/test_generate_extraction.py`

- [ ] **Step 1: Extend parametrize to cover all 8**

In `test_generate_extraction.py`:

```python
@pytest.mark.parametrize("pid", ["p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"])
```

- [ ] **Step 2: Run tests to confirm p05-p08 fail**

```bash
python -m pytest tests/text_vs_image/extraction/test_generate_extraction.py -v
```

Expected: FAIL with `NotImplementedError` for p05-p08.

- [ ] **Step 3: Implement render_p05 (Hierarchical drilldown)**

Add to `generate_extraction.py`:

```python
def render_p05(out_path: Path) -> None:
    """P5: 階層ドリルダウン — 上: 5 モジュール全体図 / 下: 決済コア拡大 + 設定表."""
    spec = SPEC["p05"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Top band: 5 modules side by side. Highlighted one has a different border.
    modules = layout["top_level_modules"]
    highlighted = layout["highlighted_module"]
    n = len(modules)
    mod_y1 = body_y + 20
    mod_y2 = mod_y1 + 120
    mod_w = (CANVAS_W - 2 * 40 - (n - 1) * 20) // n
    for i, name in enumerate(modules):
        mx1 = 40 + i * (mod_w + 20)
        mx2 = mx1 + mod_w
        is_hi = (name == highlighted)
        draw.rectangle(
            [mx1, mod_y1, mx2, mod_y2],
            fill=COLORS["card_bg"],
            outline=COLORS["danger"] if is_hi else COLORS["card_border"],
            width=3 if is_hi else 2,
        )
        nw, _ = _tsize(draw, name, _bold_font(15))
        draw.text((mx1 + (mod_w - nw) // 2, mod_y1 + 50), name,
                  fill=COLORS["text"], font=_bold_font(15))

    # Drilldown arrow from highlighted module to zoomed area below
    hi_idx = modules.index(highlighted)
    hi_cx = 40 + hi_idx * (mod_w + 20) + mod_w // 2
    _arrow(draw, (hi_cx, mod_y2 + 4), (CANVAS_W // 2, mod_y2 + 60),
           color=COLORS["danger"], width=3, head=14)

    # Zoomed submodules (left half, grid of 2x2)
    zoom_y1 = mod_y2 + 80
    zoom_y2 = zoom_y1 + 380
    _draw_screenshot_card(draw, (40, zoom_y1, 700, zoom_y2),
                          title=f"拡大: {highlighted}")
    sub = layout["zoom_submodules"]
    for i, name in enumerate(sub):
        r, c = divmod(i, 2)
        sx1 = 80 + c * 290
        sy1 = zoom_y1 + 60 + r * 130
        draw.rectangle([sx1, sy1, sx1 + 260, sy1 + 100],
                       fill=COLORS["bg"], outline=COLORS["card_border"], width=2)
        nw, _ = _tsize(draw, name, _bold_font(14))
        draw.text((sx1 + (260 - nw) // 2, sy1 + 40), name,
                  fill=COLORS["text"], font=_bold_font(14))

    # Config table (right half)
    tbl_x1, tbl_y1 = 740, zoom_y1
    tbl_x2, tbl_y2 = CANVAS_W - 40, zoom_y2
    _draw_screenshot_card(draw, (tbl_x1, tbl_y1, tbl_x2, tbl_y2), title="設定パラメータ")
    cfg = layout["config_table"]
    col_widths = [320, 200, 200]
    hx = tbl_x1 + 12
    hy = tbl_y1 + 60
    # Header
    for ci, col in enumerate(cfg["columns"]):
        draw.rectangle([hx, hy, hx + col_widths[ci], hy + 36],
                       fill=COLORS["grid"], outline=COLORS["card_border"])
        draw.text((hx + 8, hy + 10), col, fill=COLORS["text"], font=_bold_font(14))
        hx += col_widths[ci]
    # Rows
    for r, row in enumerate(cfg["rows"]):
        rx = tbl_x1 + 12
        ry = hy + 36 * (r + 1)
        for ci, val in enumerate(row):
            draw.rectangle([rx, ry, rx + col_widths[ci], ry + 36],
                           fill=COLORS["bg"], outline=COLORS["card_border"])
            draw.text((rx + 8, ry + 10), val, fill=COLORS["text"], font=_font(13))
            rx += col_widths[ci]

    img.save(out_path, "PNG")
```

- [ ] **Step 4: Implement render_p06 (Review comments)**

Add to `generate_extraction.py`:

```python
def render_p06(out_path: Path) -> None:
    """P6: レビュー反映 (赤入れ) — モック 1 + 15 個の赤コメント + 指示線."""
    spec = SPEC["p06"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Left: mockup placeholder with 6 stacked sections (labels only, for the judge to read).
    mock_x1, mock_y1 = 40, body_y + 10
    mock_x2, mock_y2 = 780, body_y + 720
    _draw_screenshot_card(draw, (mock_x1, mock_y1, mock_x2, mock_y2), title="ダッシュボード モックアップ")
    sections = layout["mockup_sections"]
    sec_h = (mock_y2 - mock_y1 - 32) // len(sections)
    for i, sec in enumerate(sections):
        sy1 = mock_y1 + 32 + i * sec_h
        sy2 = sy1 + sec_h - 4
        draw.rectangle([mock_x1 + 16, sy1, mock_x2 - 16, sy2],
                       fill=COLORS["bg"], outline=COLORS["card_border"], width=1)
        draw.text((mock_x1 + 28, sy1 + 12), sec, fill=COLORS["text"], font=_bold_font(14))

    # Right: 15 review comment bubbles, two-column layout.
    comments = layout["comments"]
    comment_x1 = 800
    comment_w = (CANVAS_W - comment_x1 - 40 - 10) // 2
    for i, (label, text) in enumerate(comments):
        col = i % 2
        row = i // 2
        cx1 = comment_x1 + col * (comment_w + 10)
        cy1 = body_y + 20 + row * 90
        draw.rectangle([cx1, cy1, cx1 + comment_w, cy1 + 78],
                       fill=COLORS["danger_bg"], outline=COLORS["danger"], width=2)
        draw.text((cx1 + 10, cy1 + 8), label, fill=COLORS["danger_text"], font=_bold_font(13))
        # Wrap text across up to 2 lines manually (approximate).
        draw.text((cx1 + 10, cy1 + 32), text[:40], fill=COLORS["danger_text"], font=_font(12))
        if len(text) > 40:
            draw.text((cx1 + 10, cy1 + 52), text[40:80], fill=COLORS["danger_text"], font=_font(12))
        # Thin leader line toward the mockup (approximate, aimed at section based on comment index).
        target_section_idx = i % len(sections)
        target_y = mock_y1 + 32 + target_section_idx * sec_h + sec_h // 2
        _arrow(draw, (cx1, cy1 + 40), (mock_x2, target_y),
               color=COLORS["danger"], width=1, head=6)

    img.save(out_path, "PNG")
```

- [ ] **Step 5: Implement render_p07 (Mixed dashboard)**

Add to `generate_extraction.py`:

```python
def render_p07(out_path: Path) -> None:
    """P7: 混合ダッシュボードページ — 表 + 棒グラフ + SS + コード + 箇条書き."""
    spec = SPEC["p07"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    # Top-left: table
    tbl = layout["table"]
    tx1, ty1 = 40, body_y + 20
    tx2, ty2 = 820, body_y + 380
    _draw_screenshot_card(draw, (tx1, ty1, tx2, ty2), title=tbl["title"])
    col_widths = [140, 130, 130, 140, 140]
    hx = tx1 + 12
    hy = ty1 + 48
    for ci, col in enumerate(tbl["columns"]):
        draw.rectangle([hx, hy, hx + col_widths[ci], hy + 34],
                       fill=COLORS["grid"], outline=COLORS["card_border"])
        draw.text((hx + 8, hy + 8), col, fill=COLORS["text"], font=_bold_font(13))
        hx += col_widths[ci]
    for r, row in enumerate(tbl["rows"]):
        rx = tx1 + 12
        ry = hy + 34 * (r + 1)
        for ci, val in enumerate(row):
            draw.rectangle([rx, ry, rx + col_widths[ci], ry + 34],
                           fill=COLORS["bg"], outline=COLORS["card_border"])
            draw.text((rx + 8, ry + 8), val, fill=COLORS["text"], font=_font(12))
            rx += col_widths[ci]

    # Top-right: bar chart
    bc = layout["bar_chart"]
    bx1, by1 = 860, body_y + 20
    bx2, by2 = CANVAS_W - 40, body_y + 380
    _draw_screenshot_card(draw, (bx1, by1, bx2, by2), title=bc["title"])
    bars = bc["data"]
    max_v = max(v for _, v in bars)
    chart_top = by1 + 60
    chart_bot = by2 - 40
    chart_left = bx1 + 40
    chart_right = bx2 - 20
    draw.line([(chart_left, chart_bot), (chart_right, chart_bot)], fill=COLORS["text"], width=2)
    bar_area_w = chart_right - chart_left - 40
    bar_w = bar_area_w // (len(bars) * 2)
    for i, (lbl, v) in enumerate(bars):
        x = chart_left + 20 + i * (bar_w * 2)
        h = int((v / max_v) * (chart_bot - chart_top - 20))
        draw.rectangle([x, chart_bot - h, x + bar_w, chart_bot], fill=COLORS["primary"])
        draw.text((x, chart_bot - h - 18), str(v), fill=COLORS["text"], font=_font(12))
        draw.text((x + bar_w // 4, chart_bot + 6), lbl, fill=COLORS["text"], font=_font(12))

    # Bottom-left: screenshot caption placeholder
    ssx1, ssy1 = 40, by2 + 20
    ssx2, ssy2 = 440, ssy1 + 360
    _draw_screenshot_card(draw, (ssx1, ssy1, ssx2, ssy2), title="スクリーンショット")
    draw.rectangle([ssx1 + 20, ssy1 + 50, ssx2 - 20, ssy2 - 50],
                   fill=COLORS["card_border"], outline=COLORS["card_border"])
    draw.text((ssx1 + 20, ssy2 - 40), layout["screenshot_caption"],
              fill=COLORS["text"], font=_bold_font(13))

    # Bottom-center: code snippet
    cx1, cy1 = 460, by2 + 20
    cx2, cy2 = 960, ssy2
    _draw_screenshot_card(draw, (cx1, cy1, cx2, cy2), title=layout["code_snippet"]["filename"])
    draw.rectangle([cx1 + 12, cy1 + 48, cx2 - 12, cy2 - 12],
                   fill="#1e1e1e", outline=COLORS["card_border"])
    code_y = cy1 + 60
    for line in layout["code_snippet"]["lines"]:
        draw.text((cx1 + 20, code_y), line, fill="#d4d4d4", font=_mono_font(13))
        code_y += 22

    # Bottom-right: bullets
    bux1, buy1 = 980, by2 + 20
    bux2, buy2 = CANVAS_W - 40, ssy2
    _draw_screenshot_card(draw, (bux1, buy1, bux2, buy2), title="主要メトリクス")
    by = buy1 + 60
    for b in layout["bullets"]:
        draw.text((bux1 + 20, by), f"• {b}", fill=COLORS["text"], font=_font(14))
        by += 36

    img.save(out_path, "PNG")
```

- [ ] **Step 6: Implement render_p08 (Org chart)**

Add to `generate_extraction.py`:

```python
def render_p08(out_path: Path) -> None:
    """P8: 組織図 + ノード SS 補足 — 3 階層 10 ノード."""
    spec = SPEC["p08"]
    layout = spec["layout"]
    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    body_y = _draw_slide_title(draw, spec["title"])

    nodes = layout["nodes"]  # list of (id, level, name, role, parent)
    # Group by level
    by_level: dict[int, list[tuple]] = {}
    for n in nodes:
        by_level.setdefault(n[1], []).append(n)

    # Level y-positions
    level_ys = {1: body_y + 40, 2: body_y + 240, 3: body_y + 500}
    node_w, node_h = 180, 120

    # Draw nodes level by level, centered horizontally
    node_positions: dict[str, tuple[int, int]] = {}  # id -> (cx, cy_top)
    for lvl, items in sorted(by_level.items()):
        total_w = len(items) * node_w + (len(items) - 1) * 40
        start_x = (CANVAS_W - total_w) // 2
        for i, (nid, _lvl, name, role, _parent) in enumerate(items):
            nx1 = start_x + i * (node_w + 40)
            ny1 = level_ys[lvl]
            nx2 = nx1 + node_w
            ny2 = ny1 + node_h
            _draw_screenshot_card(draw, (nx1, ny1, nx2, ny2))
            # Avatar placeholder (circle)
            avatar_cx = nx1 + node_w // 2
            avatar_cy = ny1 + 38
            draw.ellipse([avatar_cx - 22, avatar_cy - 22, avatar_cx + 22, avatar_cy + 22],
                         fill=COLORS["card_border"], outline=COLORS["card_border"])
            # Name + role
            nw, _ = _tsize(draw, name, _bold_font(14))
            draw.text((nx1 + (node_w - nw) // 2, ny1 + 66), name,
                      fill=COLORS["text"], font=_bold_font(14))
            rw, _ = _tsize(draw, role, _font(12))
            draw.text((nx1 + (node_w - rw) // 2, ny1 + 88), role,
                      fill=COLORS["muted"], font=_font(12))
            node_positions[nid] = (avatar_cx, ny1, ny2)

    # Draw parent→child lines
    for nid, lvl, name, role, parent in nodes:
        if parent and parent in node_positions:
            pcx, _py1, py2 = node_positions[parent]
            ccx, cy1, _cy2 = node_positions[nid]
            # Vertical line from parent bottom to child top
            draw.line([(pcx, py2), (pcx, (py2 + cy1) // 2)], fill=COLORS["text"], width=2)
            draw.line([(pcx, (py2 + cy1) // 2), (ccx, (py2 + cy1) // 2)], fill=COLORS["text"], width=2)
            draw.line([(ccx, (py2 + cy1) // 2), (ccx, cy1)], fill=COLORS["text"], width=2)

    img.save(out_path, "PNG")
```

- [ ] **Step 7: Update dispatch table**

In `generate_extraction.py`, update `render_png`:

```python
def render_png(pid: str, out_path: Path) -> None:
    renderers = {
        "p01": render_p01, "p02": render_p02, "p03": render_p03, "p04": render_p04,
        "p05": render_p05, "p06": render_p06, "p07": render_p07, "p08": render_p08,
    }
    if pid not in renderers:
        raise NotImplementedError(f"render_png not implemented for {pid}")
    renderers[pid](out_path)
```

- [ ] **Step 8: Run tests to verify all 8 pass**

```bash
python -m pytest tests/text_vs_image/extraction/test_generate_extraction.py -v
```

Expected: PASS for all 8 patterns.

- [ ] **Step 9: Visual sanity check p05-p08**

```bash
python -c "
from pathlib import Path
from tests.text_vs_image.extraction.generate_extraction import render_png
for pid in ['p05', 'p06', 'p07', 'p08']:
    render_png(pid, Path(f'/tmp/{pid}_sanity.png'))
    print(f'wrote /tmp/{pid}_sanity.png')
"
open /tmp/p05_sanity.png /tmp/p06_sanity.png /tmp/p07_sanity.png /tmp/p08_sanity.png
```

Expected:
- `p05_sanity.png`: top row of 5 module boxes (決済コア highlighted red), drilldown arrow to zoomed 2×2 submodule grid + config table on right
- `p06_sanity.png`: left dashboard mockup with 6 sections, right 15 red R01-R15 comment boxes with thin arrows to mockup sections
- `p07_sanity.png`: 4-panel layout with table (top-left), bar chart (top-right), screenshot placeholder + caption (bottom-left), code snippet + bullets (bottom-right)
- `p08_sanity.png`: 3-tier org chart — 1 CEO box at top, 3 VP boxes in middle, 6 manager boxes at bottom, connected by lines

- [ ] **Step 10: Commit**

```bash
git add tests/text_vs_image/extraction/generate_extraction.py \
        tests/text_vs_image/extraction/test_generate_extraction.py
git commit -m "feat(extraction): PIL renderers for P5-P8 (drilldown, review, mixed, org)"
```

---

## Task 6: python-pptx rendering — helpers + slides for P1-P4

**Files:**
- Modify: `tests/text_vs_image/extraction/generate_extraction.py` (add pptx helpers + slide builders for P1-P4 + `render_pptx` entry)
- Modify: `tests/text_vs_image/extraction/test_generate_extraction.py` (add PPTX test)

**Reference:** Existing [tests/text_vs_image/generate_test_pptx.py](../../../tests/text_vs_image/generate_test_pptx.py) — reuse `px()` for pixel→EMU conversion and the `_add_box`/`_add_text`/`_add_line` helpers pattern.

- [ ] **Step 1: Write the failing PPTX test**

Append to `test_generate_extraction.py`:

```python
from pptx import Presentation


def test_render_pptx_produces_8_slides(tmp_path: Path):
    out = tmp_path / "extraction_test.pptx"
    g.render_pptx(out)
    assert out.exists()
    prs = Presentation(str(out))
    assert len(prs.slides) == 8


@pytest.mark.parametrize("pid,expected_title_substring", [
    ("p01", "勤怠"),
    ("p02", "Before"),
    ("p03", "購入フロー"),
    ("p04", "売上"),
    ("p05", "決済システム"),
    ("p06", "デザインレビュー"),
    ("p07", "混合ダッシュボード"),
    ("p08", "組織図"),
])
def test_pptx_each_slide_contains_title_text(tmp_path: Path, pid: str, expected_title_substring: str):
    """Each pattern's slide must contain the pattern title as native text (so
    Copilot can read the title without OCR when given the PPTX)."""
    out = tmp_path / "extraction_test.pptx"
    g.render_pptx(out)
    prs = Presentation(str(out))
    # Slides in order p01, p02, ..., p08
    idx = int(pid[1:]) - 1
    texts: list[str] = []
    for shape in prs.slides[idx].shapes:
        if shape.has_text_frame:
            texts.append(shape.text_frame.text)
    combined = "\n".join(texts)
    assert expected_title_substring in combined, \
        f"slide {idx} (for {pid}) does not contain '{expected_title_substring}'"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/text_vs_image/extraction/test_generate_extraction.py::test_render_pptx_produces_8_slides -v
```

Expected: FAIL — `AttributeError: module has no attribute 'render_pptx'`.

- [ ] **Step 3: Add pptx helpers and p01-p04 slide builders**

Append to `generate_extraction.py`:

```python
# -----------------------------------------------------------------------------
# PPTX rendering (python-pptx)
# -----------------------------------------------------------------------------
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt


def _px(n: float) -> Emu:
    """Pixel → EMU mapping at 96 DPI so pixel layouts port over 1:1 from PIL."""
    return Emu(int(n * 9525))


def _hex_rgb(s: str) -> RGBColor:
    return RGBColor.from_string(s.lstrip("#"))


def _pptx_blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _pptx_add_box(slide, x, y, w, h, *, fill=None, outline=None, outline_w=1.0,
                  shape=MSO_SHAPE.RECTANGLE):
    shp = slide.shapes.add_shape(shape, _px(x), _px(y), _px(w), _px(h))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = _hex_rgb(fill)
    if outline is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = _hex_rgb(outline)
        shp.line.width = Pt(outline_w)
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    return shp


def _pptx_add_text(slide, x, y, w, h, text, *, size_pt=11, bold=False,
                   color="#111827", align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(_px(x), _px(y), _px(w), _px(h))
    tf = tb.text_frame
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size_pt)
        run.font.bold = bold
        run.font.color.rgb = _hex_rgb(color)
    return tb


def _pptx_add_line(slide, x1, y1, x2, y2, *, color="#111827", width_pt=2.0):
    ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                    _px(x1), _px(y1), _px(x2), _px(y2))
    ln.line.color.rgb = _hex_rgb(color)
    ln.line.width = Pt(width_pt)
    return ln


def _pptx_title(slide, title: str):
    _pptx_add_text(slide, 32, 22, 1500, 40, title, size_pt=20, bold=True)
    _pptx_add_line(slide, 32, 86, CANVAS_W - 32, 86, color=COLORS["grid"], width_pt=1.5)


def _build_slide_p01(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p01"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    # Screenshot card
    card = (40, 110, 1000, 800)
    _pptx_add_box(slide, card[0], card[1], card[2] - card[0], card[3] - card[1],
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_box(slide, card[0], card[1], card[2] - card[0], 32,
                  fill=COLORS["header_bg"], outline=COLORS["header_bg"])
    _pptx_add_text(slide, card[0] + 12, card[1] + 6, 400, 24,
                   layout["app_title"], size_pt=12, bold=True, color=COLORS["header_text"])
    _pptx_add_text(slide, card[2] - 220, card[1] + 8, 200, 24,
                   layout["header_user"], size_pt=11, color=COLORS["header_text"], align=PP_ALIGN.RIGHT)

    # Table
    tbl_x1, tbl_y1 = card[0] + 24, card[1] + 60
    col_widths = [190, 110, 110, 110, 140]
    row_h = 42
    hx = tbl_x1
    for ci, header in enumerate(layout["table_header"]):
        _pptx_add_box(slide, hx, tbl_y1, col_widths[ci], row_h,
                      fill=COLORS["grid"], outline=COLORS["card_border"])
        _pptx_add_text(slide, hx + 10, tbl_y1 + 12, col_widths[ci] - 20, row_h - 24,
                       header, size_pt=11, bold=True)
        hx += col_widths[ci]
    for r, row in enumerate(layout["table_rows"]):
        ry = tbl_y1 + row_h * (r + 1)
        rx = tbl_x1
        for ci, val in enumerate(row):
            _pptx_add_box(slide, rx, ry, col_widths[ci], row_h,
                          fill=COLORS["bg"], outline=COLORS["card_border"])
            _pptx_add_text(slide, rx + 10, ry + 12, col_widths[ci] - 20, row_h - 24,
                           val, size_pt=11)
            rx += col_widths[ci]

    # Buttons
    btn_y = tbl_y1 + row_h * (len(layout["table_rows"]) + 1) + 24
    bx = tbl_x1
    for label in layout["buttons"]:
        bw = len(label) * 16 + 24
        _pptx_add_box(slide, bx, btn_y, bw, 32,
                      fill=COLORS["primary"], outline=COLORS["primary_dk"], outline_w=1.5)
        _pptx_add_text(slide, bx, btn_y + 7, bw, 22,
                       label, size_pt=11, bold=True, color=COLORS["header_text"], align=PP_ALIGN.CENTER)
        bx += bw + 10

    # 4 red callouts with labels
    for i, (label, text) in enumerate(layout["callouts"]):
        bx1 = 1040
        by1 = 130 + i * 170
        _pptx_add_box(slide, bx1, by1, 520, 110,
                      fill=COLORS["danger_bg"], outline=COLORS["danger"], outline_w=2.0,
                      shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        _pptx_add_text(slide, bx1 + 12, by1 + 12, 500, 24,
                       label, size_pt=12, bold=True, color=COLORS["danger_text"])
        _pptx_add_text(slide, bx1 + 12, by1 + 38, 500, 60,
                       text, size_pt=11, color=COLORS["danger_text"])


def _build_slide_p02(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p02"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    gap = 40
    card_w = (CANVAS_W - 3 * gap) // 2
    for offset, side_key in [(gap, "before"), (2 * gap + card_w, "after")]:
        card = (offset, 120, offset + card_w, 770)
        s = layout[side_key]
        _pptx_add_box(slide, card[0], card[1], card_w, card[3] - card[1],
                      fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
        _pptx_add_box(slide, card[0], card[1], card_w, 32,
                      fill=COLORS["header_bg"], outline=COLORS["header_bg"])
        _pptx_add_text(slide, card[0] + 12, card[1] + 6, card_w - 24, 24,
                       s["title"], size_pt=12, bold=True, color=COLORS["header_text"])
        sx1 = card[0] + 24
        sy = card[1] + 60
        _pptx_add_box(slide, sx1, sy, card_w - 160, 36,
                      fill=COLORS["bg"], outline=COLORS["card_border"], outline_w=1.5)
        _pptx_add_text(slide, sx1 + 10, sy + 10, card_w - 180, 20,
                       s["search_placeholder"], size_pt=11, color=COLORS["muted"])
        _pptx_add_box(slide, card[2] - 130, sy, 106, 36,
                      fill=COLORS["primary"], outline=COLORS["primary_dk"], outline_w=1.5)
        _pptx_add_text(slide, card[2] - 130, sy + 10, 106, 20,
                       s["button"], size_pt=11, bold=True, color=COLORS["header_text"], align=PP_ALIGN.CENTER)
        fy = sy + 60
        for _i in range(s["filter_rows"]):
            _pptx_add_box(slide, sx1, fy, card_w - 48, 28,
                          fill=COLORS["card_bg"], outline=COLORS["card_border"])
            fy += 36
        _pptx_add_text(slide, sx1, fy + 20, card_w - 48, 20,
                       s["result_count_label"], size_pt=11)
        _pptx_add_text(slide, sx1, fy + 60, card_w - 48, 24,
                       s["pagination"], size_pt=12, bold=True)

    # Diff labels at the bottom
    for i, (label, text) in enumerate(layout["diffs"]):
        y = CANVAS_H - 220 + i * 60
        _pptx_add_box(slide, 40, y, 240, 44,
                      fill=COLORS["danger_bg"], outline=COLORS["danger"], outline_w=1.5)
        _pptx_add_text(slide, 50, y + 12, 220, 24,
                       f"{label} {text}", size_pt=11, bold=True, color=COLORS["danger_text"])


def _build_slide_p03(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p03"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    steps = layout["steps"]
    n = len(steps)
    margin = 40
    gap = 48
    card_w = (CANVAS_W - 2 * margin - (n - 1) * gap) // n
    card_h = 400
    y1 = 230
    for i, (label, step_title, step_desc) in enumerate(steps):
        x1 = margin + i * (card_w + gap)
        # Step label badge
        _pptx_add_box(slide, x1 + card_w // 2 - 24, y1 - 40, 48, 32,
                      fill=COLORS["primary"], outline=COLORS["primary_dk"], outline_w=1.5)
        _pptx_add_text(slide, x1 + card_w // 2 - 24, y1 - 34, 48, 24,
                       label, size_pt=14, bold=True, color=COLORS["header_text"], align=PP_ALIGN.CENTER)
        # Card
        _pptx_add_box(slide, x1, y1, card_w, card_h,
                      fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
        _pptx_add_box(slide, x1, y1, card_w, 32,
                      fill=COLORS["header_bg"], outline=COLORS["header_bg"])
        _pptx_add_text(slide, x1 + 12, y1 + 6, card_w - 24, 24,
                       step_title, size_pt=12, bold=True, color=COLORS["header_text"])
        _pptx_add_text(slide, x1 + 12, y1 + 48, card_w - 24, card_h - 60,
                       step_desc, size_pt=11)
        if i < n - 1:
            _pptx_add_line(slide, x1 + card_w + 4, y1 + card_h // 2,
                           x1 + card_w + gap - 4, y1 + card_h // 2,
                           color=COLORS["text"], width_pt=3.0)


def _build_slide_p04(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p04"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    # Bar chart as labeled bars (native PPT elements, not image)
    _pptx_add_box(slide, 40, 140, 600, 300,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_text(slide, 56, 152, 500, 28,
                   layout["bar_chart"]["title"], size_pt=12, bold=True)
    bars = layout["bar_chart"]["data"]
    max_v = max(v for _, v in bars)
    chart_top, chart_bot = 200, 410
    for i, (lbl, v) in enumerate(bars):
        x = 80 + i * 160
        h = int((v / max_v) * (chart_bot - chart_top - 20))
        _pptx_add_box(slide, x, chart_bot - h, 80, h,
                      fill=COLORS["primary"], outline=COLORS["primary"])
        _pptx_add_text(slide, x, chart_bot - h - 22, 80, 20,
                       str(v), size_pt=11, align=PP_ALIGN.CENTER)
        _pptx_add_text(slide, x, chart_bot + 6, 80, 20,
                       lbl, size_pt=11, align=PP_ALIGN.CENTER)

    # Pie chart — approximate as labeled legend (python-pptx chart objects are heavier; legend-like text is sufficient for extraction test)
    _pptx_add_box(slide, 800, 140, CANVAS_W - 840, 300,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_text(slide, 816, 152, 500, 28,
                   layout["pie_chart"]["title"], size_pt=12, bold=True)
    palette = [COLORS["primary"], COLORS["success"], COLORS["warn"], COLORS["muted"]]
    for i, (lbl, v) in enumerate(layout["pie_chart"]["data"]):
        _pptx_add_box(slide, 816, 190 + i * 44, 24, 24,
                      fill=palette[i % len(palette)], outline=palette[i % len(palette)])
        _pptx_add_text(slide, 850, 194 + i * 44, 400, 28,
                       f"{lbl}  {v}%", size_pt=13)

    # 3 KPI cards
    kpi_y = 470
    kpi_w = (CANVAS_W - 2 * 40 - 2 * 20) // 3
    for i, (kpi_label, kpi_val, kpi_sub) in enumerate(layout["kpi_cards"]):
        kx1 = 40 + i * (kpi_w + 20)
        _pptx_add_box(slide, kx1, kpi_y, kpi_w, 160,
                      fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
        _pptx_add_text(slide, kx1 + 16, kpi_y + 16, kpi_w - 32, 20,
                       kpi_label, size_pt=13, bold=True, color=COLORS["muted"])
        _pptx_add_text(slide, kx1 + 16, kpi_y + 48, kpi_w - 32, 44,
                       kpi_val, size_pt=26, bold=True)
        _pptx_add_text(slide, kx1 + 16, kpi_y + 104, kpi_w - 32, 24,
                       kpi_sub, size_pt=11, color=COLORS["success"])

    # 3 annotation boxes
    for i, (label, text) in enumerate(layout["annotations"]):
        ay = 650 + i * 48
        _pptx_add_box(slide, 40, ay, CANVAS_W - 80, 40,
                      fill=COLORS["danger_bg"], outline=COLORS["danger"], outline_w=1.0)
        _pptx_add_text(slide, 52, ay + 10, CANVAS_W - 120, 24,
                       f"{label} {text}", size_pt=11, bold=True, color=COLORS["danger_text"])


def render_pptx(out_path: Path) -> None:
    """Build a single 8-slide PPTX, one slide per pattern p01..p08."""
    prs = Presentation()
    prs.slide_width = _px(CANVAS_W)
    prs.slide_height = _px(CANVAS_H)
    builders = {
        "p01": _build_slide_p01,
        "p02": _build_slide_p02,
        "p03": _build_slide_p03,
        "p04": _build_slide_p04,
        # p05-p08 added in Task 7.
    }
    for pid in ["p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"]:
        builder = builders.get(pid)
        if builder is None:
            # Placeholder slide so ordering is preserved until Task 7 lands.
            slide = _pptx_blank_slide(prs)
            _pptx_title(slide, SPEC[pid]["title"])
            _pptx_add_text(slide, 40, 150, CANVAS_W - 80, 40,
                           f"(TODO: {pid} slide builder — implemented in a later task)",
                           size_pt=14, color=COLORS["muted"])
        else:
            builder(prs)
    prs.save(str(out_path))
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/text_vs_image/extraction/test_generate_extraction.py -v -k pptx
```

Expected: PASS for `test_render_pptx_produces_8_slides` and for title parametrize cases p01-p04. The p05-p08 parametrized cases will PASS too because the placeholder slide also contains the title. (They look empty but pass the title check; Task 7 fills them in.)

- [ ] **Step 5: Visual sanity check**

```bash
python -c "
from pathlib import Path
from tests.text_vs_image.extraction.generate_extraction import render_pptx
render_pptx(Path('/tmp/extraction_check.pptx'))
"
open /tmp/extraction_check.pptx
```

Expected: 8 slides open in Keynote/PowerPoint; slides 1-4 (P1-P4) show full content matching the PNGs; slides 5-8 show only the title plus a TODO placeholder.

- [ ] **Step 6: Commit**

```bash
git add tests/text_vs_image/extraction/generate_extraction.py \
        tests/text_vs_image/extraction/test_generate_extraction.py
git commit -m "feat(extraction): python-pptx builders for P1-P4 + 8-slide skeleton"
```

---

## Task 7: python-pptx rendering — slides for P5-P8

**Files:**
- Modify: `tests/text_vs_image/extraction/generate_extraction.py`

- [ ] **Step 1: Implement _build_slide_p05 (Hierarchical drilldown)**

Add to `generate_extraction.py` (before `render_pptx`):

```python
def _build_slide_p05(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p05"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    modules = layout["top_level_modules"]
    highlighted = layout["highlighted_module"]
    n = len(modules)
    mod_y1 = 120
    mod_w = (CANVAS_W - 2 * 40 - (n - 1) * 20) // n
    for i, name in enumerate(modules):
        mx1 = 40 + i * (mod_w + 20)
        is_hi = (name == highlighted)
        _pptx_add_box(slide, mx1, mod_y1, mod_w, 120,
                      fill=COLORS["card_bg"],
                      outline=COLORS["danger"] if is_hi else COLORS["card_border"],
                      outline_w=3.0 if is_hi else 1.5)
        _pptx_add_text(slide, mx1, mod_y1 + 48, mod_w, 30,
                       name, size_pt=14, bold=True, align=PP_ALIGN.CENTER)

    # Drilldown arrow
    hi_idx = modules.index(highlighted)
    hi_cx = 40 + hi_idx * (mod_w + 20) + mod_w // 2
    _pptx_add_line(slide, hi_cx, 244, CANVAS_W // 2, 300,
                   color=COLORS["danger"], width_pt=3.0)

    # Zoomed submodules (left)
    _pptx_add_box(slide, 40, 320, 660, 380,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_box(slide, 40, 320, 660, 32,
                  fill=COLORS["header_bg"], outline=COLORS["header_bg"])
    _pptx_add_text(slide, 52, 326, 640, 24,
                   f"拡大: {highlighted}", size_pt=12, bold=True, color=COLORS["header_text"])
    sub = layout["zoom_submodules"]
    for i, name in enumerate(sub):
        r, c = divmod(i, 2)
        sx1 = 80 + c * 290
        sy1 = 380 + r * 130
        _pptx_add_box(slide, sx1, sy1, 260, 100,
                      fill=COLORS["bg"], outline=COLORS["card_border"], outline_w=1.5)
        _pptx_add_text(slide, sx1, sy1 + 40, 260, 24,
                       name, size_pt=14, bold=True, align=PP_ALIGN.CENTER)

    # Config table (right)
    _pptx_add_box(slide, 740, 320, CANVAS_W - 780, 380,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_box(slide, 740, 320, CANVAS_W - 780, 32,
                  fill=COLORS["header_bg"], outline=COLORS["header_bg"])
    _pptx_add_text(slide, 752, 326, 300, 24,
                   "設定パラメータ", size_pt=12, bold=True, color=COLORS["header_text"])
    cfg = layout["config_table"]
    col_widths = [320, 200, 200]
    hy = 380
    hx = 752
    for ci, col in enumerate(cfg["columns"]):
        _pptx_add_box(slide, hx, hy, col_widths[ci], 36,
                      fill=COLORS["grid"], outline=COLORS["card_border"])
        _pptx_add_text(slide, hx + 8, hy + 8, col_widths[ci] - 16, 24,
                       col, size_pt=12, bold=True)
        hx += col_widths[ci]
    for r, row in enumerate(cfg["rows"]):
        rx = 752
        ry = hy + 36 * (r + 1)
        for ci, val in enumerate(row):
            _pptx_add_box(slide, rx, ry, col_widths[ci], 36,
                          fill=COLORS["bg"], outline=COLORS["card_border"])
            _pptx_add_text(slide, rx + 8, ry + 8, col_widths[ci] - 16, 24,
                           val, size_pt=11)
            rx += col_widths[ci]
```

- [ ] **Step 2: Implement _build_slide_p06 (Review comments)**

Add to `generate_extraction.py`:

```python
def _build_slide_p06(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p06"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    # Left: mockup with 6 sections
    _pptx_add_box(slide, 40, 110, 740, 720,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_box(slide, 40, 110, 740, 32,
                  fill=COLORS["header_bg"], outline=COLORS["header_bg"])
    _pptx_add_text(slide, 52, 116, 700, 24,
                   "ダッシュボード モックアップ", size_pt=12, bold=True, color=COLORS["header_text"])
    sections = layout["mockup_sections"]
    sec_h = (720 - 32) // len(sections)
    for i, sec in enumerate(sections):
        sy1 = 142 + i * sec_h
        _pptx_add_box(slide, 56, sy1, 708, sec_h - 4,
                      fill=COLORS["bg"], outline=COLORS["card_border"], outline_w=0.75)
        _pptx_add_text(slide, 68, sy1 + 12, 680, 24,
                       sec, size_pt=13, bold=True)

    # Right: 15 comments in 2 columns
    comments = layout["comments"]
    comment_x1 = 800
    comment_w = (CANVAS_W - comment_x1 - 40 - 10) // 2
    for i, (label, text) in enumerate(comments):
        col = i % 2
        row = i // 2
        cx1 = comment_x1 + col * (comment_w + 10)
        cy1 = 120 + row * 90
        _pptx_add_box(slide, cx1, cy1, comment_w, 78,
                      fill=COLORS["danger_bg"], outline=COLORS["danger"], outline_w=1.5)
        _pptx_add_text(slide, cx1 + 10, cy1 + 8, comment_w - 20, 20,
                       label, size_pt=12, bold=True, color=COLORS["danger_text"])
        _pptx_add_text(slide, cx1 + 10, cy1 + 32, comment_w - 20, 44,
                       text, size_pt=11, color=COLORS["danger_text"])
```

- [ ] **Step 3: Implement _build_slide_p07 (Mixed dashboard)**

Add to `generate_extraction.py`:

```python
def _build_slide_p07(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p07"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    # Top-left: table
    tbl = layout["table"]
    _pptx_add_box(slide, 40, 120, 780, 360,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_box(slide, 40, 120, 780, 32,
                  fill=COLORS["header_bg"], outline=COLORS["header_bg"])
    _pptx_add_text(slide, 52, 126, 700, 24, tbl["title"],
                   size_pt=12, bold=True, color=COLORS["header_text"])
    col_widths = [140, 130, 130, 140, 140]
    hy = 168
    hx = 52
    for ci, col in enumerate(tbl["columns"]):
        _pptx_add_box(slide, hx, hy, col_widths[ci], 34,
                      fill=COLORS["grid"], outline=COLORS["card_border"])
        _pptx_add_text(slide, hx + 8, hy + 8, col_widths[ci] - 16, 20,
                       col, size_pt=12, bold=True)
        hx += col_widths[ci]
    for r, row in enumerate(tbl["rows"]):
        rx = 52
        ry = hy + 34 * (r + 1)
        for ci, val in enumerate(row):
            _pptx_add_box(slide, rx, ry, col_widths[ci], 34,
                          fill=COLORS["bg"], outline=COLORS["card_border"])
            _pptx_add_text(slide, rx + 8, ry + 8, col_widths[ci] - 16, 20,
                           val, size_pt=11)
            rx += col_widths[ci]

    # Top-right: bar chart
    bc = layout["bar_chart"]
    _pptx_add_box(slide, 860, 120, CANVAS_W - 900, 360,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_box(slide, 860, 120, CANVAS_W - 900, 32,
                  fill=COLORS["header_bg"], outline=COLORS["header_bg"])
    _pptx_add_text(slide, 872, 126, 600, 24, bc["title"],
                   size_pt=12, bold=True, color=COLORS["header_text"])
    bars = bc["data"]
    max_v = max(v for _, v in bars)
    chart_top, chart_bot = 180, 460
    for i, (lbl, v) in enumerate(bars):
        x = 900 + i * 150
        h = int((v / max_v) * (chart_bot - chart_top - 20))
        _pptx_add_box(slide, x, chart_bot - h, 80, h,
                      fill=COLORS["primary"], outline=COLORS["primary"])
        _pptx_add_text(slide, x, chart_bot - h - 22, 80, 20,
                       str(v), size_pt=11, align=PP_ALIGN.CENTER)
        _pptx_add_text(slide, x, chart_bot + 6, 80, 20,
                       lbl, size_pt=11, align=PP_ALIGN.CENTER)

    # Bottom-left: screenshot placeholder
    _pptx_add_box(slide, 40, 500, 400, 360,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_box(slide, 40, 500, 400, 32,
                  fill=COLORS["header_bg"], outline=COLORS["header_bg"])
    _pptx_add_text(slide, 52, 506, 380, 24,
                   "スクリーンショット", size_pt=12, bold=True, color=COLORS["header_text"])
    _pptx_add_box(slide, 60, 550, 360, 240,
                  fill=COLORS["card_border"], outline=COLORS["card_border"])
    _pptx_add_text(slide, 60, 810, 360, 24,
                   layout["screenshot_caption"], size_pt=12, bold=True)

    # Bottom-middle: code snippet
    _pptx_add_box(slide, 460, 500, 500, 360,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_box(slide, 460, 500, 500, 32,
                  fill=COLORS["header_bg"], outline=COLORS["header_bg"])
    _pptx_add_text(slide, 472, 506, 480, 24,
                   layout["code_snippet"]["filename"],
                   size_pt=12, bold=True, color=COLORS["header_text"])
    _pptx_add_box(slide, 472, 548, 476, 300,
                  fill="#1e1e1e", outline=COLORS["card_border"])
    code_y = 560
    for line in layout["code_snippet"]["lines"]:
        _pptx_add_text(slide, 484, code_y, 456, 22,
                       line, size_pt=11, color="#d4d4d4")
        code_y += 26

    # Bottom-right: bullets
    _pptx_add_box(slide, 980, 500, CANVAS_W - 1020, 360,
                  fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
    _pptx_add_box(slide, 980, 500, CANVAS_W - 1020, 32,
                  fill=COLORS["header_bg"], outline=COLORS["header_bg"])
    _pptx_add_text(slide, 992, 506, 400, 24,
                   "主要メトリクス", size_pt=12, bold=True, color=COLORS["header_text"])
    by = 560
    for b in layout["bullets"]:
        _pptx_add_text(slide, 1000, by, CANVAS_W - 1060, 28,
                       f"• {b}", size_pt=12)
        by += 40
```

- [ ] **Step 4: Implement _build_slide_p08 (Org chart)**

Add to `generate_extraction.py`:

```python
def _build_slide_p08(prs) -> None:
    slide = _pptx_blank_slide(prs)
    spec = SPEC["p08"]
    layout = spec["layout"]
    _pptx_title(slide, spec["title"])

    nodes = layout["nodes"]
    by_level: dict[int, list[tuple]] = {}
    for nd in nodes:
        by_level.setdefault(nd[1], []).append(nd)
    level_ys = {1: 140, 2: 330, 3: 580}
    node_w, node_h = 180, 120
    node_positions: dict[str, tuple[int, int, int]] = {}

    for lvl, items in sorted(by_level.items()):
        total_w = len(items) * node_w + (len(items) - 1) * 40
        start_x = (CANVAS_W - total_w) // 2
        for i, (nid, _lvl, name, role, _parent) in enumerate(items):
            nx1 = start_x + i * (node_w + 40)
            ny1 = level_ys[lvl]
            _pptx_add_box(slide, nx1, ny1, node_w, node_h,
                          fill=COLORS["card_bg"], outline=COLORS["card_border"], outline_w=1.5)
            # Avatar circle
            _pptx_add_box(slide, nx1 + node_w // 2 - 22, ny1 + 16, 44, 44,
                          fill=COLORS["card_border"], outline=COLORS["card_border"],
                          shape=MSO_SHAPE.OVAL)
            _pptx_add_text(slide, nx1, ny1 + 66, node_w, 22,
                           name, size_pt=12, bold=True, align=PP_ALIGN.CENTER)
            _pptx_add_text(slide, nx1, ny1 + 90, node_w, 22,
                           role, size_pt=10, color=COLORS["muted"], align=PP_ALIGN.CENTER)
            node_positions[nid] = (nx1 + node_w // 2, ny1, ny1 + node_h)

    for nid, _lvl, _name, _role, parent in nodes:
        if parent and parent in node_positions:
            pcx, _, py2 = node_positions[parent]
            ccx, cy1, _ = node_positions[nid]
            mid_y = (py2 + cy1) // 2
            _pptx_add_line(slide, pcx, py2, pcx, mid_y, color=COLORS["text"], width_pt=1.75)
            _pptx_add_line(slide, pcx, mid_y, ccx, mid_y, color=COLORS["text"], width_pt=1.75)
            _pptx_add_line(slide, ccx, mid_y, ccx, cy1, color=COLORS["text"], width_pt=1.75)
```

- [ ] **Step 5: Register P5-P8 builders in render_pptx**

In `generate_extraction.py`, update the `builders` dict in `render_pptx`:

```python
    builders = {
        "p01": _build_slide_p01,
        "p02": _build_slide_p02,
        "p03": _build_slide_p03,
        "p04": _build_slide_p04,
        "p05": _build_slide_p05,
        "p06": _build_slide_p06,
        "p07": _build_slide_p07,
        "p08": _build_slide_p08,
    }
```

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/text_vs_image/extraction/test_generate_extraction.py -v
```

Expected: All PASS (PNG p01-p08 + PPTX 8-slide count + title parametrize all 8).

- [ ] **Step 7: Visual sanity check PPTX in Keynote/PowerPoint**

```bash
python -c "
from pathlib import Path
from tests.text_vs_image.extraction.generate_extraction import render_pptx
render_pptx(Path('/tmp/extraction_check.pptx'))
"
open /tmp/extraction_check.pptx
```

Expected: 8 fully-rendered slides. Click through each and verify content (title, main elements, callouts) matches the PNG for that pattern. No "TODO placeholder" text.

- [ ] **Step 8: Commit**

```bash
git add tests/text_vs_image/extraction/generate_extraction.py
git commit -m "feat(extraction): python-pptx builders for P5-P8"
```

---

## Task 8: `main()` CLI + generate artifacts + commit them to repo

**Files:**
- Modify: `tests/text_vs_image/extraction/generate_extraction.py` (add `main()`)
- Create: `tests/text_vs_image/extraction/extraction_test.pptx` (generated, committed)
- Create: `tests/text_vs_image/extraction/p01_ui_callouts.png` … `p08_org_chart.png` (generated, committed)
- Create: `tests/text_vs_image/extraction/ground_truth.yaml` (generated, committed)

- [ ] **Step 1: Add `main()` to generate_extraction.py**

Append to `generate_extraction.py`:

```python
PNG_FILENAMES = {
    "p01": "p01_ui_callouts.png",
    "p02": "p02_before_after.png",
    "p03": "p03_process_flow.png",
    "p04": "p04_dashboard_annotated.png",
    "p05": "p05_hierarchical_drilldown.png",
    "p06": "p06_review_comments.png",
    "p07": "p07_mixed_dashboard.png",
    "p08": "p08_org_chart.png",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate extraction test corpus (PPTX + 8 PNG + GT YAML)")
    ap.add_argument("--out-dir", default=str(ROOT),
                    help="Where to write artifacts (default: alongside this script)")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for pid, fname in PNG_FILENAMES.items():
        path = out_dir / fname
        render_png(pid, path)
        print(f"wrote {path} ({path.stat().st_size} bytes)")

    pptx_path = out_dir / "extraction_test.pptx"
    render_pptx(pptx_path)
    print(f"wrote {pptx_path} ({pptx_path.stat().st_size} bytes)")

    gt_path = out_dir / "ground_truth.yaml"
    emit_ground_truth_yaml(gt_path)
    print(f"wrote {gt_path} ({gt_path.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Generate artifacts**

```bash
python tests/text_vs_image/extraction/generate_extraction.py
```

Expected output: 10 "wrote …" lines (8 PNGs + 1 PPTX + 1 YAML), each with non-zero byte counts.

- [ ] **Step 3: Validate the artifacts**

```bash
ls -la tests/text_vs_image/extraction/*.png tests/text_vs_image/extraction/*.pptx tests/text_vs_image/extraction/ground_truth.yaml
```

Expected: 8 PNG files (each > 20 KB), 1 PPTX file (> 30 KB), 1 YAML file (> 10 KB).

- [ ] **Step 4: Visual final review**

Open each artifact and verify it matches the spec:

```bash
open tests/text_vs_image/extraction/extraction_test.pptx
open tests/text_vs_image/extraction/p0*.png
```

Expected: All content is correct, readable, and matches the pattern descriptions in `extraction_spec.py`.

- [ ] **Step 5: Commit the generators + artifacts**

```bash
git add tests/text_vs_image/extraction/generate_extraction.py \
        tests/text_vs_image/extraction/extraction_test.pptx \
        tests/text_vs_image/extraction/p01_ui_callouts.png \
        tests/text_vs_image/extraction/p02_before_after.png \
        tests/text_vs_image/extraction/p03_process_flow.png \
        tests/text_vs_image/extraction/p04_dashboard_annotated.png \
        tests/text_vs_image/extraction/p05_hierarchical_drilldown.png \
        tests/text_vs_image/extraction/p06_review_comments.png \
        tests/text_vs_image/extraction/p07_mixed_dashboard.png \
        tests/text_vs_image/extraction/p08_org_chart.png \
        tests/text_vs_image/extraction/ground_truth.yaml
git commit -m "feat(extraction): generate CLI + ship 8 PNG + 1 PPTX + ground_truth.yaml"
```

---

## Task 9: Judge scaffold — load response, parse, recall score (reuse JUDGE_PROMPT_EXTRACTION)

**Files:**
- Create: `tests/text_vs_image/extraction/judge_extraction.py`
- Create: `tests/text_vs_image/extraction/test_judge_extraction.py`

**Reference:** [tests/text_vs_image/judge_pasted_descriptions.py](../../../tests/text_vs_image/judge_pasted_descriptions.py) — follows the same "pasted MD → Gemini judge → scores.json" pattern.

- [ ] **Step 1: Write failing test for the response loader**

Create `tests/text_vs_image/extraction/test_judge_extraction.py`:

```python
"""Tests for the extraction judge pipeline (mocked Gemini calls)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from tests.text_vs_image.extraction import judge_extraction as je


def _write_response_md(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# extraction — example\n\n## Output\n\n{body}\n",
        encoding="utf-8",
    )


def test_extract_output_section_strips_header(tmp_path: Path):
    p = tmp_path / "r.md"
    _write_response_md(p, "Hello world")
    assert je.extract_output_section(p) == "Hello world"


def test_extract_output_section_handles_missing_header(tmp_path: Path):
    p = tmp_path / "r.md"
    p.write_text("No header at all\njust body", encoding="utf-8")
    # Falls back to the whole file stripped.
    assert "No header at all" in je.extract_output_section(p)


def test_load_ground_truth_returns_8_patterns(tmp_path: Path):
    from tests.text_vs_image.extraction.extraction_spec import emit_ground_truth_yaml
    gt_path = tmp_path / "gt.yaml"
    emit_ground_truth_yaml(gt_path)
    gt = je.load_ground_truth(gt_path)
    assert set(gt.keys()) == {"p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"}
    assert all("facts" in v for v in gt.values())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/text_vs_image/extraction/test_judge_extraction.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named '...judge_extraction'`.

- [ ] **Step 3: Implement judge_extraction.py core loader + recall path**

Create `tests/text_vs_image/extraction/judge_extraction.py`:

```python
#!/usr/bin/env python
"""Judge Copilot Web verbatim-extraction responses against ground_truth.yaml.

Usage (after user has pasted Copilot responses under
benchmarks/out/extraction/{prompt_id}/):

    python tests/text_vs_image/extraction/judge_extraction.py \\
        --prompt-id my_prompt_v1 \\
        --n-runs 3

Produces:
    benchmarks/out/extraction/{prompt_id}/scores/
        png_p01_scores.json ... png_p08_scores.json
        pptx_scores.json
        summary.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Reuse the existing phase 4 judge infrastructure.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from phase4_quality_eval import (  # noqa: E402
    SCORE_MAP,
    JUDGE_PROMPT_EXTRACTION,
    extract_json,
    _mode_and_agreement,
    _stdev,
)

from google import genai


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_EXTRACTION_DIR = Path(__file__).resolve().parent
DEFAULT_OUT_ROOT = REPO_ROOT / "benchmarks" / "out" / "extraction"
DEFAULT_GT = DEFAULT_EXTRACTION_DIR / "ground_truth.yaml"


PNG_FILENAMES_TO_PID = {
    "png_p01_response.md": "p01",
    "png_p02_response.md": "p02",
    "png_p03_response.md": "p03",
    "png_p04_response.md": "p04",
    "png_p05_response.md": "p05",
    "png_p06_response.md": "p06",
    "png_p07_response.md": "p07",
    "png_p08_response.md": "p08",
}


def extract_output_section(md_path: Path) -> str:
    """Return only the body after `## Output` (mirrors _load_description from
    generate_human_eval_ui.py). Falls back to the full file body if the header
    is absent."""
    text = md_path.read_text(encoding="utf-8")
    if "## Output" in text:
        text = text.split("## Output", 1)[1]
    # Strip HTML comments (common pasted placeholder).
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text.strip()


def load_ground_truth(gt_path: Path) -> dict[str, dict[str, Any]]:
    return yaml.safe_load(gt_path.read_text(encoding="utf-8"))


def _judge_recall_once(
    gemini: genai.Client,
    judge_model: str,
    response_text: str,
    facts: list[dict[str, str]],
) -> dict[str, str]:
    """One Gemini call that returns {fact_id: verdict} for the recall dimension."""
    items_for_prompt = [{"id": f["id"], "text": f["text"]} for f in facts]
    prompt = JUDGE_PROMPT_EXTRACTION.format(
        description=response_text,
        items_json=json.dumps(items_for_prompt, ensure_ascii=False, indent=2),
    )
    last_err: Exception | None = None
    for _ in range(3):
        try:
            resp = gemini.models.generate_content(model=judge_model, contents=[prompt])
            text = getattr(resp, "text", "") or ""
            return extract_json(text)
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"judge failed after 3 retries: {last_err}")


def judge_one(
    gemini: genai.Client,
    judge_model: str,
    response_text: str,
    pid: str,
    gt: dict[str, dict[str, Any]],
    n_runs: int,
) -> dict[str, Any]:
    """Run recall judging `n_runs` times and aggregate into one scores object.

    Does NOT yet compute hallucination — that lands in Task 10.
    """
    facts = gt[pid]["facts"]
    per_item_verdicts: dict[str, list[str]] = {f["id"]: [] for f in facts}
    runs_meta: list[dict[str, Any]] = []

    for run_idx in range(1, n_runs + 1):
        t0 = time.perf_counter()
        verdicts = _judge_recall_once(gemini, judge_model, response_text, facts)
        elapsed = time.perf_counter() - t0
        run_numeric: list[float] = []
        for f in facts:
            v = verdicts.get(f["id"], "missing")
            if v not in SCORE_MAP:
                v = "missing"
            per_item_verdicts[f["id"]].append(v)
            run_numeric.append(SCORE_MAP[v])
        run_avg = sum(run_numeric) / len(run_numeric) if run_numeric else 0.0
        runs_meta.append({"run": run_idx, "score_avg": run_avg, "judge_seconds": elapsed})
        print(f"    [run {run_idx}/{n_runs}] recall={run_avg:.3f} ({elapsed:.1f}s)", flush=True)

    agg_avg = sum(r["score_avg"] for r in runs_meta) / len(runs_meta) if runs_meta else 0.0
    agg_std = _stdev([r["score_avg"] for r in runs_meta])
    facts_out: list[dict[str, Any]] = []
    for f in facts:
        vlist = per_item_verdicts[f["id"]]
        mode, agreement = _mode_and_agreement(vlist)
        facts_out.append({
            "id": f["id"], "text": f["text"],
            "verdict": mode, "verdicts": vlist,
            "verdict_mode": mode, "agreement": agreement,
        })
    return {
        "pattern_id": pid,
        "pattern_name": gt[pid]["pattern_name"],
        "n_runs": n_runs,
        "n_facts": len(facts),
        "recall_avg": agg_avg,
        "recall_std": agg_std,
        "runs": runs_meta,
        "facts": facts_out,
    }


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Judge Copilot extraction responses")
    ap.add_argument("--prompt-id", required=True,
                    help="Name of the subdirectory under benchmarks/out/extraction/")
    ap.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    ap.add_argument("--gt", default=str(DEFAULT_GT))
    ap.add_argument("--judge-model", default="gemini-2.5-flash")
    ap.add_argument("--n-runs", type=int, default=3)
    ap.add_argument("--patterns", default="p01,p02,p03,p04,p05,p06,p07,p08",
                    help="Comma-separated pattern ids to judge")
    return ap.parse_args()


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    args = _parse_args()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env", file=sys.stderr)
        return 2

    gemini = genai.Client(api_key=api_key)
    gt = load_ground_truth(Path(args.gt))
    patterns = [p.strip() for p in args.patterns.split(",") if p.strip()]

    prompt_dir = Path(args.out_root) / args.prompt_id
    scores_dir = prompt_dir / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)

    # Judge PNG responses (one file per pattern)
    for pid in patterns:
        resp_path = prompt_dir / f"png_{pid}_response.md"
        if not resp_path.exists():
            print(f"SKIP {pid}: {resp_path.name} not found")
            continue
        print(f"[png/{pid}]")
        response_text = extract_output_section(resp_path)
        scores = judge_one(gemini, args.judge_model, response_text, pid, gt, args.n_runs)
        out = scores_dir / f"png_{pid}_scores.json"
        out.write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    → {out.name} recall={scores['recall_avg']:.3f}")

    # PPTX judging (single response file covering all 8 slides)
    # Splitting logic lands in Task 10; for now, if pptx_response.md exists, just
    # punt with a placeholder scores file noting the pending split step.
    pptx_resp = prompt_dir / "pptx_response.md"
    if pptx_resp.exists():
        print("[pptx] response exists but splitting deferred to Task 10 implementation")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/text_vs_image/extraction/test_judge_extraction.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/text_vs_image/extraction/judge_extraction.py \
        tests/text_vs_image/extraction/test_judge_extraction.py
git commit -m "feat(extraction): judge scaffold — load responses, recall scoring (PNG only)"
```

---

## Task 10: Hallucination prompt + PPTX response slide splitting

**Files:**
- Modify: `tests/text_vs_image/extraction/judge_extraction.py`
- Modify: `tests/text_vs_image/extraction/test_judge_extraction.py`

- [ ] **Step 1: Write failing tests for hallucination judgment and split logic**

Append to `test_judge_extraction.py`:

```python
def test_hallucination_prompt_template_has_required_slots():
    tmpl = je.JUDGE_PROMPT_HALLUCINATION
    assert "{description}" in tmpl
    assert "{facts_json}" in tmpl


def test_split_pptx_response_heuristic_uses_slide_headers():
    response = """
## Slide 1
Line A for p01.

## Slide 2
Line B for p02.

## Slide 3
Line C for p03.
""".strip()
    segments = je.split_pptx_response_heuristic(response, n_slides=8)
    assert len(segments) == 8
    assert "Line A for p01" in segments[0]
    assert "Line B for p02" in segments[1]
    assert "Line C for p03" in segments[2]
    # Slides 4-8 have no header match; should be empty strings.
    for i in range(3, 8):
        assert segments[i] == "", f"slide {i+1} should be empty when no header present"


def test_split_pptx_response_heuristic_no_headers_returns_whole_as_slide_1():
    response = "Free-form text, no slide headers at all"
    segments = je.split_pptx_response_heuristic(response, n_slides=8)
    assert segments[0] == response
    for i in range(1, 8):
        assert segments[i] == ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/text_vs_image/extraction/test_judge_extraction.py::test_hallucination_prompt_template_has_required_slots -v
```

Expected: FAIL — `AttributeError: module has no attribute 'JUDGE_PROMPT_HALLUCINATION'`.

- [ ] **Step 3: Add hallucination prompt template + judge function**

In `judge_extraction.py`, add after the imports:

```python
JUDGE_PROMPT_HALLUCINATION = """以下の description（Copilot の出力）を読み、
参照ドキュメントに存在しない情報（捏造）が含まれているか判定してください。

## 判定対象の参照事実（ground truth）
{facts_json}

## Copilot の出力
{description}

## タスク
1. Copilot の出力の中で、上の参照事実のどれにも該当せず、かつ事実として元の
   ドキュメントに含まれていなかった可能性が高い具体的な記述を列挙してください。
2. 一般的な要約・構造化・Markdown 整形・フォーマット装飾は hallucination とは
   みなしません。事実の追加のみを対象とします。

## 出力形式
以下の JSON 形式で厳格に返してください。JSON 以外の説明文は禁止。

{{
  "hallucination_count": <int>,
  "examples": ["...", "..."]
}}

"examples" には最大 10 件の具体的な捏造内容を原文で記載してください。
"hallucination_count" は検出総数です（11 件以上ある場合は examples を 10 件に
切り詰めても count はすべての件数）。"""


def _judge_hallucination_once(
    gemini: genai.Client,
    judge_model: str,
    response_text: str,
    facts: list[dict[str, str]],
) -> dict[str, Any]:
    prompt = JUDGE_PROMPT_HALLUCINATION.format(
        description=response_text,
        facts_json=json.dumps(
            [{"id": f["id"], "text": f["text"]} for f in facts],
            ensure_ascii=False, indent=2,
        ),
    )
    last_err: Exception | None = None
    for _ in range(3):
        try:
            resp = gemini.models.generate_content(model=judge_model, contents=[prompt])
            text = getattr(resp, "text", "") or ""
            parsed = extract_json(text)
            count = int(parsed.get("hallucination_count", 0))
            examples = list(parsed.get("examples", []))[:10]
            return {"count": count, "examples": examples}
        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"hallucination judge failed after 3 retries: {last_err}")
```

- [ ] **Step 4: Add PPTX response splitting logic**

In `judge_extraction.py`, add:

```python
_SLIDE_HEADER_RE = re.compile(r"^##\s*(?:Slide|スライド|slide)\s*(\d+)", re.IGNORECASE | re.MULTILINE)


def split_pptx_response_heuristic(response_text: str, n_slides: int = 8) -> list[str]:
    """Split a Copilot PPTX response into per-slide segments.

    Strategy:
      1. If response contains `## Slide N` (or `スライド N`) markers, split on those.
      2. Otherwise, put all text in segment 0 and leave the rest empty
         (the caller can then fall back to a Gemini-based splitter, added later
         if heuristic fails often in practice).

    Returns a list of length `n_slides`, 0-indexed (segment[i] corresponds to
    slide i+1).
    """
    segments = [""] * n_slides
    matches = list(_SLIDE_HEADER_RE.finditer(response_text))
    if not matches:
        segments[0] = response_text.strip()
        return segments
    for i, m in enumerate(matches):
        slide_num = int(m.group(1))
        if not (1 <= slide_num <= n_slides):
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(response_text)
        segments[slide_num - 1] = response_text[start:end].strip()
    return segments
```

- [ ] **Step 5: Integrate hallucination + PPTX handling into `judge_one` and `main()`**

In `judge_extraction.py`, extend `judge_one` to also compute hallucination:

```python
def judge_one(
    gemini: genai.Client,
    judge_model: str,
    response_text: str,
    pid: str,
    gt: dict[str, dict[str, Any]],
    n_runs: int,
) -> dict[str, Any]:
    """Recall (n_runs) + hallucination (1 run — cheap, list rather than percentage)."""
    facts = gt[pid]["facts"]
    per_item_verdicts: dict[str, list[str]] = {f["id"]: [] for f in facts}
    runs_meta: list[dict[str, Any]] = []

    for run_idx in range(1, n_runs + 1):
        t0 = time.perf_counter()
        verdicts = _judge_recall_once(gemini, judge_model, response_text, facts)
        elapsed = time.perf_counter() - t0
        run_numeric: list[float] = []
        for f in facts:
            v = verdicts.get(f["id"], "missing")
            if v not in SCORE_MAP:
                v = "missing"
            per_item_verdicts[f["id"]].append(v)
            run_numeric.append(SCORE_MAP[v])
        run_avg = sum(run_numeric) / len(run_numeric) if run_numeric else 0.0
        runs_meta.append({"run": run_idx, "score_avg": run_avg, "judge_seconds": elapsed})
        print(f"    [run {run_idx}/{n_runs}] recall={run_avg:.3f} ({elapsed:.1f}s)", flush=True)

    print(f"    [hallucination check]", flush=True)
    hallu = _judge_hallucination_once(gemini, judge_model, response_text, facts)

    agg_avg = sum(r["score_avg"] for r in runs_meta) / len(runs_meta) if runs_meta else 0.0
    agg_std = _stdev([r["score_avg"] for r in runs_meta])
    facts_out: list[dict[str, Any]] = []
    for f in facts:
        vlist = per_item_verdicts[f["id"]]
        mode, agreement = _mode_and_agreement(vlist)
        facts_out.append({
            "id": f["id"], "text": f["text"],
            "verdict": mode, "verdicts": vlist,
            "verdict_mode": mode, "agreement": agreement,
        })
    return {
        "pattern_id": pid,
        "pattern_name": gt[pid]["pattern_name"],
        "n_runs": n_runs,
        "n_facts": len(facts),
        "recall_avg": agg_avg,
        "recall_std": agg_std,
        "hallucination_count": hallu["count"],
        "hallucination_examples": hallu["examples"],
        "runs": runs_meta,
        "facts": facts_out,
    }
```

And update `main()` to replace the PPTX placeholder with actual splitting + per-slide judging. Replace the block `if pptx_resp.exists():` with:

```python
    if pptx_resp.exists():
        print("[pptx] splitting per-slide and judging each segment...")
        pptx_text = extract_output_section(pptx_resp)
        segments = split_pptx_response_heuristic(pptx_text, n_slides=8)
        pptx_scores: list[dict[str, Any]] = []
        all_pids = ["p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"]
        for i, pid in enumerate(all_pids):
            if pid not in patterns:
                continue
            seg = segments[i]
            print(f"[pptx/{pid}]  ({len(seg)} chars)")
            if not seg.strip():
                # Empty segment → judge treats as missing; skip hallucination.
                facts = gt[pid]["facts"]
                pptx_scores.append({
                    "pattern_id": pid,
                    "pattern_name": gt[pid]["pattern_name"],
                    "n_runs": 0,
                    "n_facts": len(facts),
                    "recall_avg": 0.0,
                    "recall_std": 0.0,
                    "hallucination_count": 0,
                    "hallucination_examples": [],
                    "runs": [],
                    "facts": [
                        {"id": f["id"], "text": f["text"],
                         "verdict": "missing", "verdicts": ["missing"],
                         "verdict_mode": "missing", "agreement": 1.0}
                        for f in facts
                    ],
                    "note": "pptx split heuristic found no text for this slide",
                })
                continue
            scores = judge_one(gemini, args.judge_model, seg, pid, gt, args.n_runs)
            pptx_scores.append(scores)
            print(f"    → recall={scores['recall_avg']:.3f} hallu={scores['hallucination_count']}")
        (scores_dir / "pptx_scores.json").write_text(
            json.dumps(pptx_scores, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # Summary
    summary = {
        "prompt_id": args.prompt_id,
        "judge_model": args.judge_model,
        "n_runs": args.n_runs,
        "patterns_judged": patterns,
    }
    (scores_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/text_vs_image/extraction/test_judge_extraction.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 7: E2E smoke test with a dummy response**

Create a dummy response that quotes p01 GT facts exactly (should score ~1.0 recall, 0 hallucination), then run the judge:

```bash
mkdir -p benchmarks/out/extraction/dummy_smoke
python -c "
import yaml
from pathlib import Path
gt = yaml.safe_load(open('tests/text_vs_image/extraction/ground_truth.yaml', encoding='utf-8').read())
body = '\n'.join(f['text'] for f in gt['p01']['facts'])
Path('benchmarks/out/extraction/dummy_smoke/png_p01_response.md').write_text(
    f'# dummy\n\n## Output\n\n{body}\n', encoding='utf-8')
print('wrote dummy p01 response with', len(gt['p01']['facts']), 'facts verbatim')
"
python tests/text_vs_image/extraction/judge_extraction.py \
    --prompt-id dummy_smoke --patterns p01 --n-runs 1
```

Expected: output shows `recall=1.000` (or very close) and `hallu=0`, and `benchmarks/out/extraction/dummy_smoke/scores/png_p01_scores.json` is created.

Clean up:

```bash
rm -rf benchmarks/out/extraction/dummy_smoke
```

- [ ] **Step 8: Commit**

```bash
git add tests/text_vs_image/extraction/judge_extraction.py \
        tests/text_vs_image/extraction/test_judge_extraction.py
git commit -m "feat(extraction): add hallucination judge + PPTX response slide-splitting"
```

---

## Task 11: Cross-prompt comparison report

**Files:**
- Create: `tests/text_vs_image/extraction/extraction_report.py`

- [ ] **Step 1: Implement the report generator**

Create `tests/text_vs_image/extraction/extraction_report.py`:

```python
#!/usr/bin/env python
"""Aggregate all prompt-trial scores under benchmarks/out/extraction/ into one
Japanese Markdown comparison report.

Usage:
    python tests/text_vs_image/extraction/extraction_report.py \\
        --out tests/text_vs_image/extraction/extraction_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUT_ROOT = REPO_ROOT / "benchmarks" / "out" / "extraction"
DEFAULT_REPORT = Path(__file__).resolve().parent / "extraction_report.md"
ALL_PIDS = ["p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"]


def _load_prompt_scores(prompt_dir: Path) -> dict[str, dict] | None:
    """Return {channel: {pid: {recall_avg, hallucination_count, ...}}} or None if no scores."""
    scores_dir = prompt_dir / "scores"
    if not scores_dir.exists():
        return None
    out = {"png": {}, "pptx": {}}
    for pid in ALL_PIDS:
        png_path = scores_dir / f"png_{pid}_scores.json"
        if png_path.exists():
            out["png"][pid] = json.loads(png_path.read_text(encoding="utf-8"))
    pptx_path = scores_dir / "pptx_scores.json"
    if pptx_path.exists():
        for entry in json.loads(pptx_path.read_text(encoding="utf-8")):
            out["pptx"][entry["pattern_id"]] = entry
    return out


def _fmt(x: float | None) -> str:
    return "—" if x is None else f"{x:.3f}"


def build_report(out_root: Path, today: str) -> str:
    trials: list[tuple[str, dict]] = []
    for prompt_dir in sorted(out_root.glob("*/")):
        if not prompt_dir.is_dir():
            continue
        scores = _load_prompt_scores(prompt_dir)
        if scores:
            trials.append((prompt_dir.name, scores))
    if not trials:
        return f"# Copilot 抽出プロンプト 比較レポート\n\n_生成日: {today}_\n\n採点済みのプロンプト試行はまだありません。\n"

    lines: list[str] = []
    lines.append("# Copilot 抽出プロンプト 比較レポート")
    lines.append("")
    lines.append(f"_生成日: {today}_")
    lines.append("")
    lines.append(f"対象プロンプト: {len(trials)} 種類")
    lines.append("")
    lines.append("## 概要 (プロンプト × フォーマット 平均)")
    lines.append("")
    lines.append("| prompt_id | PNG recall avg | PNG hallu total | PPTX recall avg | PPTX hallu total |")
    lines.append("| --- | --- | --- | --- | --- |")
    for name, sc in trials:
        png_vals = [v["recall_avg"] for v in sc["png"].values()]
        pptx_vals = [v["recall_avg"] for v in sc["pptx"].values()]
        png_hallu = sum(v.get("hallucination_count", 0) for v in sc["png"].values())
        pptx_hallu = sum(v.get("hallucination_count", 0) for v in sc["pptx"].values())
        png_avg = sum(png_vals) / len(png_vals) if png_vals else None
        pptx_avg = sum(pptx_vals) / len(pptx_vals) if pptx_vals else None
        lines.append(f"| `{name}` | {_fmt(png_avg)} | {png_hallu} | {_fmt(pptx_avg)} | {pptx_hallu} |")
    lines.append("")

    lines.append("## パターン別 recall (PNG)")
    lines.append("")
    header = ["prompt_id"] + ALL_PIDS
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for name, sc in trials:
        row = [f"`{name}`"]
        for pid in ALL_PIDS:
            v = sc["png"].get(pid)
            row.append(_fmt(v["recall_avg"]) if v else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## パターン別 recall (PPTX)")
    lines.append("")
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for name, sc in trials:
        row = [f"`{name}`"]
        for pid in ALL_PIDS:
            v = sc["pptx"].get(pid)
            row.append(_fmt(v["recall_avg"]) if v else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## ハルシネーション件数 (パターン別、PNG / PPTX 合計)")
    lines.append("")
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for name, sc in trials:
        row = [f"`{name}`"]
        for pid in ALL_PIDS:
            png_h = sc["png"].get(pid, {}).get("hallucination_count", 0)
            pptx_h = sc["pptx"].get(pid, {}).get("hallucination_count", 0)
            row.append(str(png_h + pptx_h))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## ハルシネーション具体例 (プロンプト別、最初の 3 件)")
    lines.append("")
    for name, sc in trials:
        lines.append(f"### `{name}`")
        shown = 0
        for channel in ("png", "pptx"):
            for pid, v in sc[channel].items():
                for ex in v.get("hallucination_examples", [])[:3]:
                    lines.append(f"- **[{channel}/{pid}]** {ex}")
                    shown += 1
                    if shown >= 3:
                        break
                if shown >= 3:
                    break
            if shown >= 3:
                break
        if shown == 0:
            lines.append("- ハルシネーションなし")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    ap.add_argument("--out", default=str(DEFAULT_REPORT))
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()
    report = build_report(Path(args.out_root), args.date)
    out = Path(args.out)
    out.write_text(report, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Smoke test against an empty out-root**

```bash
python tests/text_vs_image/extraction/extraction_report.py --out /tmp/empty_report.md
head -5 /tmp/empty_report.md
```

Expected: Report says "採点済みのプロンプト試行はまだありません".

- [ ] **Step 3: Commit**

```bash
git add tests/text_vs_image/extraction/extraction_report.py
git commit -m "feat(extraction): cross-prompt comparison report (日本語 Markdown)"
```

---

## Task 12: README + final E2E validation

**Files:**
- Create: `tests/text_vs_image/extraction/README.md`
- Create: `tests/text_vs_image/extraction/.gitignore` (ignores local `/tmp` artifacts only; repo root gitignore already covers `.env`)

- [ ] **Step 1: Write README.md**

Create `tests/text_vs_image/extraction/README.md`:

```markdown
# Copilot 抽出プロンプト実験

お客様が Copilot Chat に画像 / PPT を渡して verbatim なテキスト抽出をさせるための
**フォーマット別プロンプト**を開発・評価するための実験基盤。

- 設計書: [docs/superpowers/specs/2026-04-24-copilot-extraction-prompt-design.md](../../../docs/superpowers/specs/2026-04-24-copilot-extraction-prompt-design.md)
- 先行実験: [../COPILOT_FINDINGS.md](../COPILOT_FINDINGS.md)

## 1. 材料生成 (1 回だけ)

```bash
python tests/text_vs_image/extraction/generate_extraction.py
```

これで以下が生成される:

- `extraction_test.pptx` — 8 slides (P1-P8) 入り、Copilot にアップロードする本体
- `p01_ui_callouts.png` 〜 `p08_org_chart.png` — 各 slide に対応する独立 PNG (8 枚)
- `ground_truth.yaml` — 採点時に Gemini judge が参照する正解事実リスト

## 2. プロンプト試行 (何回でも)

### 2.1 試行用の prompt_id を決める

例: `pptx_detailed_v1` / `png_cot_v2` など。内容が分かる任意の文字列。

### 2.2 Copilot Web で試行

1. <https://copilot.microsoft.com/> を開く
2. **PPTX 試行**: `extraction_test.pptx` をアップロード → プロンプトを貼付 → 送信 → 回答をコピー → 下記ファイルに保存
   - `benchmarks/out/extraction/{prompt_id}/pptx_response.md`
3. **PNG 試行 (8 回)**: `p01_ui_callouts.png` 〜 `p08_org_chart.png` を 1 枚ずつアップロード → 同じプロンプトを貼付 → 回答を
   - `benchmarks/out/extraction/{prompt_id}/png_p01_response.md` 〜 `png_p08_response.md` に保存
4. (任意) 使用したプロンプト全文を
   - `benchmarks/out/extraction/{prompt_id}/prompt.md` に保存しておくと後で比較しやすい

各 response MD は `## Output` 以下に回答を貼り付けるだけで可 (`## Output` ヘッダーは必須):

```markdown
# {prompt_id} / png_p01

**Date:** 2026-04-25

## Output

<Copilot の回答をここに貼り付け>
```

### 2.3 採点

```bash
python tests/text_vs_image/extraction/judge_extraction.py \
    --prompt-id {prompt_id}
```

Gemini 2.5 Flash が recall (n_runs=3) と hallucination (各 1 run) を判定し、
`benchmarks/out/extraction/{prompt_id}/scores/` に以下を書き出す:

- `png_p01_scores.json` 〜 `png_p08_scores.json` — 各パターンごとの採点
- `pptx_scores.json` — PPTX 応答を per-slide 分離して採点したリスト
- `summary.json` — 試行メタ情報

ターミナルには per-slide の recall と hallucination 件数が表示される。

## 3. 比較レポート (複数 prompt_id 試した後)

```bash
python tests/text_vs_image/extraction/extraction_report.py
```

`extraction_report.md` に以下を含む日本語レポートが生成される:

- プロンプト × フォーマットの recall 平均 / ハルシネーション合計
- パターン別 recall (PNG 表 / PPTX 表)
- パターン別ハルシネーション合計
- ハルシネーション具体例 (プロンプトごとに先頭 3 件)

## 4. トラブルシュート

### Copilot が PPTX の途中 slide で応答を切る

`pptx_response.md` をそのまま保存 (完全でなくて OK)。`judge_extraction.py` の
per-slide 分割ロジックは欠落 slide を空として扱い、該当 slide の recall は 0 になる。

**対策**: slide 数を減らして複数試行に分ける / CoT 系プロンプトで "最後の slide
まで書いてください" と明示する など、プロンプト工夫の検証対象になる。

### `## Slide N` 見出しが無くて per-slide 分割できない

現状の分割は `## Slide N` / `## スライド N` の見出しに依存。プロンプトに
"各スライドは `## Slide N` の見出しで始めてください" と書くと確実。
見出しなしの応答は slide 1 として扱われ、slide 2-8 は空になる (recall=0)。

### `GEMINI_API_KEY not set`

リポジトリ直下の `.env` に `GEMINI_API_KEY=...` を追加すること。
`.env` は `.gitignore` に登録済みなのでコミットされない。
```

- [ ] **Step 2: Final end-to-end smoke test**

Re-run the dummy smoke test from Task 10 Step 7 to verify everything still works after all Task 10-12 additions:

```bash
mkdir -p benchmarks/out/extraction/final_smoke
python -c "
import yaml
from pathlib import Path
gt = yaml.safe_load(open('tests/text_vs_image/extraction/ground_truth.yaml', encoding='utf-8').read())
# PNG: exact GT for p01
body = '\n'.join(f['text'] for f in gt['p01']['facts'])
Path('benchmarks/out/extraction/final_smoke/png_p01_response.md').write_text(
    f'# dummy\n\n## Output\n\n{body}\n', encoding='utf-8')
# PPTX: all 8 slides concatenated with ## Slide N headers
pptx_body = []
for i, pid in enumerate(['p01','p02','p03','p04','p05','p06','p07','p08'], start=1):
    pptx_body.append(f'## Slide {i}')
    pptx_body.extend(f['text'] for f in gt[pid]['facts'])
    pptx_body.append('')
Path('benchmarks/out/extraction/final_smoke/pptx_response.md').write_text(
    '# dummy\n\n## Output\n\n' + '\n'.join(pptx_body), encoding='utf-8')
print('dummy responses written')
"
python tests/text_vs_image/extraction/judge_extraction.py \
    --prompt-id final_smoke --patterns p01 --n-runs 1
python tests/text_vs_image/extraction/extraction_report.py \
    --out /tmp/final_smoke_report.md
head -30 /tmp/final_smoke_report.md
```

Expected:
- `png_p01_scores.json` shows `recall_avg` ≈ 1.0
- `pptx_scores.json` has an entry for p01 with `recall_avg` ≈ 1.0
- Report shows `final_smoke` row with PNG avg ≈ 1.0

Clean up:

```bash
rm -rf benchmarks/out/extraction/final_smoke /tmp/final_smoke_report.md
```

- [ ] **Step 3: Run the full test suite once more**

```bash
python -m pytest tests/text_vs_image/extraction/ -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/text_vs_image/extraction/README.md
git commit -m "docs(extraction): add user workflow README (日本語)"
```

- [ ] **Step 5: Verify final state**

```bash
git log --oneline -15
ls tests/text_vs_image/extraction/
```

Expected:
- 8 commits from Task 1-8 + Task 9-12 = ~12 commits total for this plan
- Directory contains: `__init__.py`, `extraction_spec.py`, `generate_extraction.py`, `judge_extraction.py`, `extraction_report.py`, `README.md`, 3 `test_*.py`, 8 PNGs, 1 PPTX, 1 YAML
- `git status` is clean

---

## Self-Review

After writing the plan, run through this checklist against the spec:

**1. Spec coverage**

- ✅ Spec §1.3 obj 1 (8 pattern PPTX + 8 PNG) → Tasks 3-8
- ✅ Spec §1.3 obj 2 (GT YAML) → Task 2
- ✅ Spec §1.3 obj 3 (Gemini judge recall + hallucination) → Tasks 9-10
- ✅ Spec §1.3 obj 4 (multi-prompt workflow) → Task 11 + README
- ✅ Spec §1.3 obj 5 (prompt finalization "後続フェーズ") → explicitly out of plan scope, consistent with spec §1.5 / §6 Phase 3
- ✅ Spec §2.2 (P1-P8 fact count targets ~225) → test_total_fact_count_is_in_expected_range asserts [180, 280]
- ✅ Spec §2.3 (single source of truth) → Task 1 establishes spec, all renderers import it
- ✅ Spec §3.1 Metric B → Task 10 adds hallucination judge
- ✅ Spec §3.2 per-slide scoring → Task 10 adds PPTX response splitting + per-slide judge
- ✅ Spec §4.1 workflow → Task 12 README covers every step
- ✅ Spec §5.1 file structure → matches plan File Structure section exactly
- ✅ Spec §7 validation → covered by pytest tests + Task 8/10/12 smoke tests

**2. Placeholder scan** — no TBD/TODO/ambiguous instructions inside tasks. Every step has concrete code or exact command.

**3. Type consistency** — `render_png(pid, out_path)` used consistently; `judge_one(gemini, judge_model, response_text, pid, gt, n_runs)` signature stable across Task 9 → 10; `SPEC[pid]["facts"]` and `SPEC[pid]["layout"]` referenced consistently.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-24-copilot-extraction-prompt-experiment.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Good for rendering tasks where visual sanity checks matter and context stays clean.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Faster if you want to stay in this conversation.

**Which approach?**


