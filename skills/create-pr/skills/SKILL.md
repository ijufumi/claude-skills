---
name: create-pr
description: GitHub の Pull Request を作成するスキル。カレントブランチのコミット内容を要約し、マージ先ブランチ（未指定時は main / master を自動検出）に対する PR を作成してリンクを返す。実行前にマージ先ブランチ・PR タイトル・本文をユーザーに提示して確認を取り、承認後に PR を作成する。GitHub 操作は MCP（`mcp__github__create_pull_request` など）が使える場合は MCP を優先し、使えない場合は `gh` CLI にフォールバックする。ユーザーが「PR 作成」「PR を作って」「プルリクエスト作成」「create PR」「open a PR」「プルリク出して」「PR にして」「MR 作成」「この変更で PR」「現在のブランチで PR」などに言及した場合にこのスキルを使うこと。ブランチをプッシュしていない場合は先にプッシュ可否をユーザーに確認してから push も含めて行う。Draft PR / Ready PR の選択やテンプレート（.github/PULL_REQUEST_TEMPLATE.md）の有無も考慮する。
---

# PR 作成スキル

GitHub 上に Pull Request を作成するためのスキル。カレントブランチの差分・コミット履歴を要約し、マージ先ブランチに対する PR を作成してリンクを返すところまでを一貫して行う。

## 前提条件

- カレントディレクトリが Git リポジトリであり、リモート（origin 等）に GitHub を指していること
- カレントブランチにベースブランチから分岐したコミットが 1 件以上あること（差分が無ければ PR は作れないためユーザーに通知して中断）
- 以下のいずれかが利用可能であること:
  - **推奨**: GitHub MCP サーバー（`mcp__github__create_pull_request`, `mcp__github__get_file_contents`, `mcp__github__list_pull_requests` など）
  - **フォールバック**: `gh` CLI（`gh auth login` 済み、`repo` スコープ以上）

> GitHub MCP が使える場合は必ず MCP を優先すること。同じセッション内で MCP と `gh` を混在させるのは避け、原則どちらか一方に統一する。

---

## ワークフロー概要

```
[Step 1: 実行環境の確認（MCP or gh）]
  → [Step 2: リポジトリ / ブランチ情報の収集]
  → [Step 3: マージ先ブランチの確定]
  → [Step 4: 差分・コミットの収集と要約]
  → [Step 5: 既存 PR の確認（重複防止）]
  → [Step 6: PR テンプレートの読み込み（あれば）]
  → [Step 7: PR タイトル・本文のドラフト生成と確認]
  → [Step 8: リモートへの push 確認]
  → [Step 9: PR の作成]
  → [Step 10: 結果（PR URL）の報告]
```

**重要**: Step 3（マージ先ブランチ）、Step 7（PR タイトル・本文）、Step 8（push 実行可否）の 3 点はユーザーに提示して承認を得てから進める。ユーザーが最初のリクエスト内で明示している項目は、その意図を 1 行で復唱するに留め、往復の確認は省略してよい（例: 「main に PR を作って」→ マージ先は main として即進行）。

---

## Step 1: 実行環境の確認

GitHub 操作に使えるツールを確認し、以下の順で優先する。

1. **GitHub MCP が利用可能か**: 現在のセッションで `mcp__github__create_pull_request`（または同等の PR 作成ツール）が登録されているかを確認する。PR 作成・既存 PR 一覧取得・リポジトリ情報取得ができれば MCP を採用する。
2. **`gh` CLI が利用可能か**: `gh auth status` で認証済みかを確認する。MCP が使えず `gh` が使えればフォールバックとして `gh` を使う。
3. どちらも使えない場合は、`gh auth login` または MCP サーバー設定の案内を出して中断する。

ユーザーへの最初のテキスト出力で、「どちらを使って PR を作成するか」を 1 行で明示すること（例: `GitHub MCP を使って PR を作成します`）。

## Step 2: リポジトリ / ブランチ情報の収集

以下の情報を収集する。

```bash
# リポジトリ（owner/repo）の特定
gh repo view --json nameWithOwner -q '.nameWithOwner'
# もしくは
git remote get-url origin

# カレントブランチ名 / HEAD SHA
git branch --show-current
git rev-parse HEAD

# リモート追跡ブランチの状況（push 済みかの判断に使う）
git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || echo "(no upstream)"
git status -sb
```

MCP の場合は `mcp__github__get_me` でアクセス可能なユーザーを確認したり、リモート URL から `owner/repo` を推定する。

以下をメモしておく:

