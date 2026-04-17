---
name: code-review
description: GitHub Pull Request のコードレビューを実施するスキル。PR の差分を取得し、🔴 MUST / 🟡 SHOULD / 🟢 NICE TO HAVE の3段階で指摘を分類した上で、該当コード行にインラインレビューコメントを投稿し、最後にサマリコメントを PR に残す。リポジトリ共通のレビュー観点（docs/REVIEW.md）と PR 固有のレビュー観点（PR 本文の `<!-- REVIEW_FOCUS -->` ブロック）も考慮する。GitHub の操作は MCP（`mcp__github__*` / `mcp__github_inline_comment__*` / `mcp__github_comment__*`）が使える場合は MCP を優先し、使えない場合は `gh` CLI にフォールバックする。ユーザーが「コードレビュー」「code review」「PR レビュー」「プルリクエストのレビュー」「レビューして」「review this PR」「指摘して」「レビューコメント」「MUST / SHOULD / NICE TO HAVE」「レビュー観点」「差分レビュー」などに言及した場合にこのスキルを使うこと。PR 番号や PR URL が渡された時、あるいは「この PR をレビューして」といった依頼にも対応する。
---

# コードレビュー実施スキル

GitHub の Pull Request に対して、Claude がコードレビューを実施し、インラインコメントとサマリコメントを投稿するためのスキル。CLI 上で一貫したレビュー体験をローカルから実行できるようにすることが目的。

## 前提条件

- レビュー対象の PR が存在する GitHub リポジトリにアクセスできること
- 以下のいずれかが利用可能であること:
  - **推奨**: GitHub MCP サーバー（`mcp__github__*`, `mcp__github_inline_comment__*`, `mcp__github_comment__*` などのツール）
  - **フォールバック**: `gh` CLI（`gh auth login` 済み、`repo` スコープ以上）
- レビュー対象のコードがカレントディレクトリまたは checkout 済みのパスで読み取れること（ローカルの grep / read でコードを追うため）

> GitHub MCP が使える場合は必ず MCP を優先すること。MCP が使えない環境では `gh` API / `gh pr` にフォールバックする。同じセッション内で MCP と `gh` を混在させるのは避け、原則どちらか一方に統一する。

---

## レビュー方針（分類ルール）

すべての指摘を以下の3段階で分類し、コメント先頭に必ずタグを付ける。

- 🔴 **[MUST]** — 修正必須。バグ、セキュリティ脆弱性、データ損失リスク、重大なロジックエラー、本番障害につながる可能性がある問題。
- 🟡 **[SHOULD]** — 修正推奨。可読性・保守性の低下、パフォーマンス改善の余地、エラーハンドリング不足、テスト不足など。
- 🟢 **[NICE TO HAVE]** — 検討推奨。コードスタイルの軽微な改善、命名の微調整、コメント追加の提案、リファクタリングのアイデアなど。

分類の運用ルール:

- セキュリティに関わる問題は必ず **MUST** にする。
- 些細すぎる指摘は控え、本当に価値のあるフィードバックに絞る。
- 改善案がある場合は GitHub の suggestion ブロック（\`\`\`suggestion \`\`\`）で具体的な修正提案を示す。

---

## ワークフロー概要

```
[Step 1: PR 特定]
  → [Step 2: 実行環境の確認（MCP or gh）]
  → [Step 3: レビュー開始通知]
  → [Step 4: 共通レビュー観点の読み込み（docs/REVIEW.md）]
  → [Step 5: PR 固有観点の抽出（<!-- REVIEW_FOCUS -->）]
  → [Step 6: PR 差分・関連ファイルの取得]
  → [Step 7: レビュー指摘の洗い出しと分類]
  → [Step 8: インラインレビューコメントの投稿]
  → [Step 9: サマリコメントの投稿（レビュー提出）]
  → [Step 10: 完了通知]
