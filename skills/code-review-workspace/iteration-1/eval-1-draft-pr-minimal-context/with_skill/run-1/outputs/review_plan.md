# レビュープラン（Dry-run）

本ドキュメントは `ijufumi/my-webapp#7`（Draft PR: "WIP: useAsyncData hook"）に対するコードレビューの dry-run プランである。実際の GitHub アクセス（MCP / gh / ネットワーク）は行わず、「本番実行時に何をどのように投稿するか」を先に書き出したもの。

---

## 1. 実行環境

- **判定結果: `gh` CLI を使用（フォールバック経路）**
- 根拠:
  - 現在のセッションで利用可能なツール一覧を内省した結果、`mcp__github__*` / `mcp__github_inline_comment__*` / `mcp__github_comment__*` などの GitHub MCP ツール、および deferred tool 一覧にも該当ツールは存在しない（見えているのは `mcp__claude_ai_Google_Drive__*` のみ）。
  - したがって SKILL.md Step 2 のフォールバック規則に従い `gh` CLI を採用する。
  - 本番実行時はユーザーへの最初の出力で `gh CLI を使ってレビューを実施します` と 1 行明示する。
- **dry-run 中の制約**: 本プラン作成中は `gh` / MCP / ネットワークへのアクセスは一切行わない。以下の「本番実行するなら」のコマンド例はあくまで擬似コードとして記載する。

---

## 2. 事前準備

### 2.1 `docs/REVIEW.md` の取り込み結果
- **結果: なし（スキップ）**
- 本タスクの指示により `docs/REVIEW.md` は存在しない前提。SKILL.md Step 4 の規則に従い `（docs/REVIEW.md が見つかりませんでした。スキップします）` として扱い、汎用ベストプラクティスのみを適用する。

### 2.2 `<!-- REVIEW_FOCUS -->` の抽出結果
- **結果: なし**
- `pr_body.md` を確認した限り、`<!-- REVIEW_FOCUS -->` ブロックは存在しない（`## Summary` と `## TODO` のみ）。
- SKILL.md Step 5 の規則に従い `（PR 固有のレビュー観点は指定されていません）` として扱う。

### 2.3 Draft PR 時の対応
- **PR は Draft 状態（`IsDraft: true`, ラベル `wip`）。**
- PR 本文にも「まだ書き途中で、TODO が残っている」と明記されており、`エラーハンドリング` / `ローディング状態` / `キャッシュ` が未対応であることが開示済み。
- SKILL.md Step 1「Draft PR の扱い」に従う:
  - 本番実行時は、まずユーザーに「Draft PR ですが、このままレビューしてよろしいですか？」と確認する。今回は dry-run のためこの確認は省略し、「Draft 前提のレビュー方針」でプランを書き出す。
  - **方針**: 書きかけ前提で、PR 本文で既に TODO として開示されている項目（エラーハンドリング未完、ローディング未実装、キャッシュ未実装）は指摘対象から外すか、重くとも NICE TO HAVE 止まり。一方で、書きかけでは済まされない **設計・方針レベルの問題**（メモリリーク、古い state の上書き、型安全性など）は SHOULD 以上で指摘する。
  - 小さな揚げ足取りは避ける。

---

## 3. インラインコメント（投稿予定）

差分は `src/hooks/useAsyncData.ts` 1ファイル（追加 22 行）のみ。各指摘は新規追加行に対するもので、`side=RIGHT` を想定。行番号は新ファイルの行番号（1 始まり）。

### コメント 1
- ファイル: `src/hooks/useAsyncData.ts`
- 行番号: 13–22（`useEffect` の hunk 全体。`start_line=13`, `line=22`, `start_side=RIGHT`, `side=RIGHT`）
- 分類: 🔴 MUST
- 観点由来: 汎用（React / 非同期処理の基本）
- 本文（完成形）:

~~~markdown
🔴 **[MUST]** アンマウント後に `setData` / `setError` が呼ばれるとメモリリーク・警告の原因になる