- `REPO`（例: `ijufumi/claude-skills`）
- `HEAD_BRANCH`（カレントブランチ名）
- `HEAD_SHA`
- `HAS_UPSTREAM`（リモート追跡ブランチがあるか）
- `AHEAD / BEHIND`（リモートとの差分コミット数。upstream がある場合のみ）

ブランチが `main` / `master` などのベースブランチそのものだった場合は、そのままでは PR を作れない（head と base が同じになるため）。中断せず、以下の手順で自動的に作業ブランチを切り出してから以降の Step を続行する。

1. **変更内容の要約**: `git status --porcelain` と `git diff` / `git diff --cached` を読み、ステージ / 未ステージ / 未追跡ファイルをまとめて「何を変えたか」を 3〜5 語程度の短い英語スラッグに要約する（例: `add-create-pr-skill`, `fix-login-validation`, `update-readme-install`）。
2. **ブランチ名の生成**: リポジトリの既存 PR / 直近ブランチ名の命名規則を `git log --all --pretty='%D' | head -50` や `gh pr list --state all --limit 20 --json headRefName -q '.[].headRefName'` で確認し、プレフィックス（`feat/` / `fix/` / `docs/` / `chore/` 等）を揃える。規則が判別できない場合は `work/` + スラッグを既定とする。
3. **ユーザーへの提示**: 生成したブランチ名を 1 行で提示して承認を取る（例: `作業ブランチとして 'feat/add-create-pr-skill' を作成して続行してよいですか？`）。ユーザーから別名の指示があればそれを採用する。
4. **ブランチ作成**: `git switch -c <BRANCH_NAME>` で作成してカレントを切り替える。未コミット変更はそのまま新ブランチに引き継がれる（`main` / `master` 側には残らない）。
5. **コミット可否の確認**: この時点でまだ未コミットの変更がある場合、Step 7 の本文ドラフト提示の直前でユーザーに「この内容でコミットしてから PR 作成してよいですか？」と確認する。勝手に `git commit` しない。承認後にコミットメッセージ案も合わせて提示してから実行する。

> ベースブランチ上に他人の未 push コミットがある可能性は低いが、念のため新ブランチ作成前に `git log origin/${BASE_BRANCH}..HEAD --oneline` で差分コミットの有無を確認しておくとよい。差分があればユーザーに「main にローカル先行コミットが N 件あります。ブランチに移してよいですか？」と 1 行確認する。

## Step 3: マージ先ブランチの確定

ユーザーが明示的にマージ先を指定している場合はそれを採用する（例: 「develop に PR」「base=release/v2」）。指定がない場合は以下の順で自動検出する。

```bash
# リポジトリのデフォルトブランチを取得
gh repo view --json defaultBranchRef -q '.defaultBranchRef.name'

# または origin/HEAD から
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'
```

検出ロジック:

1. `gh repo view` / MCP からデフォルトブランチが取れればそれを採用する。
2. 取れなければローカルで `main` → `master` の順にリモート（`origin/<name>`）が存在するかを確認し、最初に見つかったものを採用する。
3. どれも見つからなければユーザーにベースブランチ名を尋ねる。

検出したマージ先を `BASE_BRANCH` として保持する。自動検出した場合は、ユーザーに「マージ先は `main` で進めます。変更する場合は教えてください」と 1 行で伝えてから次に進む（明示指定があった場合は復唱のみでよい）。

`BASE_BRANCH` と `HEAD_BRANCH` が同じ場合は中断する。

## Step 4: 差分・コミットの収集と要約

マージ先との差分を取得し、PR 本文で使う要約を作る。

```bash
# マージベースを計算
MERGE_BASE=$(git merge-base "origin/${BASE_BRANCH}" HEAD)

# コミット一覧（件名 + 本文の1行目）
git log "${MERGE_BASE}..HEAD" --pretty='%h %s' --no-merges

# 変更ファイル一覧（追加/変更/削除）
git diff --name-status "${MERGE_BASE}...HEAD"

# 差分統計（行数・ファイル数）
git diff --stat "${MERGE_BASE}...HEAD"

# 必要に応じて実際のパッチ
git diff "${MERGE_BASE}...HEAD" > /tmp/create_pr_diff.patch
```

以下の観点で要約を作る:

- **何を変えたか**: 機能追加 / バグ修正 / リファクタ / ドキュメント / テスト / CI など分類と、対象モジュール・ファイル群。
- **なぜ変えたか**: コミットメッセージに書かれている動機・背景。推測で補足しすぎない（書かれていなければ「（コミットメッセージから読み取れる範囲で）」と留保する）。
- **どう変えたか**: 実装方針・採用したアプローチ。細かい実装詳細までは書かず、重要な設計判断を中心に。
- **影響範囲**: 破壊的変更、マイグレーション要否、設定追加、依存パッケージ変更の有無。
- **動作確認**: コミットメッセージや差分から読み取れるテスト追加・手動確認の痕跡。やっていないことは書かない。

