---
name: git-sync-cleanup
description: ローカルリポジトリを最新化し、不要になったローカルブランチを掃除するスキル。ベースブランチ（main / master を自動検出）に切り替え、`git pull --prune` で origin から最新化し、リモート側ですでに削除されているローカルブランチ（upstream が `gone` のもの）を一括削除する。実行前に未コミット変更を検知して中断し、削除対象は一覧提示してユーザーから一括承認を取り、未マージのブランチは安全のため削除せずリストで報告する。リモートは origin 固定。ユーザーが「ローカル最新化」「コードを最新化」「main を pull」「master 更新」「最新の main に追従」「ブランチ整理」「ブランチ掃除」「不要ブランチ削除」「リモートで削除されたブランチ」「マージ済みブランチを消したい」「git pull --prune」「git fetch --prune」「prune」「gone ブランチ」「朝イチの同期」「作業開始時の同期」「pull して掃除」「sync」「cleanup branches」「prune local branches」などに言及した場合にこのスキルを使うこと。「pull」「最新化」「同期」「ブランチ削除」だけでも、ローカル作業の起点としてこのスキルが適切であれば積極的に使ってよい。
---

# ローカル最新化 & ブランチ掃除スキル

ローカルリポジトリを `origin` の最新に追従させ、リモート側で削除済みのローカルブランチを掃除するためのスキル。日々の作業開始時や、長期開発の合間にローカルが散らかってきたタイミングで使う。

## 前提条件

- カレントディレクトリが Git リポジトリであること
- `origin` という名前のリモートが存在し、認証済みで `git fetch` / `git pull` が可能なこと
- `origin` 上に `main` または `master` のいずれかのブランチが存在すること

> リモートは **`origin` 固定** で扱う。複数リモートを運用していても、このスキルは `origin` のみを対象に fetch / prune / pull する。他リモートの掃除をしたい場合はユーザーが個別に指示する想定。

---

## ワークフロー概要

```
[Step 1: 環境の確認]
  → [Step 2: 未コミット変更の検出（あれば中断）]
  → [Step 3: ベースブランチの検出と切り替え]
  → [Step 4: git pull --prune で最新化]
  → [Step 5: 削除候補（upstream が gone のブランチ）の検出]
  → [Step 6: 削除対象一覧の提示と一括承認]
  → [Step 7: 一括削除（未マージは保護してリスト報告）]
  → [Step 8: 結果サマリ]
```

**ユーザー承認が必須なのは Step 6 の 1 箇所のみ**。Step 2 で未コミット変更を検出した場合は承認ではなく「中断 → 状況報告 → ユーザーに対応を委ねる」で扱う。

ユーザーが最初のリクエストで「全部 OK」「掃除も含めて全部やって」など事前承認を明言している場合は、Step 6 の確認を 1 行の復唱に省略してよい（例: `gone ブランチ 5 件を削除します`）。

---

## Step 1: 環境の確認

最初にツールが揃っているかを軽く確認する。

```bash
# Git リポジトリか
git rev-parse --is-inside-work-tree

# origin が存在するか
git remote get-url origin
```

どちらかが失敗した場合は、その内容をユーザーに報告して中断する。Git リポジトリでない場合は「ここは Git リポジトリではないようです」と素直に伝える（`git init` は勝手にしない）。`origin` が無い場合は「`origin` リモートが見つかりません。リモートを追加してから再実行してください」と案内する。

ユーザーへの最初のテキスト出力で、これから行うことを 1 行で予告すること（例: `origin から最新化して、不要なローカルブランチを掃除します`）。

## Step 2: 未コミット変更の検出（あれば中断）

ベースブランチに切り替える前に、ワークツリーがクリーンであることを確認する。`git switch` は変更が衝突しない場合は通すが、`git pull` も含めて予期せぬ事故を避けるため、**未コミット変更がある時点で中断する**。勝手に `stash` / `commit` / `restore` はしない。

```bash
# 変更の有無を一気に判定
git status --porcelain
```

出力が空ならクリーン。空でなければ以下のように扱う:

- ステージ済み・未ステージ・未追跡ファイルの内訳を `git status -sb` で取得してそのまま提示する。
- 「未コミットの変更があるためスキルを中断しました。`git stash` / `git commit` / `git restore` のいずれかで状態を整えてから再実行してください」と案内し、スキルを終了する。
- ユーザーから「stash してから続けて」など明示の指示があった場合のみ、`git stash push -u -m "git-sync-cleanup auto stash"` を実行してから次に進み、最後（Step 8 の前）に `git stash pop` を試みて結果を報告する。pop が衝突した場合は無理に解消せず、stash 名と状況を伝える。

> ベースブランチに切り替えた後で `git pull` が走るため、未追跡ファイルが上書きされるリスクもある。中断のしきい値は「未コミット変更が **少しでも** あれば」とする。

## Step 3: ベースブランチの検出と切り替え

