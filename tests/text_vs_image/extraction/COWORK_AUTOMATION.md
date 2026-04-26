# Cowork で Copilot 抽出試行を自動化

[Claude Cowork](https://claude.com/claude-for-chrome) (Chrome 拡張) を使って、9 試行 (1 PPTX + 8 PNG) を 1 コマンドで回すための workflow。

## 1. セットアップ (1 回だけ)

### 1.1 Claude in Chrome 拡張インストール
1. <https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn> から拡張をインストール
2. Pin する (toolbar に常駐)
3. 拡張をクリック → Claude にサインイン (Pro/Max/Team/Enterprise の有料プラン必須)
4. 必要な権限 (debugger, storage) を許可

### 1.2 Cowork デスクトップ側で Chrome connector 有効化
1. Cowork デスクトップ アプリ起動
2. 左下のイニシャル → **Settings**
3. **Chrome connector** トグル ON
4. Cowork が Chrome 拡張を検知できるようになる

### 1.3 Microsoft Copilot にログイン
1. Chrome で <https://copilot.microsoft.com/> を開く
2. Microsoft アカウントでサインイン (MFA 含む、1 回だけ)
3. cookie が保存され、以降 Cowork が同 session で操作できる

### 1.4 (推奨) Cowork に site allowlist 設定
- 拡張アイコン → permissions
- `copilot.microsoft.com` への access を **always allow** に設定 (毎回承認だと面倒)

## 2. 試行 1 回分 (例: prompt_id = `v1`)

### 2.1 事前確認
- [ ] [benchmarks/out/extraction/v1/prompt.md](../../../benchmarks/out/extraction/v1/prompt.md) に試したいプロンプト本文がある
- [ ] [benchmarks/out/extraction/v1/](../../../benchmarks/out/extraction/v1/) に 9 個の `*_response.md` 雛形ファイルがある (空でも OK)
- [ ] Chrome で Copilot.microsoft.com が開いている (新規 conversation 状態)

### 2.2 Cowork に貼り付ける instruction

Cowork デスクトップを開いて、以下の文を貼り付けて送信:

````
Microsoft Copilot Web (https://copilot.microsoft.com/) で 9 回の抽出試行を順番に実行してください。Claude in Chrome 拡張を使って browser を駆動します。

# 共通設定
- 抽出プロンプト本文: /Volumes/mac_hd/work/github-copilot-exercise/benchmarks/out/extraction/v1/prompt.md の中の "## PNG / PPTX 共通プロンプト (貼付用)" セクションの code block 内のテキスト
- 入力ファイルのディレクトリ: /Volumes/mac_hd/work/github-copilot-exercise/tests/text_vs_image/extraction/
- 出力ファイルのディレクトリ: /Volumes/mac_hd/work/github-copilot-exercise/benchmarks/out/extraction/v1/
- 試行間に 30 秒待つ (rate limit 回避)

# 9 試行のリスト
1. 入力: extraction_test.pptx → 出力: pptx_response.md
2. 入力: p01_ui_callouts.png → 出力: png_p01_response.md
3. 入力: p02_before_after.png → 出力: png_p02_response.md
4. 入力: p03_process_flow.png → 出力: png_p03_response.md
5. 入力: p04_dashboard_annotated.png → 出力: png_p04_response.md
6. 入力: p05_hierarchical_drilldown.png → 出力: png_p05_response.md
7. 入力: p06_review_comments.png → 出力: png_p06_response.md
8. 入力: p07_mixed_dashboard.png → 出力: png_p07_response.md
9. 入力: p08_org_chart.png → 出力: png_p08_response.md

# 各試行の手順 (この通り 9 回繰り返す)
1. Copilot.microsoft.com を開いて、左上の "新しいチャット" をクリックして新規会話を開始
2. チャット入力欄の左側にあるアタッチアイコン (クリップ or "+" マーク) をクリック
3. ファイル選択ダイアログから上記の入力ファイルを選択
4. アップロード完了 (ファイルのサムネイルがチャット欄に表示される) を待つ
5. 抽出プロンプト本文をチャット入力欄に貼り付ける
6. 送信ボタンをクリックする (または Enter)
7. Copilot の応答が完了するまで待つ — 判定は: "回答を停止" / "Stop generating" ボタンが消えて、3 秒以上テキストが追加されないこと
8. 応答メッセージのテキスト全体を選択してコピー
9. 出力ファイル (例: benchmarks/out/extraction/v1/pptx_response.md) を以下の内容で上書き保存:

```markdown
# v1 / {filename}

**Date:** 2026-04-26
**Source:** Microsoft Copilot Web, prompt_id=v1

## Output

<ここに Copilot の応答をそのまま貼付>
```

10. 30 秒待ってから次の試行へ

# 全試行完了後
最後にターミナルで以下のコマンドを実行:
```
cd /Volumes/mac_hd/work/github-copilot-exercise
python tests/text_vs_image/extraction/judge_extraction.py --prompt-id v1
python tests/text_vs_image/extraction/extraction_report.py
```

エラーや判断に迷う点があれば、その時点で停止して相談してください。
````

### 2.3 Cowork が走り出してから

- Cowork は per-action approve で逐次確認してくる可能性あり (特に最初の数アクション)
- 信頼できる確認が積み重なれば "always allow for this site" を選んで以降スキップ
- 試行ごとの response が保存されているのを別ターミナルで `tail -f benchmarks/out/extraction/v1/*.md` 等で監視可

## 3. トラブルシュート

### Copilot が応答途中で止まる / 切れる
- response.md を空のまま保存 → judge は recall 0 として記録
- 後で手動でその試行だけ再実行する

### Cowork がアップロードボタンを見つけられない
- Copilot の UI が更新された可能性。スクリーンショットを撮って Cowork に「このボタンをクリック」と画像で指示し直す
- 最悪、その試行だけ手動で実行 (1 試行 1-2 分)

### "Stop generating" ボタンの判定がずれる
- Cowork に「30 秒固定で待つ」を追加させる代替プロンプト案も用意

### MS テナント制限で外部 automation 弾かれる
- 個人 Microsoft アカウントに切り替えるか、テナント管理者に確認

## 4. 複数 prompt_id を試したい場合

`v2`, `v3` も同じ要領で:
1. `cp -r benchmarks/out/extraction/v1 benchmarks/out/extraction/v2`
2. `v2/prompt.md` を編集 (例: step-by-step 指示を追加)
3. 上の Cowork instruction の `v1` を `v2` に置換して送信
4. 全 prompt_id で judge 走らせた後、`extraction_report.py` で横並び比較

---

## 参考リンク

- [Get started with Claude in Chrome](https://support.claude.com/en/articles/12012173-get-started-with-claude-in-chrome) — 公式インストールガイド
- [Use Claude Cowork safely](https://support.claude.com/en/articles/13364135-use-claude-cowork-safely) — permission モデル / 安全ガイド
- [Claude for Chrome - Anthropic](https://claude.com/claude-for-chrome) — 製品ページ
- [Chrome Web Store: Claude](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn) — 拡張インストール