```

---

## Step 1: PR の特定

ユーザーからの入力（PR URL、PR 番号、あるいは「この PR」などの指示）から、レビュー対象のリポジトリと PR 番号を特定する。

- PR URL が与えられた場合: `https://github.com/OWNER/REPO/pull/NUMBER` を分解する
- PR 番号のみ与えられた場合: カレントディレクトリの Git リモートからリポジトリを推定する
- 不明な場合はユーザーに `OWNER/REPO#NUMBER` を尋ねる

```bash
# カレントリポジトリの特定
gh repo view --json nameWithOwner -q '.nameWithOwner'

# PR 番号未指定で、カレントブランチに紐づく PR を探す場合
gh pr status --json number,title,url
```

## Step 2: 実行環境の確認

GitHub 操作に使えるツールを確認し、以下の順で優先する。

1. **GitHub MCP が利用可能か**: 利用可能なツールに `mcp__github__*`, `mcp__github_inline_comment__*`, `mcp__github_comment__*` が含まれているかを確認する。
   - 含まれていれば MCP を使う。
2. **`gh` CLI が利用可能か**: `gh auth status` で認証済みかを確認する。
   - MCP が使えず `gh` が使えればフォールバックとして `gh` を使う。
3. どちらも使えない場合は、ユーザーに認証または MCP サーバー設定を案内して中断する。

ユーザーへの最初のテキスト出力で、「どちらを使ってレビューを進めるか」を1行で明示すること（例: `GitHub MCP を使ってレビューを実施します`）。

## Step 3: レビュー開始の通知

PR に「レビュー中」であることを伝えるコメントを投稿する（後で削除・更新するため ID を保持する）。

### MCP の場合

- `mcp__github_comment__update_claude_comment` 相当、または `mcp__github__add_issue_comment` で「レビュー中」コメントを作成する。
- 作成したコメントの ID を控える。

### gh CLI の場合

```bash
PR_NUMBER=<number>
REPO=<owner/repo>

# 👀 リアクションを付与
gh api "repos/${REPO}/issues/${PR_NUMBER}/reactions" -f content=eyes --silent || true

# 「claude-reviewing」ラベルを付与（存在しなければ作成）
gh label create "claude-reviewing" --repo "${REPO}" \
  --description "Claude コードレビュー実施中" --color "FFA500" --force || true
gh pr edit "${PR_NUMBER}" --repo "${REPO}" --add-label "claude-reviewing" || true

# 「レビュー中」コメントを投稿して ID を控える
COMMENT_BODY='## 🔍 コードレビュー中

Claude がこのPRのコードレビューを実施しています。
完了次第、レビュー結果をサマリとしてコメントします。

> ⏳ しばらくお待ちください...'

COMMENT_ID=$(gh api "repos/${REPO}/issues/${PR_NUMBER}/comments" \
  -f body="${COMMENT_BODY}" --jq '.id')
echo "$COMMENT_ID"
```

レビュー完了時（Step 10）に、この「レビュー中」コメント・ラベルを削除する。

## Step 4: リポジトリ共通レビュー観点の読み込み

リポジトリ直下に `docs/REVIEW.md` が存在する場合、その内容を「リポジトリ共通レビュー観点」として読み込み、Step 7 のレビュー指摘の洗い出しで必ず参照する。

```bash
# 存在確認
test -f docs/REVIEW.md && echo "found" || echo "missing"
```

存在する場合は `Read` ツールで全文を取得し、以降のレビューで参照する。違反がある場合は該当する観点を明示する。存在しない場合は `（docs/REVIEW.md が見つかりませんでした。スキップします）` と扱い、汎用的なベストプラクティスのみを適用する。

## Step 5: PR 固有レビュー観点の抽出

PR 本文の中から `<!-- REVIEW_FOCUS -->` と `<!-- /REVIEW_FOCUS -->` に挟まれたブロックを抽出し、「PR 固有のレビュー観点」として扱う。

### MCP の場合

- `mcp__github__get_pull_request` などで PR 本文を取得し、正規表現で `<!-- REVIEW_FOCUS -->...<!-- /REVIEW_FOCUS -->` を抽出する。

### gh CLI の場合

