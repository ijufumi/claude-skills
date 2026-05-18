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

以下のテンプレートで出力する（観点 / severity の 0 件セルは `0` のままにし、見出し下の指摘リストは `指摘なし ✅` と記載するか省略する）。GitHub 出力・コンソール出力のどちらでも同じテンプレートを使う。

```markdown
## 🤖 Claude コードレビュー サマリ

### 🔧 モード
`通常`（1 subagent A_review が 10 観点を横断レビュー + 1 subagent C_review がメタレビュー） /
`詳細`（10 観点に分割し A_i × N で並列レビュー + C_i × N で観点ごとに評価）
※ どちらか一方を、採用したモードに応じて記載する。

### 📊 概要
**Severity 別件数:**
| 分類 | 件数 |
|------|------|
| 🔴 MUST（修正必須） | X |
| 🟡 SHOULD（修正推奨） | X |
| 🟢 NICE TO HAVE（検討推奨） | X |
| **合計** | **X** |

**観点別件数（10 観点 × severity）:**
| 観点 | 🔴 | 🟡 | 🟢 | 状態 |
|------|----|----|----|------|
| コード正確性 (correctness) | N | N | N | ✅ |
| プロジェクト規約 (conventions) | N | N | N | ✅ |
| パフォーマンス (performance) | N | N | N | ✅ |
| テストカバレッジ (test_coverage) | N | N | N | ✅ |
| セキュリティ (security) | N | N | N | ✅ |
| エラーハンドリング (error_handling) | N | N | N | ✅ |
| 可読性・保守性 (readability) | N | N | N | ✅ |
| シンプル化 (simplify) | N | N | N | ✅ |
| リポジトリ共通観点 (repo_common) | N | N | N | ✅ / ⏭ 未起動 |
| PR 固有観点 (pr_specific) | N | N | N | ✅ / ⏭ 未起動 |

- 「状態」列は `✅`（A_i 成功）/ `⚠️ 失敗`（A_i 失敗）/ `⏭ 未起動`（条件未充足）のいずれか。

### 🚨 マージブロッカー
最重要 0〜5 件を観点横断で抜粋（MUST / 動作確認失敗のうち、マージを止めるべき指摘）。0 件なら「なし ✅」。

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

### 🔎 メタレビュー

採用したモードに応じて以下のいずれかを記載する。

#### 通常モード（C_review）

C_review の集計を 1 行で記載した上で、`per_perspective_quality[]` を観点ごとに 1 行ずつ列挙する:

```
C_review: invalid 2 / severity 調整 1 / 文言改善 3 / 漏れ補完 1（overall_quality: good）
```

| 観点 | overall_quality | コメント |
|------|------|------|
| コード正確性 (correctness) | good | 境界条件は概ね押さえられている |
| プロジェクト規約 (conventions) | good | 周辺ファイルのスタイルに揃っている |
| パフォーマンス (performance) | needs_improvement | ループ内 DB アクセスが 1 箇所残る |
| ... | ... | ... |

- C_review が失敗していた場合: `⚠️ メタレビューは未適用（C_review 失敗）` と記載し、表は省略してよい。
- `per_perspective_quality[]` には 10 観点すべてのエントリが入っている想定。条件付きで起動しなかった観点（`repo_common` / `pr_specific`）が無いケースでも、A_review がスキップした旨を `overall_quality = "good"` / コメント = `インプット無し（観点として未起動）` のように埋めるか、行自体を省略する。

#### 詳細モード（観点別 C_i）

観点ごとに 1 行ずつ列挙する:

| 観点 | overall_quality | invalid | severity 調整 | 文言改善 | 漏れ補完 |
|------|------|---|---|---|---|
| コード正確性 (correctness) | good | 0 | 1 | 0 | 1 |
| セキュリティ (security) | good | 1 | 0 | 1 | 0 |
| ... | ... | ... | ... | ... | ... |
| **合計** | - | N | N | N | N |

- C_i が失敗していた / 起動されなかった観点は `overall_quality` 列を `⚠️ 未適用` と記載する。

### 💬 総評
2〜4 文で記載。以下の 3 要素を必ず含める:

1. **PR 概要 + 良い点**: 差分・PR 本文・各 A_i の `overall_comment` から、PR が何をしているか・良い点を 1〜2 文で要約。
2. **主要リスク**: マージブロッカー扱いの指摘から最重要 1〜3 件を抜粋して短く言及。
3. **観点別品質の偏り**: C_i の `overall_quality` が割れている場合、最も低い観点を 1 つ言及（例: `観点別品質: performance が needs_improvement、その他は good 以上`）。

### 🔴 MUST（修正必須）
該当する指摘がなければ「指摘なし ✅」と記載。ある場合は**観点別カテゴリ**で記載:

#### セキュリティ (security)
- （該当する指摘。なければこのカテゴリを省略）

#### コード正確性 (correctness)
- （該当する指摘。なければこのカテゴリを省略）

#### エラーハンドリング (error_handling)
- （該当する指摘。なければこのカテゴリを省略）

（他観点で MUST がある場合は同形式で追加）

### 🟡 SHOULD（修正推奨）
該当する指摘がなければ「指摘なし ✅」と記載。ある場合は**観点別カテゴリ**で記載:

#### パフォーマンス (performance)
- （該当する指摘。なければこのカテゴリを省略）

#### テストカバレッジ (test_coverage)
- （該当する指摘。なければこのカテゴリを省略）

#### 可読性・保守性 (readability)
- （該当する指摘。なければこのカテゴリを省略）

#### プロジェクト規約 (conventions)
- （該当する指摘。なければこのカテゴリを省略）

（他観点で SHOULD がある場合は同形式で追加）

### 🟢 NICE TO HAVE（検討推奨）
該当する指摘がなければ「指摘なし ✅」と記載。ある場合は**観点別カテゴリ**で記載:

#### シンプル化 (simplify)
- （該当する指摘。なければこのカテゴリを省略）

#### 可読性・保守性 (readability)
- （該当する指摘。なければこのカテゴリを省略）

（他観点で NICE TO HAVE がある場合は同形式で追加）

---
⏱️ レビュー完了
```