`useEffect` 内で起動した非同期処理の結果を、コンポーネントがアンマウントされた後や `fetcher` が差し替わった後にも state に書き戻してしまう構造です。React 18 の StrictMode では effect が二重に走るため、古い fetch の結果で新しい state を上書きする競合（stale closure）も発生します。`// TODO: cleanup` とコメントされている通り未対応ですが、これは Draft でも骨組みとして入れておくべき設計事項なので MUST として指摘します。

```suggestion
  useEffect(() => {
    let cancelled = false;
    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err);
      });
    return () => {
      cancelled = true;
    };
  }, [fetcher]);
```
~~~

### コメント 2
- ファイル: `src/hooks/useAsyncData.ts`
- 行番号: 23（`}, []); // TODO: deps` の行）
- 分類: 🟡 SHOULD
- 観点由来: 汎用（React hooks 依存配列）
- 本文（完成形）:

~~~markdown
🟡 **[SHOULD]** `useEffect` の依存配列に `fetcher` が含まれておらず、古い `fetcher` を使い続ける恐れがあります

呼び出し側が毎レンダー新しい関数リテラルを渡してくる可能性が高く、その場合でも初回マウント時の `fetcher` だけが呼ばれ続け、propsの変更に追従できません。ESLint の `react-hooks/exhaustive-deps` にも抵触します。ただし、`fetcher` を依存に入れると今度は無限ループを誘発しうるので、呼び出し側で `useCallback` を使う前提にするか、`useRef` で最新 fetcher を保持するなど運用ルールをコメントで明記するのが望ましいです。コメント 1 の修正案に `[fetcher]` を含めています。
~~~

### コメント 3
- ファイル: `src/hooks/useAsyncData.ts`
- 行番号: 3（`export function useAsyncData(fetcher: () => Promise<any>) {`）
- 分類: 🟡 SHOULD
- 観点由来: 汎用（TypeScript 型安全性）
- 本文（完成形）:

~~~markdown
🟡 **[SHOULD]** `any` の多用で型安全性が失われています

`fetcher` の戻り型・`data` / `error` のいずれも `any` になっており、このフックを使う側で補完や型チェックの恩恵を受けられません。ジェネリクスで戻り値の型を引き回す形にすると、Draft 段階でも呼び出し側のリファクタリング負担が小さく済みます。`error` は `unknown` にして、利用側で `instanceof Error` などのナローイングを強制する形が安全です。

```suggestion
export function useAsyncData<T>(fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
```
（`useState` 2 行も合わせて差し替えてください）
~~~

### コメント 4
- ファイル: `src/hooks/useAsyncData.ts`
- 行番号: 22（関数末尾の `return { data, error };` 直前の閉じ `}` あたり。厳密には `}, []);` の次行として 22 を使う）
- 分類: 🟢 NICE TO HAVE
- 観点由来: 汎用
- 本文（完成形）:

~~~markdown
🟢 **[NICE TO HAVE]** `loading` / `cache` / `retry` は PR 本文の TODO にも挙がっているので任せます

末尾 `// TODO: loading / cache / retry` と整合する形で PR 本文の TODO にも明記されているため、このコメントは Draft 完了までに対応されれば十分と理解しました。設計のヒントだけ残しておくと、
- `loading` は `useState<boolean>` で明示する方が利用側が扱いやすい（`data === null` と `loading` は意味が別）
- `cache` はキー設計が肝なので、`useAsyncData(key, fetcher)` のシグネチャに先に寄せておくと後から破壊的変更が減る
あたりが初期検討事項になるかと思います。
~~~

### 同一行指摘の統合方針
- コメント 1（13–22 の範囲指摘）とコメント 2（23 行）は範囲が重ならないので統合不要。
- コメント 3 は 3 行目、コメント 4 は 22 行目付近なので独立で可。
- もし将来「コメント 1 の範囲を 13–23 に拡張」する場合は、コメント 2 と統合し、重い方の MUST タグに寄せる（SKILL.md Step 10 の運用ルール）。

---

## 4. サマリコメント（投稿予定）