切り替え先のベースブランチ（`main` または `master`）を以下の順で決める。

```bash
# 1. origin/HEAD のシンボリックリンクから（最も信頼できる）
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'

# 2. リモート上に main / master が存在するか
git ls-remote --exit-code --heads origin main   >/dev/null 2>&1 && echo main
git ls-remote --exit-code --heads origin master >/dev/null 2>&1 && echo master
```

検出ロジック:

1. `git symbolic-ref refs/remotes/origin/HEAD` が取れればそれを採用する（`origin` のデフォルトブランチ）。取れなければ `git remote set-head origin -a` を 1 度だけ試して再取得してもよい。
2. それでも決まらなければ `main` → `master` の順でリモート存在確認をして、最初に見つかったものを採用する。
3. どちらも見つからなければ、ベースブランチ名をユーザーに尋ねて中断する（勝手な推測はしない）。

採用したベースブランチを `BASE_BRANCH` として保持する。

カレントブランチを記憶し、`BASE_BRANCH` に切り替える。

```bash
ORIGINAL_BRANCH=$(git branch --show-current)

# すでに BASE_BRANCH 上にいる場合は switch 不要
if [ "$ORIGINAL_BRANCH" != "$BASE_BRANCH" ]; then
  # ローカルに BASE_BRANCH が無ければ origin から作成
  if git show-ref --verify --quiet "refs/heads/${BASE_BRANCH}"; then
    git switch "${BASE_BRANCH}"
  else
    git switch -c "${BASE_BRANCH}" "origin/${BASE_BRANCH}"
  fi
fi
```

`switch` が失敗した場合は、エラー内容をそのまま報告して中断する（force / restore で強行突破しない）。

## Step 4: `git pull --prune` で最新化

`origin` の `BASE_BRANCH` から最新を取り込みつつ、リモートトラッキング参照を prune する。

```bash
git pull --prune origin "${BASE_BRANCH}"
```

このコマンドにより:

- `origin/${BASE_BRANCH}` を fetch して `BASE_BRANCH` にマージ（fast-forward 想定）
- `origin/*` のリモートトラッキング参照のうち、リモート側で消えているものを削除（= Step 5 で `gone` 判定が正しく入るための前提）

merge / rebase の競合が発生した場合（典型的にはユーザーが `BASE_BRANCH` 上で直接コミットしていたケース）は中断し、状況を報告する。勝手に `--rebase` / `--no-rebase` を切り替えたり、`reset --hard` で回避したりしない。

`git pull` が成功したら、取り込んだコミット数を `git log @{1}..HEAD --oneline | wc -l` などで参考までに把握しておくとサマリで使える（必須ではない）。

## Step 5: 削除候補（upstream が gone のブランチ）の検出

`origin` 上で削除されたブランチをトラッキングしているローカルブランチを抽出する。Step 4 の prune が済んでいる前提で、以下が確実な検出方法:

```bash
git for-each-ref \
  --format='%(refname:short)|%(upstream)|%(upstream:track)' \
  refs/heads/ \
  | awk -F'|' '$2 ~ /^refs\/remotes\/origin\// && $3 == "[gone]" { print $1 }'
```

ポイント:

- `upstream` が `refs/remotes/origin/...` のものに限定する（他リモート追跡のブランチには触らない）。
- `upstream:track == "[gone]"` のものだけを抽出する（upstream 未設定のローカルオンリーなブランチや、ahead/behind のブランチは対象外）。
- `BASE_BRANCH` 自身は通常 upstream が存在するため、この抽出には引っかからない。それでも保険として、結果から `BASE_BRANCH` を除外しておくと安全。

抽出結果を `GONE_BRANCHES` として保持する。

候補が 0 件の場合は Step 6・Step 7 をスキップして Step 8 に進む（その旨を「掃除対象はありませんでした」と簡潔に伝える）。

## Step 6: 削除対象一覧の提示と一括承認

候補が 1 件以上ある場合、**まとめてユーザーに提示し、一括承認を取る**。1 ブランチごとの個別確認はしない。

提示フォーマット（例）:

```
リモートで削除済みのローカルブランチが 5 件見つかりました。

  - feat/login-validation     (last commit: 2026-04-20, abc1234, "validate email format")
  - fix/typo-readme           (last commit: 2026-04-18, def5678, "fix typo in README")
  - chore/update-deps         (last commit: 2026-04-15, 9abcdef, "bump axios to 1.7.0")
  - feat/dashboard-prototype  (last commit: 2026-03-30, 0123456, "wip dashboard")
  - hotfix/payment-rounding   (last commit: 2026-03-22, 7890abc, "fix rounding error")

これらをまとめて削除します（未マージのものは安全のため自動的に保護してリスト報告します）。進めてよいですか？
```

各ブランチの参考情報は以下で取得する:

```bash
git log -1 --format='%cs %h "%s"' "${branch}"
```