要約の粒度:

- コミットが 1 件だけ: そのコミットメッセージを基に 1〜3 行で要約。
- コミットが複数ある場合: 「変更の塊」ごとにまとめる。コミット単位で列挙するのではなく、PR としての意図が伝わる構造にする。
- 非常に大きな PR（例: 30 コミット / 50 ファイル超）: 詳細はコミット履歴へのリンクに委ね、PR 本文では主要な変更のみを挙げる。

## Step 5: 既存 PR の確認（重複防止）

同じ `HEAD_BRANCH` → `BASE_BRANCH` の open 中 PR が既に存在する場合、新規作成ではなく既存 PR の更新（ブランチ push のみ）で足りるケースが多い。重複作成を避けるため事前に確認する。

```bash
gh pr list --repo "${REPO}" --state open --head "${HEAD_BRANCH}" --base "${BASE_BRANCH}" \
  --json number,url,title,isDraft
```

MCP の場合は `mcp__github__list_pull_requests` で `head=OWNER:HEAD_BRANCH` / `base=BASE_BRANCH` / `state=open` で検索する。

- 既存 PR が見つかった場合: ユーザーに「既に PR #N が存在します: URL。新規作成せず、このブランチの push だけ行いますか？」と確認する。ユーザーが「はい」なら Step 8 の push のみ行い、Step 9 をスキップして Step 10 で既存 PR のリンクを返す。「新規で作りたい」と言われた場合でも、基本的には同一 head/base の open PR がある間は新規作成できない点を案内する（どうしても新規が必要なら既存 PR を close してから、とユーザーに判断してもらう）。
- 見つからなかった場合: そのまま次に進む。

## Step 6: PR テンプレートの読み込み（あれば）

リポジトリに PR テンプレートがあれば、それを下敷きに本文を組み立てる。優先順位:

1. `.github/PULL_REQUEST_TEMPLATE.md`
2. `.github/pull_request_template.md`
3. `docs/PULL_REQUEST_TEMPLATE.md`
4. `PULL_REQUEST_TEMPLATE.md`

```bash
for f in .github/PULL_REQUEST_TEMPLATE.md .github/pull_request_template.md \
         docs/PULL_REQUEST_TEMPLATE.md PULL_REQUEST_TEMPLATE.md; do
  [ -f "$f" ] && echo "FOUND: $f" && break
done
```

存在する場合は `Read` でテンプレートを読み込み、テンプレートのセクション構成（## Summary / ## Test plan など）に合わせて Step 4 の要約を流し込む。テンプレートの項目で情報が無いものは `(未確認)` や `(該当なし)` と記載する。勝手に埋めない。

存在しない場合は以下の既定テンプレートを使う:

```markdown
## 概要

<Step 4 の要約を 2〜4 行で>

## 変更内容

- <主要な変更 1>
- <主要な変更 2>
- <主要な変更 3>

## 影響範囲 / 注意点

<破壊的変更・マイグレーション・設定追加があれば記載。無ければ「特になし」>

## 動作確認

<コミットから読み取れる範囲で。未確認なら「未実施」>
```

## Step 7: PR タイトル・本文のドラフト生成と確認

PR タイトルのルール:

- 70 文字以内に収める（GitHub UI での視認性優先）。
- リポジトリの既存 PR が Conventional Commits 風（`feat:` / `fix:` / `docs:` 等）を採用していればそれに揃える。直近の PR / コミットタイトルを `git log` で確認してから決める。
- コミットが 1 件だけなら、そのコミットメッセージのサブジェクトを流用してよい。
- 複数コミットなら、PR としての主題を 1 行で表す（コミットの羅列ではなく要約）。

タイトル + 本文のドラフトをユーザーに提示して承認を得る。提示フォーマット（例）:

```
以下の内容で PR を作成します。修正したい箇所があれば指示してください（そのまま OK なら「OK」などと返してください）。

マージ先: main ← feat/create-pr-skill
タイトル: feat: PR 作成 skill を追加

本文:
---
## 概要
...
---
```

ユーザーが修正を依頼した場合はタイトル・本文を差し替えて再提示する。承認が取れたら次に進む。

## Step 8: リモートへの push 確認

PR を作成するにはリモートにブランチが push されている必要がある。状態ごとに以下のように扱う。