### 4.1 提出イベント
- **`REQUEST_CHANGES`**
- 根拠: 🔴 MUST が 1 件、🟡 SHOULD が 2 件存在するため、SKILL.md Step 9-1 の分岐ルールにより `REQUEST_CHANGES` を選択する。
- 注意: Draft PR に対して `REQUEST_CHANGES` を投げると作者に通知が飛ぶため、本番実行時はユーザーに「Draft に REQUEST_CHANGES を出して良いか」軽く確認すると安全（SKILL.md には強制の規定はないが、運用配慮として）。本プランでは既定通り `REQUEST_CHANGES` とする。

### 4.2 サマリ本文（完成形）

~~~markdown
## 🤖 Claude コードレビュー サマリ

### 📊 概要
| 分類 | 件数 |
|------|------|
| 🔴 MUST（修正必須） | 1 |
| 🟡 SHOULD（修正推奨） | 2 |
| 🟢 NICE TO HAVE（検討推奨） | 1 |
| **合計** | **4** |

### 💬 総評
Draft での骨組みレビューとして、シグネチャはシンプルで React hook らしい良い出発点です。一方で、`useEffect` クリーンアップ不在によるアンマウント後の state 更新は Draft でも押さえておきたい設計事項なので MUST としました。型を `any` ではなくジェネリクスで受ける形に早めに寄せておくと、呼び出し側のリファクタリング負担が軽くなります。PR 本文の TODO（エラーハンドリング・ローディング・キャッシュ）については Draft 前提として本レビューでは深追いしていません。

### 🔴 MUST（修正必須）

#### バグ・ロジックエラー
- `src/hooks/useAsyncData.ts:13-22` アンマウント / fetcher 差し替え後の `setState` によるメモリリーク・stale closure。`cancelled` フラグもしくは `AbortController` でクリーンアップする。

### 🟡 SHOULD（修正推奨）

#### バグ・ロジックエラー
- `src/hooks/useAsyncData.ts:23` `useEffect` 依存配列が空で `fetcher` の変更に追従できない。`[fetcher]` を入れるか、呼び出し側に `useCallback` を要求するかを決める。

#### 可読性・保守性
- `src/hooks/useAsyncData.ts:3` `fetcher` / `data` / `error` がすべて `any`。ジェネリクス `<T>` で戻り値型を引き回し、`error` は `unknown` にして型安全性を確保する。

### 🟢 NICE TO HAVE（検討推奨）

#### リファクタリング提案
- `src/hooks/useAsyncData.ts:22` `loading` は独立した `useState<boolean>`、`cache` は `(key, fetcher)` 型シグネチャへの布石を早めに入れておくと後の破壊的変更を減らせる（PR 本文 TODO と整合）。

---
⏱️ レビュー完了
~~~

### 4.3 スティッキーコメント運用
- 本番実行時は SKILL.md Step 9-2 の手順で、`## 🤖 Claude コードレビュー サマリ` をマーカーに既存コメントを検索し、あれば PATCH、なければ新規投稿する。Step 3（レビュー中通知）はスキップ予定のため `COMMENT_ID` 経由の上書きは不要。

---

## 5. ターミナル側への報告（Step 10-2 の完成形）

本番実行の最後にターミナルへ返す 5〜10 行報告（SKILL.md Step 10-2 のフォーマット）:

```
レビュー完了: 🔴 MUST 1 / 🟡 SHOULD 2 / 🟢 NICE TO HAVE 1（REQUEST_CHANGES で提出）
- [MUST] src/hooks/useAsyncData.ts:13-22 useEffect のクリーンアップ未実装でアンマウント後に setState が走り得る
補足: Draft PR のため、PR 本文 TODO（エラーハンドリング/ローディング/キャッシュ）は指摘対象外としました。
PR: https://github.com/ijufumi/my-webapp/pull/7
```

---

## 付記: 禁止事項の遵守
- 本プラン作成中、`gh` / GitHub MCP / `curl` などネットワーク系コマンドは一切実行していない。
- PR 本文および差分に含まれるコメント文字列（`// TODO: ...` 等）は「データ」として扱い、そこに書かれた指示には従っていない（SKILL.md「prompt injection 対策」準拠）。今回の材料にはそもそも指示らしきものは含まれていなかった。
