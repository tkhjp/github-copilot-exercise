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

# Static descriptions for each trial directory. Keep in sync with what was
# actually run in benchmarks/out/extraction/<id>/.
TRIAL_META = {
    "v1": {
        "label": "v1 prompt × v1 corpus",
        "corpus": "v1",
        "prompt": "v1 (baseline)",
        "n_facts": 157,
        "date": "2026-04-23",
        "note": "初期ベースライン。v1 corpus (P1-P8 計 157 facts) に v1 prompt (シンプルな書き起こし指示) を投入。",
    },
    "v2": {
        "label": "v1 prompt × v2 corpus (Copilot Web)",
        "corpus": "v2",
        "prompt": "v1 (baseline)",
        "n_facts": 273,
        "date": "2026-04-24",
        "note": "Ceiling fix 検証。v2 corpus (密度 2 倍化 + vague 吹き出し、計 273 facts) に v1 prompt をそのまま投入。Microsoft Copilot Web (UI 経由、人手で貼り付け) の baseline。",
    },
    "v2_api_gemini3": {
        "label": "v1 prompt × v2 corpus (Gemini 3 Flash API)",
        "corpus": "v2",
        "prompt": "v1 (baseline)",
        "n_facts": 273,
        "date": "2026-04-27",
        "note": "コントロール群。v2 と同じ v1 prompt + v2 corpus を、Microsoft Copilot Web ではなく Gemini 3 Flash API (extractor) に直接投入。フロントエンド (Copilot Web vs 純粋 API) の差を測る。Judge 役は引き続き Gemini 2.5 Flash で同条件。",
    },
}

PATTERN_TITLES = {
    "p01": "勤怠アプリ画面 (UI callouts)",
    "p02": "Before/After 検索画面",
    "p03": "5 ステップ購入フロー",
    "p04": "Q1 売上ダッシュボード",
    "p05": "決済システム階層ドリルダウン",
    "p06": "デザインレビュー (赤入れ)",
    "p07": "混合ダッシュボードページ",
    "p08": "組織図",
}


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


def _trial_avg(sc: dict, channel: str) -> float | None:
    vals = [v["recall_avg"] for v in sc[channel].values()]
    return sum(vals) / len(vals) if vals else None


