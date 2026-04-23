# 出力テンプレート / コマンドリファレンス

`SKILL.md` の **Step 10: 結果の出力** で参照する、GitHub 投稿用コマンド例・コメント本文フォーマット・コンソール出力フォーマット・サマリ Markdown テンプレート集。SKILL.md では出力先の選択ロジックのみを説明し、具体的なテンプレートはこのファイルを参照すること。

## 目次

- [GitHub 投稿: インラインコメント（gh CLI）](#github-投稿-インラインコメントgh-cli)
- [GitHub 投稿: レビュー提出（gh CLI）](#github-投稿-レビュー提出gh-cli)
- [インラインコメント本文のフォーマット](#インラインコメント本文のフォーマット)
- [コンソール出力フォーマット](#コンソール出力フォーマット)
- [サマリ Markdown テンプレート](#サマリ-markdown-テンプレート)

---

## GitHub 投稿: インラインコメント（gh CLI）

`gh` には pending review を扱う専用コマンドがないため、`gh api` で GitHub REST API を直接叩く。MCP が使える場合は `mcp__github__add_comment_to_pending_review` / `mcp__github_inline_comment__create_inline_comment` を優先すること。

```bash
# HEAD_SHA は PR の先頭コミット SHA
HEAD_SHA=$(gh pr view "${PR_NUMBER}" --repo "${REPO}" --json headRefOid -q '.headRefOid')

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
```

- 複数行にまたがるコメントを付ける場合は `start_line` と `start_side` も指定する。
- 削除された行に付ける場合は `side=LEFT`。`LEFT` には suggestion ブロックを付けない。

## GitHub 投稿: レビュー提出（gh CLI）

全インラインコメント投稿後、レビュー提出でサマリ本文を付与する。投稿は 1 回だけ（Issue コメントで別途サマリは投稿しない）。

```bash
# REQUEST_CHANGES または COMMENT を選択
gh api "repos/${REPO}/pulls/${PR_NUMBER}/reviews" \
  -f event="REQUEST_CHANGES" \
  -f body="$(cat /tmp/review_summary_${PR_NUMBER}.md)"
```

### レビュー提出イベントの選択ルール

- 🔴 MUST または 🟡 SHOULD の指摘がある場合: `event: REQUEST_CHANGES`
- **動作確認 subagent が `checks[].status == "fail"` を 1 件以上返している場合**: `event: REQUEST_CHANGES`
- 🟢 NICE TO HAVE のみ、または指摘なしの場合: `event: COMMENT`

### MCP を使う場合の対応ツール

- **方式 A（pending review 一括提出）**: `mcp__github__create_pending_pull_request_review` → `mcp__github__add_comment_to_pending_review` ×N → `mcp__github__submit_pending_pull_request_review`
- **方式 B（インラインコメント 1 件ずつ投稿）**: `mcp__github_inline_comment__create_inline_comment` ×N → `mcp__github__create_pull_request_review`（`event` 指定）

いずれの方式でも、コメント本文の先頭に分類タグ（🔴 / 🟡 / 🟢）を必ず付ける。

## インラインコメント本文のフォーマット

```
🔴 **[MUST]** <指摘の要点を1文で>

<詳細な説明（なぜ問題か、どう影響するか）>

（固有観点 / リポジトリ共通観点 に由来する場合はその旨を記載）

```suggestion
<修正案（1行でも複数行でも）>
```
```

- タグは MUST / SHOULD / NICE TO HAVE に応じて 🔴 / 🟡 / 🟢 を使い分ける。
- suggestion ブロックは修正案が明確なときのみ付ける。削除された行（`side=LEFT`）には付けない。

## コンソール出力フォーマット

`REVIEW_OUTPUT=console` の場合、GitHub には何も投稿せずターミナルに整形して出す。

### 指摘一覧（インラインコメント相当）

1 指摘 1 ブロックで列挙する。件数が多い場合（目安 30 件超）はファイル別にまとめ、見出しを付ける。

```
path/to/file.go:42  🔴 [MUST] セキュリティ
  JWT 検証前に署名アルゴリズムを確認していないため alg=none 攻撃を受け得る。
  suggestion:
    if token.Method.Alg() != "RS256" { return ErrInvalidAlg }
```

### 末尾に追加するもの

- **サマリ**: 後述の「サマリ Markdown テンプレート」をそのまま標準出力に書く。
- **レビュー提出相当の判定**: `判定: REQUEST_CHANGES` のように 1 行で記載する（投稿はしない）。
- **GitHub 投稿への誘導**: 「この結果を GitHub に投稿し直すには再度スキルを呼び出して出力先に GitHub を選択してください」と 1 行添える。
- **レポート保存（任意）**: `/tmp/review_console_<timestamp>.md` に指摘一覧とサマリを保存し、パスをユーザーに伝えると再利用しやすい。

## サマリ Markdown テンプレート

以下のテンプレートで出力する（指摘が 0 件のカテゴリは `指摘なし ✅` と記載。そのカテゴリ自体を省略してもよい）。GitHub 出力・コンソール出力のどちらでも同じテンプレートを使う。

```markdown
## 🤖 Claude コードレビュー サマリ

### 📊 概要
| 分類 | 件数 |
|------|------|
| 🔴 MUST（修正必須） | X |
| 🟡 SHOULD（修正推奨） | X |
| 🟢 NICE TO HAVE（検討推奨） | X |
| **合計** | **X** |

### 🧪 動作確認
| チェック | 結果 | 所要 | 備考 |
|---------|-----|------|------|
| 例: go build ./... | ✅ pass | 12s | - |
| 例: go test ./... | ❌ fail | 45s | TestAuthorize/unauthenticated_user が失敗 |
| 例: golangci-lint run | ⏭ skipped | - | リポジトリに設定なし |

- **総合**: `✅ 全チェック成功` / `❌ 失敗あり（N 件）` / `⚠️ 一部スキップ`
- **再現コマンド（失敗時）**: 失敗したチェックの再現コマンドと、該当ログファイル（/tmp/check-*.log）のパスを記載。
- **スキップしたチェック**: 理由を 1 行で添える（例: docker-compose 起動に 5 分以上かかるため）。

動作確認を実施できなかった場合は、理由に応じて以下のいずれかを記載する:

- `REVIEW_VERIFY=no`（ユーザーが動作確認をスキップ）: `⏭ 動作確認は未実施（ユーザー選択によりスキップ）`
- subagent B が失敗 / ローカルにチェックアウトできなかった等: `⚠️ 動作確認は未実施（理由を記載）`

### 🔎 メタレビュー（subagent C）
| 指標 | 値 |
|------|------|
| 全体品質 | excellent / good / needs_improvement |
| 誤検知（invalid） | N |
| 重要度調整（adjust_severity） | N |
| 文言改善（improve_wording） | N |
| 漏れ補完（missing_findings） | N |

- **subagent C コメント**: overall_comment をそのまま記載（2〜3 文）。
- subagent C が失敗していた場合は `⚠️ メタレビューは未適用（理由を記載）` と明記する。

### 💬 総評
（PR 全体に対する総評を 2〜3 文で記載。良い点も必ず含める。動作確認の結果とメタレビューの結果も踏まえる）

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