- **upstream なし（未 push）**: `git push -u origin <HEAD_BRANCH>` の実行可否をユーザーに確認してから実行する。
- **upstream あり・ahead > 0（ローカル先行）**: `git push` の実行可否をユーザーに確認してから実行する。
- **upstream あり・ahead = 0・behind = 0**: そのまま Step 9 に進む。
- **upstream あり・behind > 0**: ローカルが遅れている可能性がある。ユーザーに「リモートのほうが先行しています。`git pull --rebase` してから push し直しますか？」と確認する。勝手に `pull` / `rebase` は実行しない。

force push（`--force` / `--force-with-lease`）は**明示的にユーザーが依頼した場合のみ**実行する。既定では通常の push のみ。

push コマンド例:

```bash
# 初回
git push -u origin "${HEAD_BRANCH}"

# 2 回目以降
git push
```

push が失敗した場合はエラー内容をそのまま報告し、ユーザーに対応を委ねる（勝手に force push には切り替えない）。

## Step 9: PR の作成

### MCP の場合（推奨）

`mcp__github__create_pull_request` を呼び出す。主要パラメータ:

- `owner`, `repo`: Step 2 で取得したもの
- `head`: `HEAD_BRANCH`（fork 越しの場合は `OWNER:HEAD_BRANCH` 形式）
- `base`: `BASE_BRANCH`
- `title`: Step 7 で確定したタイトル
- `body`: Step 7 で確定した本文
- `draft`: ユーザーから Draft 指定があれば `true`、既定は `false`
- `maintainer_can_modify`: 既定 `true`（fork からの PR でメンテナが編集可）

### gh CLI の場合（フォールバック）

HEREDOC で本文を渡して改行・特殊文字を安全に扱う。

```bash
gh pr create \
  --repo "${REPO}" \
  --base "${BASE_BRANCH}" \
  --head "${HEAD_BRANCH}" \
  --title "${PR_TITLE}" \
  --body "$(cat <<'EOF'
<Step 7 で確定した本文>
EOF
)"
```

Draft にする場合は `--draft` を付ける。

### 失敗時の扱い

- 既存 PR と head/base が衝突して失敗: Step 5 の確認漏れ。既存 PR のリンクを返す。
- ブランチ未 push で失敗: Step 8 を案内して再実行する。
- 権限エラー: `gh auth refresh` / MCP サーバー設定の見直しを案内する。

失敗内容はユーザーに生のエラーメッセージと合わせて報告する（原因を勝手に推測せず、エラーの事実を伝える）。

## Step 10: 結果（PR URL）の報告

作成した PR の URL をターミナルに明示的に出力し、簡潔なサマリを添える。

出力例:

```
✅ PR を作成しました

- タイトル: feat: PR 作成 skill を追加
- マージ先: main ← feat/create-pr-skill
- URL: https://github.com/ijufumi/claude-skills/pull/42
- 状態: Ready for review
```

Draft で作成した場合は `- 状態: Draft` と記載する。既存 PR が存在したため新規作成をスキップした場合は `(既存 PR を更新しました)` と明示する。

この出力をもってスキルを終了する。レビュー依頼・マージ・追加のコメント投稿までは行わない（必要ならユーザーが別途依頼する）。

---

## セキュリティ / 運用上の注意

- **3 点の確認は必ず実行する**: Step 3（マージ先ブランチ）、Step 7（タイトル・本文）、Step 8（push 可否）。初回リクエストで明示されている項目のみ 1 行の復唱で省略してよい。
- **force push は勝手にやらない**: 既定は通常 push。`--force` / `--force-with-lease` はユーザーの明示指示がある場合のみ。
- **勝手なブランチ操作をしない**: `git pull` / `git rebase` / `git reset` / ベースブランチの `git merge` などはユーザー承認なしに実行しない。behind の場合は状況を報告して判断を仰ぐ。
- **PR 本文に機密を書かない**: 差分に API キー・パスワード・トークンらしき文字列が含まれていた場合は、本文に転記せず、ユーザーに「機密らしき値が差分に含まれています。PR 作成前に履歴から除去を推奨します」と警告する。
- **存在しない事実を書かない**: 動作確認・テスト追加など、コミット・差分から読み取れない内容は PR 本文に書かない。「未確認」「該当なし」と素直に記載する。
- **言語**: リポジトリの既存 PR の言語（英語 / 日本語）に揃える。直近の PR を数件参照して判断する。明確でなければユーザーの対話言語に合わせる。
- **MCP と gh の混在回避**: 同じセッション内では原則どちらか一方に統一する。