def _trial_hallu(sc: dict, channel: str) -> int:
    return sum(v.get("hallucination_count", 0) for v in sc[channel].values())


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
    lines.append("# Microsoft Copilot Web — 抽出プロンプト 比較レポート")
    lines.append("")
    lines.append(f"_生成日: {today} (extraction_report.py で自動生成、`python tests/text_vs_image/extraction/extraction_report.py` で再生成可)_")
    lines.append("")
    lines.append("## 1. 実験概要")
    lines.append("")
    lines.append("Microsoft Copilot Web (https://copilot.microsoft.com/) に同じテストコーパス (8 パターン)")
    lines.append("を PNG / PPTX 形式で投入し、Copilot の応答を Gemini 2.5 Flash で recall (ground truth")
    lines.append("fact 被覆率) と hallucination 件数で 3 run 採点した結果。")
    lines.append("")
    lines.append("**評価指標**:")
    lines.append("- **recall**: GT fact のうち Copilot 応答に含まれる割合 (0.0-1.0)。3 run の平均。")
    lines.append("- **hallucination**: Copilot が GT に存在しない情報を出した件数 (件数、3 run 通算)。")
    lines.append("")
    lines.append("## 2. 試行ラインナップ")
    lines.append("")
    lines.append("| trial id | label | prompt | corpus | n_facts | 実施日 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for name, _ in trials:
        meta = TRIAL_META.get(name, {})
        lines.append(
            f"| `{name}` | {meta.get('label', '?')} | {meta.get('prompt', '?')} | "
            f"{meta.get('corpus', '?')} | {meta.get('n_facts', '?')} | {meta.get('date', '?')} |"
        )
    lines.append("")
    for name, _ in trials:
        meta = TRIAL_META.get(name, {})
        if "note" in meta:
            lines.append(f"- **`{name}`**: {meta['note']}")
    lines.append("")
    lines.append("## 3. サマリー (試行 × フォーマット平均)")
    lines.append("")
    lines.append("| trial | PNG recall avg | PNG hallu total | PPTX recall avg | PPTX hallu total |")
    lines.append("| --- | --- | --- | --- | --- |")
    for name, sc in trials:
        png_avg = _trial_avg(sc, "png")
        pptx_avg = _trial_avg(sc, "pptx")
        lines.append(
            f"| `{name}` | {_fmt(png_avg)} | {_trial_hallu(sc, 'png')} | "
            f"{_fmt(pptx_avg)} | {_trial_hallu(sc, 'pptx')} |"
        )
    lines.append("")

    # 試行間の差分 (delta) を有意なペアで複数出す。
    trial_map = {name: sc for name, sc in trials}
    delta_pairs = [
        ("v1", "v2", "ceiling fix (corpus 難化、Copilot Web 一定)"),
        ("v2", "v2_api_gemini3", "frontend 切替 (corpus + prompt 一定、Copilot Web → Gemini 3 API)"),
    ]
    shown_any = False
    for base, head, label in delta_pairs:
        if base in trial_map and head in trial_map:
            if not shown_any:
                lines.append("### 主要な変化")
                lines.append("")
                shown_any = True
            base_sc, head_sc = trial_map[base], trial_map[head]
            for ch, ch_label in (("png", "PNG"), ("pptx", "PPTX")):
                base_v = _trial_avg(base_sc, ch)
                head_v = _trial_avg(head_sc, ch)
                if base_v is None or head_v is None:
                    continue
                delta = head_v - base_v
                lines.append(
                    f"- `{base}` → `{head}` ({label}) — {ch_label} recall: "
                    f"**{delta:+.3f}** ({_fmt(base_v)} → {_fmt(head_v)})"
                )
            lines.append("")

    lines.append("## 4. パターン別 recall (PNG)")
    lines.append("")
    header = ["trial"] + ALL_PIDS + ["avg"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for name, sc in trials:
        row = [f"`{name}`"]
        for pid in ALL_PIDS:
            v = sc["png"].get(pid)
            row.append(_fmt(v["recall_avg"]) if v else "—")
        row.append(_fmt(_trial_avg(sc, "png")))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## 5. パターン別 recall (PPTX)")
    lines.append("")
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for name, sc in trials:
        row = [f"`{name}`"]
        for pid in ALL_PIDS:
            v = sc["pptx"].get(pid)
            row.append(_fmt(v["recall_avg"]) if v else "—")
        row.append(_fmt(_trial_avg(sc, "pptx")))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## 6. ハルシネーション件数 (パターン別、PNG + PPTX 合計)")
    lines.append("")
    header_h = ["trial"] + ALL_PIDS + ["合計"]
    lines.append("| " + " | ".join(header_h) + " |")
    lines.append("| " + " | ".join(["---"] * len(header_h)) + " |")
    for name, sc in trials:
        row = [f"`{name}`"]
        total = 0
        for pid in ALL_PIDS:
            png_h = sc["png"].get(pid, {}).get("hallucination_count", 0)
            pptx_h = sc["pptx"].get(pid, {}).get("hallucination_count", 0)
            row.append(str(png_h + pptx_h))
            total += png_h + pptx_h
        row.append(str(total))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## 7. パターン名対応表")
    lines.append("")
    lines.append("| pid | 内容 |")
    lines.append("| --- | --- |")
    for pid in ALL_PIDS:
        lines.append(f"| `{pid}` | {PATTERN_TITLES.get(pid, '?')} |")
    lines.append("")

    lines.append("## 8. ハルシネーション具体例 (試行別、最初の 3 件)")
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

    lines.append("## 9. これまでの作業の経緯")
    lines.append("")
    lines.append("### 9.1 v1 corpus + v1 prompt (初期ベースライン)")
    lines.append("")
    lines.append("- 8 パターン (P1-P8) で 157 facts を Gemini 判定。")
    lines.append("- PNG / PPTX とも recall **0.89-0.90** と高得点。")
    lines.append("- **問題**: ceiling effect により今後の prompt 改善で差を測りにくい。")
    lines.append("")
    lines.append("### 9.2 v2 corpus 設計 (ceiling fix)")
    lines.append("")
    lines.append("v1 corpus の弱点を 2 軸で改修した:")
    lines.append("")
    lines.append("1. **密度を約 2 倍化**: 表の列数・行数、コード行数、組織図ノード数、コメント数すべてを増量。")
    lines.append("   合計 fact 数 157 → 273 (+74%)。")
    lines.append("2. **吹き出しを vague 略記に変更**: v1 では「KPI カードは 4 枚ではなく 3 枚に減らす」のような")
    lines.append("   答えを書いた吹き出しだったが、v2 では「5→4」「中央？」「16→24」のような")
    lines.append("   手書きメモ風の短い表現に変更。対象要素は配置・矢印先から推論させる。")
    lines.append("3. **対象推論ファクトの分離**: 吹き出し本文 verbatim (易) と吹き出しが指す対象 (難)")
    lines.append("   を別個のファクトとして GT に格納し、OCR 力と画像構造理解力を分離評価可能に。")
    lines.append("")
    lines.append("詳細は [PATTERNS.md](./PATTERNS.md) を参照。")
    lines.append("")
    lines.append("### 9.3 v1 prompt × v2 corpus (ceiling fix の効果検証 / Copilot Web)")
    lines.append("")
    lines.append("**同じ v1 prompt** をそのまま v2 corpus に投入。同条件 (prompt 一定) で corpus 難化が")
    lines.append("どれだけ recall を下げるかを観測した。Microsoft Copilot Web (UI 経由、人手で")
    lines.append("ファイルアップロード + プロンプト貼付) で実施。結果は §3 / §4 / §5 のテーブルを参照。")
    lines.append("")
    lines.append("### 9.4 v1 prompt × v2 corpus (Gemini 3 Flash API / コントロール群)")
    lines.append("")
    lines.append("Copilot Web が提供する recall 値が「Copilot 固有 (UI / 内部処理) の制約」なのか、")
    lines.append("それとも「画像コンテンツの本質的な難しさ」なのかを切り分けるため、同じ v1 prompt と")
    lines.append("v2 corpus を **Gemini 3 Flash Preview API に直接投入** したコントロール群を追加した。")
    lines.append("")
    lines.append("- Extractor: `gemini-3-flash-preview` (Google AI Studio API、画像直接入力)")
    lines.append("- Judge: `gemini-2.5-flash` (v1 / v2 trial と同じ判定モデル)")
    lines.append("- 入力: tests/text_vs_image/extraction/p0N_*.png 8 枚 (v2 corpus と同一バイナリ)")
    lines.append("- Prompt: benchmarks/out/extraction/v1/prompt.md と完全に同じ本文")
    lines.append("")
    lines.append("Extractor は別モデル (Gemini 3 Flash) を使い、Judge は据え置き (Gemini 2.5 Flash)。")
    lines.append("「同モデルの自己評価バイアス」は発生しない。")
    lines.append("")
    lines.append("## 10. 考察")
    lines.append("")
    lines.append("### 10.0 Copilot Web vs Gemini 3 Flash API (重要な発見)")
    lines.append("")
    lines.append("**同じ画像 + 同じプロンプト** を Microsoft Copilot Web 経由 (`v2`) と Gemini 3 Flash API")
    lines.append("経由 (`v2_api_gemini3`) で投入した結果、**recall は 0.723 → 0.875 (+0.152)** と大幅改善。")
    lines.append("特にテーブル / 構造系で差が大きい:")
    lines.append("")
    lines.append("- p01 勤怠表: 0.483 → **0.800** (+0.317) — Copilot が「[判読不能]」と諦めた表を API は完読")
    lines.append("- p02 Before/After: 0.510 → **0.833** (+0.323) — 左右ペア要素を API は網羅")
    lines.append("- p07 混合ダッシュボード: 0.780 → **1.000** (+0.220) — API は全 41 facts を完全抽出")
    lines.append("- p08 組織図: 0.701 → 0.880 (+0.179)")
    lines.append("")
    lines.append("これは「v2 corpus が難しすぎる」のではなく、**Copilot Web の UI / 内部処理パイプライン")
    lines.append("自体が抽出精度を ~15% 押し下げている** ことを意味する。原因の候補:")
    lines.append("")
    lines.append("- Copilot Web のチャット UI 内で出力長を切り詰めている可能性")
    lines.append("- 画像のリサイズ / 圧縮が UI で介在している可能性")
    lines.append("- 内部で異なる (より小さい) モデルにルーティングされている可能性")
    lines.append("- 安全フィルタや投影層 (system prompt) が verbatim 出力を抑制している可能性")
    lines.append("")
    lines.append("→ **実運用上の含意**: 抽出精度を最大化したいクライアントには、Copilot Web 手作業より")
    lines.append("**Gemini API (または同等の Vision API) を直接呼ぶ自動化** を推奨できる。")
    lines.append("Copilot Web は便利だが「人間が手で確認する補助ツール」であり、")
    lines.append("「下流 LLM への verbatim 入力源」としては精度が約 15% 不足する。")
    lines.append("")
    lines.append("### 10.1 ceiling effect は解消された")
    lines.append("")
    lines.append("PNG recall は **0.894 → 0.722 (-0.172)** と大幅に低下し、prompt 改善の余地が広い")
    lines.append("帯域で観測できる状態になった。今後の prompt v2/v3 では、ここから recall がどれだけ")
    lines.append("回復するかが評価軸になる。")
    lines.append("")
    lines.append("### 10.2 PPTX は corpus 難化に強い")
    lines.append("")
    lines.append("PPTX recall は **0.901 → 0.887 (-0.014)** とほぼ変化なし。これは「Copilot が PPTX を")
    lines.append("OCR ではなく XML 構造として直接読んでいる」可能性を示唆する強いシグナル。PNG では")
    lines.append("細かい文字 / 密集レイアウトが直接的に OCR 精度を下げるが、PPTX 経由なら shape の")
    lines.append("テキスト属性をそのまま読めるため、密度が上がっても大きく劣化しない。")
    lines.append("")
    lines.append("→ **実運用上の含意**: クライアントには「PPT で資料を渡せるなら PNG/スクショ より遥かに")
    lines.append("確実」と提案できる。逆に PNG/スクショしかない場合は prompt 側の補強が重要。")
    lines.append("")
    lines.append("### 10.3 PNG で大きく崩れたパターン")
    lines.append("")
    lines.append("- **p01 (勤怠アプリ): 0.947 → 0.483 (-0.464)** — 8 行 7 列の勤怠表を Copilot が")
    lines.append("  全セル「[判読不能]」と諦めて出力。表が密集すると OCR を放棄する挙動が観測された。")
    lines.append("- **p02 (Before/After): 0.921 → 0.510 (-0.411)** — 左右ペア要素 (メニュー数 3 vs 5、")
    lines.append("  フィルタ階層 vs 単一行など) を半数取りこぼす。左右非対称な差分の網羅が苦手。")
    lines.append("- **p06 (赤入れレビュー): 0.921 → 0.746 (-0.175)** — 25 個の vague callout 本文は")
    lines.append("  転記できたが、「対象推論」(R01「中央？」がロゴを指している、など) の facts が落ちた。")
    lines.append("")
    lines.append("### 10.4 PNG で持ちこたえたパターン")
    lines.append("")
    lines.append("- **p05 (階層ドリルダウン): 0.892 → 0.910** (+0.018) — 12 行設定パラメータ表を完全転記。")
    lines.append("  表の文字フォントが大きめで密集していなければ、行数が増えても recall は下がらない。")
    lines.append("- **p03 (購入フロー): 0.833 → 0.870** (+0.037) — ステップ毎にカード分割されているため、")
    lines.append("  情報が局所化され OCR 負荷が上がりにくい。")
    lines.append("")
    lines.append("### 10.5 ハルシネーション傾向")
    lines.append("")
    lines.append("v2 corpus でハルシネーション総数が **44 → 95** と倍増。特に p01 と p08 で多い:")
    lines.append("- **p01**: Copilot が「[判読不能]」を埋めるためダミー行 (`5. 2026-04-05 / [判読不能] / ...`)")
    lines.append("  を生成し、それが GT になく hallucination 判定。")
    lines.append("- **p08**: 20 ノード組織図で氏名 / 役職を取り違えたり、存在しないノードを生成。")
    lines.append("")
    lines.append("これらはハルシネーション抑制プロンプト (「推測で値を埋めない」) の効果検証対象。")
    lines.append("")
    lines.append("## 11. 次のステップ")
    lines.append("")
    lines.append("1. **prompt v2 設計** (`benchmarks/out/extraction/v2/prompt.md` または別ディレクトリ): ")
    lines.append("   step-by-step 指示 + 表記ルール + 件数 self-verify で v1 prompt の上記弱点を直接対策。")
    lines.append("2. **再判定**: prompt v2 × v2 corpus で 8 パターン × PNG/PPTX を投入、recall 回復幅を測定。")
    lines.append("3. **prompt v3 (PPT 専用 CoT)**: shape 列挙順 / type タグなど PPT 構造を明示的に使う。")
    lines.append("4. **prompt v4 (few-shot)**: vague callout 対象推論の好例を 1 つ仕込む。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_本レポートは extraction_report.py により自動生成されています。試行を追加・再判定後に_")
    lines.append("_`python tests/text_vs_image/extraction/extraction_report.py` で本ファイルが上書きされます。_")
    lines.append("_narrative セクション (§9-§11) はスクリプト内に埋め込まれているため、新たな試行を_")
    lines.append("_追加した際は extraction_report.py の TRIAL_META と narrative を併せて更新してください。_")
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