```bash
PR_BODY=$(gh pr view "${PR_NUMBER}" --repo "${REPO}" --json body -q '.body')
echo "$PR_BODY" | sed -n '/<!-- REVIEW_FOCUS -->/,/<!-- \/REVIEW_FOCUS -->/{
  /<!-- REVIEW_FOCUS -->/d
  /<!-- \/REVIEW_FOCUS -->/d
  p
}' | sed '/^$/d'
```

抽出できた場合: そのブロックの内容を Step 7 で特に重点的にチェックし、該当する指摘には「PR 固有観点」である旨を明示する。
抽出できなかった場合: `（PR 固有のレビュー観点は指定されていません）` として扱い、共通観点 + 汎用ベストプラクティスのみで進める。

## Step 6: PR 差分・関連ファイルの取得

レビュー対象となる差分を取得し、必要に応じて周辺コードも読み込む。

### MCP の場合

- `mcp__github__get_pull_request_diff` で差分を取得する。
- `mcp__github__get_pull_request_files` で変更ファイル一覧（追加/変更/削除）を取得する。
- 判断に必要な周辺コードは、カレントディレクトリから `Read` / `Grep` で追う。

### gh CLI の場合

```bash
# 差分（パッチ形式）
gh pr diff "${PR_NUMBER}" --repo "${REPO}" --patch > /tmp/pr_${PR_NUMBER}.patch

# 変更ファイル一覧
gh pr view "${PR_NUMBER}" --repo "${REPO}" --json files -q '.files[].path'

# PR メタ情報
gh pr view "${PR_NUMBER}" --repo "${REPO}" --json number,title,body,author,baseRefName,headRefName,state,isDraft
```

差分ファイルが多い PR では全行を一度にレビューしようとせず、差分のまとまり（hunk）ごとに検討を進める。必要な周辺コードは現在のワークツリーから `Read` で読み、影響範囲を確認する。

## Step 7: レビュー指摘の洗い出しと分類

差分・共通観点・PR 固有観点を踏まえて、各ファイル・各 hunk を読み、指摘を洗い出す。洗い出しの観点例:

- **セキュリティ**: 入力検証、認可、機密情報の扱い、インジェクション、依存パッケージの脆弱性 など
- **バグ・ロジック**: 境界条件、nil/null 処理、非同期の競合、意図と実装の乖離、例外経路
- **データ整合性**: トランザクション境界、冪等性、マイグレーションの後方互換性
- **パフォーマンス**: N+1 クエリ、大量データの走査、無駄な再計算、メモリリーク
- **エラーハンドリング**: 握り潰し、誤ったリトライ、ユーザーに伝わらないエラー
- **可読性・保守性**: 責務分離、命名、重複、過剰な抽象化 / 具象化
- **テスト**: 正常系・異常系・境界値のカバレッジ、モックの妥当性、テストの独立性
- **リポジトリ共通観点**（Step 4 で取得した内容）
- **PR 固有観点**（Step 5 で取得した内容）

洗い出した各指摘について、**🔴 MUST / 🟡 SHOULD / 🟢 NICE TO HAVE** のいずれかに分類する。分類が迷う場合は、より重いほうに倒す前に「実害があるか」「回避可能か」を自問し、実害があるものだけを MUST にする。

各指摘には以下をセットで記録する（内部メモ）:

- 対象ファイルのパス
- 対象行番号（可能なら start_line と end_line、単一行なら line のみ）
- 分類タグ（🔴 / 🟡 / 🟢）
- 指摘の本文（2〜4 文程度）
- 改善案（suggestion ブロックに入れる内容があれば）
- どの観点由来か（汎用 / リポジトリ共通 / PR 固有）

## Step 8: インラインレビューコメントの投稿

Step 7 で洗い出した指摘を、該当するコード行にインラインコメントとして投稿する。

### MCP の場合（推奨）

**方式 A: pending review を作って一括で提出**

1. `mcp__github__create_pending_pull_request_review` で pending レビューを作成。
2. 各指摘ごとに `mcp__github__add_comment_to_pending_review`（ないし同等のインラインコメント追加ツール）で行コメントを追加。
3. Step 9 で `mcp__github__submit_pending_pull_request_review` により REQUEST_CHANGES / COMMENT としてまとめて提出する。

