# Review Plan: PR #7 `WIP: useAsyncData hook`

- Repository: `ijufumi/my-webapp`
- PR: #7 (https://github.com/ijufumi/my-webapp/pull/7)
- Author: ijufumi (OWNER)
- Base/Head: `main` <- `feat/async-data-hook`
- State: open, **Draft**, label: `wip`
- Changed files: 1 (+22 / -0)
- Target file: `src/hooks/useAsyncData.ts` (new)

## 0. Overall stance

本 PR は Draft かつ `wip` ラベル付きで、著者自身が未完了事項（エラーハンドリング / ローディング / キャッシュ）を TODO として PR body に明示している。
したがって、レビューの目的は「マージ可否の判定」ではなく、**著者が本実装へ進む前に認識合わせしておきたい設計上のリスクを軽く指摘する**ことに留める。
軽微なスタイル指摘や TODO 済みの欠落（ローディング・キャッシュ）を重ねて指摘するのは Draft PR には過剰なので避ける。
代わりに、著者の TODO には挙がっていないが本実装で忘れやすい論点（cleanup / fetcher の参照安定性 / `any` / race condition）を nit ではなく設計メモとして残す方針。

## 1. Inline comments

対象ファイルは 1 ファイルのみ: `src/hooks/useAsyncData.ts`

### 1-1. 13 行目付近（`useEffect` 内 / `// TODO: cleanup`）— severity: major（設計指摘）

> Draft 前提なので実装の要求ではなく、本実装前に方針を合わせたい論点として 1 件コメントする。

コメント案:
```
Draft 前提のメモです。cleanup の TODO がありますが、`fetcher` が解決する前にコンポーネントがアンマウントされた場合、`setData` / `setError` が unmounted component 上で呼ばれて race condition になります。
AbortController で中断する or `cancelled` フラグで setState をガードする、のどちらで実装するか本実装の前に決めておけると後戻りが減ると思います。
また、連続して fetcher が変わったとき（下のコメントで触れる deps の話と関連）、古いリクエストの結果が新しい結果を上書きする可能性もあるので、同じ仕組みでカバーされる想定か確認したいです。
```

### 1-2. 23 行目（`}, []); // TODO: deps`）— severity: major（設計指摘）

コメント案:
```
deps を空配列にしていますが、`fetcher` をそのまま依存に入れると呼び出し側が毎レンダーで新しい関数を渡してきたときに無限ループになりがちです。
本実装時には、
- 呼び出し側に `useCallback` 必須を強いる（ドキュメント化する）
- もしくは `key`（string など）を別引数で受けて deps に使う
のどちらの API にするか決めておくと、利用者側の事故を防げます。`useSWR` / `@tanstack/react-query` の `queryKey` パターンが参考になります。
```

### 1-3. 9 行目（関数シグネチャの `Promise<any>` と 10–11 行目の `useState<any>`）— severity: minor

コメント案:
```
nit / Draft なので必須ではありません。本実装では `useAsyncData<T>(fetcher: () => Promise<T>)` のようにジェネリクス化して、`data: T | null` / `error: unknown` にしておくと呼び出し側で型が効くので便利です。error も `any` より `unknown` のほうが安全です。
```

> ローディング状態 / キャッシュ / リトライ / 28 行目のコメントは PR body の TODO に明記済みなので **重ねては指摘しない**。

## 2. PR summary comment

投稿する要約コメント案:

```
Draft 拝見しました。本実装を始める前に、以下 2 点だけ方針合わせをさせてください（いずれも PR body の TODO には明示されていなかった論点です）。

1. unmount / fetcher 変更時の race condition 対策（AbortController or cancelled フラグ）
2. `fetcher` を deps に入れるかどうかの API 設計（`useCallback` を利用者に強いるか、`key` を別で受けるか）

`data` / `error` の `any` はジェネリクス化で解消できるので、本実装のタイミングで合わせてご検討ください。

PR body の TODO（loading / エラーハンドリング / cache）については、Draft 段階での重複指摘は控えます。本実装に上がってきた段階で改めて見ます。LGTM for draft direction.
```

## 3. Posting strategy (dry-run なので実際には送らない)

- Inline コメント 3 件（1-1, 1-2 は major、1-3 は minor）を `src/hooks/useAsyncData.ts` に付与。
- PR 全体に summary コメント 1 件。
- Draft PR かつ著者本人が TODO を宣言しているため、**Request changes はしない**。コメントのみ（`--comment`）で投稿する想定。
- 以上 dry-run のため投稿操作は行わない。

## 4. ユーザー（ターミナル）への最終報告（案）

```
PR #7 (ijufumi/my-webapp, Draft, wip) のレビュー計画を作成しました。

前提:
- Draft + wip ラベル、PR body に TODO (エラーハンドリング/ローディング/キャッシュ) が明示されている
- 変更は src/hooks/useAsyncData.ts の 1 ファイル、+22/-0

レビュー方針:
- TODO で著者が認識している欠落は重複指摘しない
- 著者が明示していない設計リスクだけを major 2 件 + minor 1 件に絞る

インラインコメント予定 (src/hooks/useAsyncData.ts):
  1. L13 付近 useEffect: unmount / fetcher 変更時の race condition (major)
  2. L23 deps: fetcher を deps に入れる API 設計の方針確認 (major)
  3. L9-11 any: ジェネリクス化と error: unknown への変更提案 (minor)

PR サマリコメント:
  上記 2 点の設計方針合わせを依頼 + any のジェネリクス化提案 + TODO 項目は重複指摘しない旨を明記。
  Draft 方向性は LGTM。Request changes はしない (コメントのみ)。

dry-run のため、実際の投稿は行っていません。
計画ファイル: .../without_skill/outputs/review_plan.md
```
