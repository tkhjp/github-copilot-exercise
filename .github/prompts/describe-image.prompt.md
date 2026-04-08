---
mode: agent
description: 指定された画像ファイル（png/jpg等）を Gemini Vision で記述し、内容を要約する
---

ユーザーが指定した画像ファイルのパスを引数として受け取ります。

1. `run_in_terminal` ツールで次のコマンドを実行してください:
   ```bash
   python tools/describe_image.py <ユーザー指定のパス>
   ```
2. stdout に出力される Markdown 形式の記述を読み取ります。
3. 記述内容を日本語でユーザーにわかりやすく要約し、主要ポイントを箇条書きで示してください。
4. 必要に応じて元の記述の該当箇所を引用してください。

スクリプトが非ゼロ exit code で終了した場合、stderr の内容をユーザーに伝え、推測で回答を捏造しないでください。