**方式 B: インラインコメント追加ツールで 1件ずつ投稿**

- `mcp__github_inline_comment__create_inline_comment` を使い、指摘ごとにインラインコメントを投稿する。
- 最終的な「レビュー提出」は Step 9 で `mcp__github__create_pull_request_review` に `event: REQUEST_CHANGES` / `event: COMMENT` を指定して行う。

いずれの方式でも、コメント本文の先頭に分類タグ（🔴 / 🟡 / 🟢）を付ける。

### gh CLI の場合（フォールバック）

`gh` には pending review を扱う専用コマンドがないため、`gh api` で GitHub REST API を直接叩く。

```bash
# 1件ずつインラインコメントを投稿（pending にならない点に注意）
gh api "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
  -f body="$(cat <<'EOF'
🔴 **[MUST]** <指摘本文>

\`\`\`suggestion
<修正案があればここに>
\`\`\`
EOF
)" \
  -f commit_id="${HEAD_SHA}" \
  -f path="${FILE_PATH}" \
  -F line="${LINE_NUMBER}" \
  -f side="RIGHT"

# HEAD_SHA は PR の先頭コミット SHA（下記で取得）
HEAD_SHA=$(gh pr view "${PR_NUMBER}" --repo "${REPO}" --json headRefOid -q '.headRefOid')
```

複数行に跨るコメントを付ける場合は `start_line` と `start_side` も指定する。削除された行に付ける場合は `side=LEFT`。

### コメント本文のフォーマット

```
🔴 **[MUST]** <指摘の要点を1文で>

<詳細な説明（なぜ問題か、どう影響するか）>

（PR 固有観点 / リポジトリ共通観点 に由来する場合はその旨を記載）

```suggestion
<修正案（1行でも複数行でも）>
```
```

suggestion ブロックは、`side=RIGHT` のときのみ有効。削除行に対するコメントには入れない。

## Step 9: サマリコメントの投稿（レビュー提出）

全インラインコメントを投稿したら、**必ず以下の2ステップでサマリを投稿する**（指摘が0件の場合も投稿する）。

### ステップ 9-1: PR レビューを提出

- 🔴 MUST または 🟡 SHOULD の指摘がある場合: `event: REQUEST_CHANGES`
- 🟢 NICE TO HAVE のみ、または指摘なしの場合: `event: COMMENT`
- `body` にはサマリ全文（下記フォーマット）を含める。

#### MCP の場合

`mcp__github__create_pull_request_review`（または pending review を提出するツール）を使用する。

#### gh CLI の場合

```bash
gh api "repos/${REPO}/pulls/${PR_NUMBER}/reviews" \
  -f event="REQUEST_CHANGES" \
  -f body="$(cat /tmp/review_summary_${PR_NUMBER}.md)"
```

### ステップ 9-2: スティッキーコメントを更新（任意）

同じ PR で再実行した際に前回のサマリを更新できるよう、スティッキーコメント用のコメントも同じ本文で投稿する。

- MCP: `mcp__github_comment__update_claude_comment` 相当のツールを使う。
- gh: Step 3 で保持した「レビュー中」コメントを PATCH で更新するか、新しいコメントを投稿する。

```bash
gh api "repos/${REPO}/issues/comments/${COMMENT_ID}" -X PATCH \
  -f body="$(cat /tmp/review_summary_${PR_NUMBER}.md)"
```

### サマリのフォーマット

以下のテンプレートで出力する（指摘が 0 件のカテゴリは `指摘なし ✅` と記載。そのカテゴリ自体を省略してもよい）。