ユーザーが承認したら Step 7 に進む。拒否された場合や、特定ブランチだけ残したいと言われた場合は、対象リストから外して再提示するか、そのままスキルを終了する（ユーザーの意図に従う）。

## Step 7: 一括削除（未マージは保護してリスト報告）

承認された一覧に対して `git branch -d` を実行する。`-d` は `BASE_BRANCH` にマージ済みかを Git が自動判定し、未マージの場合は失敗するため、安全側に倒れる。**`-D`（強制削除）は使わない**。

```bash
DELETED=()
KEPT_UNMERGED=()
KEPT_OTHER=()

for branch in "${GONE_BRANCHES[@]}"; do
  if output=$(git branch -d "${branch}" 2>&1); then
    DELETED+=("${branch}")
  else
    # `git branch -d` は未マージ時に "not fully merged" を返す
    if echo "${output}" | grep -q "not fully merged"; then
      KEPT_UNMERGED+=("${branch}")
    else
      KEPT_OTHER+=("${branch}|${output}")
    fi
  fi
done
```

未マージで残ったブランチについては、削除しない。代わりに「リモートでは消えているがローカルではマージされていないため保護しました」とリストで報告する。ユーザーが内容を確認した上で `git branch -D <name>` を手動で実行する想定。

`-d` でも `not fully merged` 以外の理由で失敗した場合（例: ブランチが他の worktree でチェックアウト中など）は、エラー文をそのままサマリに転記する。

> Step 6 の承認は「`-d` での一括削除」までを含む。未マージブランチを `-D` で強制削除するかどうかは別の意思決定であり、ユーザーが明示的に依頼しない限り行わない。

## Step 8: 結果サマリ

最後に元のブランチ位置に戻すかどうかを判断し、結果を報告する。

**ブランチを戻すか:**

- ユーザーが最初のリクエストで「main に居ていい」「main で続ける」のように示している場合、`BASE_BRANCH` のままで終わる。
- それ以外で、`ORIGINAL_BRANCH` が `BASE_BRANCH` と異なり、かつ削除されていない（= 現存する）場合は、戻すかをユーザーに 1 行で確認する（例: `元の 'feat/foo' に戻しますか？`）。
- `ORIGINAL_BRANCH` が今回削除されたブランチに含まれる場合は、戻れないので `BASE_BRANCH` のままにし、その旨を報告する。

**サマリ出力（例）:**

```
✅ ローカル最新化 & ブランチ掃除が完了しました

- ベースブランチ: main（origin から 3 コミット取り込み）
- カレントブランチ: main（元: feat/login-validation → 削除済みのため main に留まります）

削除済み (3 件):
  - feat/login-validation
  - fix/typo-readme
  - chore/update-deps

保護 (未マージ・2 件):
  - feat/dashboard-prototype
  - hotfix/payment-rounding
  → 削除する場合は `git branch -D <name>` を手動で実行してください

エラー (0 件):
  なし
```

サマリ内の各セクションは件数が 0 でも「なし」と明示的に書く（沈黙すると「やったのか / やってないのか」がぼやけるため）。

この出力をもってスキルを終了する。続けて作業ブランチを切る・PR を出す等は別スキル（`create-pr` 等）に委ねる。

---

## セキュリティ / 運用上の注意

- **未コミット変更は中断のしきい値**: ステージ済みでも未追跡でも「少しでもあれば中断」。`git pull` のマージや `git switch` の意図せぬ巻き込みでローカル変更を失わないため。勝手に `stash` / `commit` / `restore` しない。
- **ユーザー承認は Step 6 の 1 箇所**: それ以外の Step は事前に決まったオペレーションのため逐一確認しない。ただし最初のテキストで「これから何をするか」を 1 行予告すること。
- **`-D`（強制削除）は使わない**: 「リモートで消えている」と「ローカルでマージ済み」は別の概念。未マージのまま消えているブランチは、リベースで履歴が再構築された PR や、レビュー前に消されたブランチかもしれない。安全側に倒し、ユーザー判断に委ねる。
- **リモートは `origin` 固定**: 他リモート（`upstream` / `fork` 等）には触らない。`origin` 以外を追跡しているローカルブランチは Step 5 の抽出時点で除外される。
- **`BASE_BRANCH` を消さない**: 抽出結果から `BASE_BRANCH` を除外しておく。通常は upstream が存在するため引っかからないが、保険として明示的に除外する。
- **勝手な force / reset / rebase をしない**: `git pull` が競合した、`git switch` が失敗した、といった場面で `--force` / `--hard` / `--rebase` で押し切らない。状況をそのまま報告し、ユーザーに対応を委ねる。
- **`stash` を勝手に使わない**: ユーザーが明示指示した場合のみ。auto-stash の pop が衝突して気づかぬ間に変更が宙に浮く事故を防ぐため。
- **言語**: ユーザーとの対話言語に合わせる。リポジトリの慣習（コミットメッセージや PR の言語）には依存しない。