```markdown
## 🤖 Claude コードレビュー サマリ

### 📊 概要
| 分類 | 件数 |
|------|------|
| 🔴 MUST（修正必須） | X |
| 🟡 SHOULD（修正推奨） | X |
| 🟢 NICE TO HAVE（検討推奨） | X |
| **合計** | **X** |

### 💬 総評
（PR 全体に対する総評を 2〜3 文で記載。良い点も必ず含める）

### 🔴 MUST（修正必須）
該当する指摘がなければ「指摘なし ✅」と記載。ある場合は以下のカテゴリ別に記載:

#### セキュリティ
- （該当する指摘。なければこのカテゴリを省略）

#### バグ・ロジックエラー
- （該当する指摘。なければこのカテゴリを省略）

#### データ損失リスク
- （該当する指摘。なければこのカテゴリを省略）

### 🟡 SHOULD（修正推奨）
該当する指摘がなければ「指摘なし ✅」と記載。ある場合は以下のカテゴリ別に記載:

#### パフォーマンス
- （該当する指摘。なければこのカテゴリを省略）

#### エラーハンドリング
- （該当する指摘。なければこのカテゴリを省略）

#### 可読性・保守性
- （該当する指摘。なければこのカテゴリを省略）

#### テスト
- （該当する指摘。なければこのカテゴリを省略）

### 🟢 NICE TO HAVE（検討推奨）
該当する指摘がなければ「指摘なし ✅」と記載。ある場合は以下のカテゴリ別に記載:

#### コードスタイル
- （該当する指摘。なければこのカテゴリを省略）

#### 命名
- （該当する指摘。なければこのカテゴリを省略）

#### リファクタリング提案
- （該当する指摘。なければこのカテゴリを省略）

---
⏱️ レビュー完了
```

## Step 10: 完了通知

サマリ投稿後、Step 3 で付与した「レビュー中」の状態を解除する。

### MCP の場合

- 「レビュー中」コメントを削除、または Step 9 のサマリ本文で上書きする。
- `mcp__github__update_issue` / 相当のツールでラベル `claude-reviewing` を除去する。

### gh CLI の場合

```bash
# 「レビュー中」コメントを削除
if [ -n "${COMMENT_ID}" ]; then
  gh api "repos/${REPO}/issues/comments/${COMMENT_ID}" -X DELETE --silent || true
fi

# 「claude-reviewing」ラベルを除去
gh pr edit "${PR_NUMBER}" --repo "${REPO}" --remove-label "claude-reviewing" || true
```

最後にユーザーへ、レビュー結果の集計（MUST/SHOULD/NICE TO HAVE の件数）と、PR へのリンクを 1〜2 行で報告して完了。

---

## 運用上の注意

- **コメントの投稿前に一度サマリを作る**: 指摘を洗い出してから投稿順を決める。漏れや重複を防ぐため、内部メモを先に作ってから投稿フェーズに入る。
- **同じ行に複数指摘が付く場合**: 1件のコメントに統合し、分類タグはもっとも重いもの（MUST > SHOULD > NICE TO HAVE）を採用する。
- **実装意図がわからない場合**: 断定せず「〜の意図で合っているか確認したい」と質問形式にする。
- **レビューの一貫性**: 既存コードに存在する問題と PR で新規に混入した問題を区別する。既存からの問題は SHOULD 以下に倒すのが基本（セキュリティ・データ損失リスクは除く）。
- **言語**: レビューコメントとサマリは日本語で記述する（リポジトリの既存コメント言語に合わせる場合はそれに従う）。
- **MCP と gh の混在回避**: 同じセッション内では原則どちらか一方に統一する。途中で切り替えるとコメントの ID 追跡やスティッキーコメント更新で不整合が出る。

---

## レビュー挙動のサマリ

このスキルが満たすべき挙動をまとめると以下のとおり:

- `docs/REVIEW.md` をリポジトリ共通レビュー観点として読み込む
- PR 本文の `<!-- REVIEW_FOCUS -->` ブロックを PR 固有観点として抽出する
- 指摘を 🔴 MUST / 🟡 SHOULD / 🟢 NICE TO HAVE の 3 段階で分類する
- インラインコメント + サマリコメントの 2 段構成で投稿する
- MUST / SHOULD がある場合は `REQUEST_CHANGES`、それ以外は `COMMENT` でレビュー提出する
- スティッキーコメントで再実行時に同じコメントを更新する
- 「レビュー中」ラベル・コメントの開始 → 削除で進捗を可視化する
