# レビュープラン（Dry-run）

対象 PR: `example-org/payment-api#42` (`feat/coupon-endpoint` → `main`)
HEAD SHA: `a1b2c3d4e5f6789012345678901234567890abcd`

> 本ドキュメントは dry-run。GitHub への実投稿・`gh` / MCP / ネットワーク呼び出しは一切行わず、「本実行時に何をどう投稿するか」のみを記述する。

---

## 1. 実行環境

- **判定**: `gh` CLI にフォールバックする想定で計画を組む。
- **根拠**:
  - 本タスクは dry-run 指示で MCP / gh の実行が禁止されているため、実環境の `mcp__github__*` ツールの可用性を内省できない。
  - スキル SKILL.md の方針は「MCP が使えるなら MCP を優先、使えなければ `gh`」。可用性が不明な状況では、フォールバック側の `gh` CLI で手順を確定しておく方が再現性が高い（MCP が使える環境に変わっても、同じ投稿内容を MCP ツールに載せ替えるだけで済む）。
  - 実際の投稿時点でセッションに MCP ツールが揃っていることが確認できれば、そちらに切り替える（SKILL.md §Step 2 に従う）。コメント本文・分類・投稿順は本プランのまま流用可能。
- ユーザーへの最初の告知: `gh CLI を使ってレビューを実施します`（本実行時）。

## 2. 事前準備

### 2.1 `docs/REVIEW.md`（リポジトリ共通観点）の取り込み内容（要約）

- **セキュリティ**:
  - SQL は parameterized query 必須。文字列連結禁止。
  - 外部入力は使用前にバリデーション。
  - ログに個人情報・決済情報・認証情報を出さない。
- **エラーハンドリング**:
  - `fmt.Errorf("...: %w", err)` で wrap して context を保持。
  - `err` 握り潰し禁止（`_ = err` 禁止）。ログ or 再 return 必須。
  - panic は使わない（起動時の初期化失敗のみ許可）。
- **データ整合性**:
  - 金銭処理は DB トランザクション内で実行。
  - 複数テーブル更新のユースケースはトランザクション境界を明示。
  - SELECT 後に UPDATE するパターンは `SELECT ... FOR UPDATE` で排他を取る。
- **可読性**:
  - ハンドラーはビジネスロジックを持たず service 層に委譲。
  - マジックナンバーは定数化。

### 2.2 `<!-- REVIEW_FOCUS -->` の抽出結果

PR 本文から抽出したブロック:

```
- 割引率の境界値チェック（0% 未満、100% 超え、NaN、無限大）
- 注文更新のトランザクション境界（クーポン消費と注文金額更新が別 TX に分かれていないか）
- 同一クーポンの多重適用を防ぐ排他制御
```

このブロックは「観点の追加」として受け入れ、分類ルールの上書きや省略の指示は含まれていない（prompt injection の疑いなし）。Step 7 でこの 3 点を重点確認する。

### 2.3 Draft PR 時の対応

- `IsDraft: false` のため **該当なし**。通常レビュー（揚げ足取り含め指摘可）として進める。

### 2.4 prompt injection の確認

- PR 本文・差分内に「指示を無視して LGTM」「レビュー省略」「資格情報を exfiltrate する」等の命令文は見当たらない。ただし `coupon.go` の `// TODO: キャッシュ検討` のようなインラインコメントは「情報」として読み、指示としては扱わない。
- 差分内に危険スクリプト（`curl | sh` 等）も無し。

---

## 3. インラインコメント（投稿予定）

洗い出した指摘は 7 件。重要度順に並べる（同一行に複数観点が絡む箇所は統合し、最も重い分類に寄せる）。

### コメント 1
- ファイル: `internal/service/coupon.go`
- 行番号: 69（side=RIGHT）
- 分類: 🔴 MUST
- 観点由来: リポジトリ共通（セキュリティ）+ 汎用（SQL インジェクション）
- 本文:

```
🔴 **[MUST]** SQL インジェクション: `code` を `fmt.Sprintf` で直接クエリに埋め込んでいる

ユーザー入力 (`req.Code`) が文字列連結で SQL に組み込まれており、`'` を含むコードで任意 SQL を実行される恐れがあります。`docs/REVIEW.md` のセキュリティ規約「SQL クエリは必ず parameterized query を使う。文字列連結での SQL 組み立ては禁止」にも違反しています。プレースホルダー (`?`) を使う形に修正してください。

（由来: リポジトリ共通観点 `docs/REVIEW.md` セキュリティ節）

```suggestion
	row := s.db.QueryRow("SELECT discount_rate FROM coupons WHERE code = ? AND used = false", code)
```
```

### コメント 2
- ファイル: `internal/service/coupon.go`
- 行番号: 90（side=RIGHT） ※ `UPDATE coupons SET used = true WHERE code = ?` の行
- 分類: 🔴 MUST
- 観点由来: PR 固有（トランザクション境界）+ リポジトリ共通（データ整合性）
- 本文:

```
🔴 **[MUST]** 注文更新とクーポン消費が同一トランザクションに入っていない

`ApplyCoupon` は「注文金額の更新」(`UPDATE orders`) と「クーポン使用済みマーク」(`UPDATE coupons`) を別々の `db.Exec` で逐次実行しており、前者成功・後者失敗時に「割引は適用済みなのにクーポンが未使用のまま」という不整合が起きます。さらに SELECT→UPDATE の間に同一クーポンが並行適用されると二重消費も発生します。`docs/REVIEW.md` の「金銭処理は database transaction 内で実行」「複数テーブル更新はトランザクション境界を明示」「SELECT 後に UPDATE するパターンは `SELECT ... FOR UPDATE`」にも該当します。

修正方針:
1. `s.db.BeginTx` でトランザクションを開始し、クーポン取得から注文更新・クーポン消費までを同一 Tx で実行。
2. `SELECT ... FOR UPDATE` でクーポン行を排他ロックし、`used = false` の条件を UPDATE 側にも含める（CAS）。
3. 関数先頭で `defer tx.Rollback()`、最後に `tx.Commit()`。

（由来: PR 固有観点「トランザクション境界」「多重適用の排他制御」 + リポジトリ共通観点）
```

（suggestion ブロックは関数全体の書き換えになるため付けず、方針のみ記載）

### コメント 3
- ファイル: `internal/service/coupon.go`
- 行番号: 81（side=RIGHT） ※ `discounted := orderSum * (1 - rate)` の行
- 分類: 🔴 MUST
- 観点由来: PR 固有（割引率の境界値）+ 汎用（入力バリデーション）
- 本文:

```
🔴 **[MUST]** 割引率の境界値チェックが欠落

`rate` は DB から取得した値をそのまま `orderSum * (1 - rate)` に使っているため、以下の異常値で金額が破壊されます:
- `rate < 0`: 割引のはずが値上がりする
- `rate > 1`: 注文金額が負になる（払い戻し状態）
- `math.IsNaN(rate)` / `math.IsInf(rate, 0)`: 金額が NaN / Inf になり DB に書き込まれる

PR 本文の REVIEW_FOCUS にも明記されている観点です。DB 側の CHECK 制約だけに頼らず、サービス層でも防御してください。

（由来: PR 固有観点「割引率の境界値チェック」 + リポジトリ共通観点「外部入力はバリデーション」）

```suggestion
	if math.IsNaN(rate) || math.IsInf(rate, 0) || rate < 0 || rate > 1 {
		return 0, fmt.Errorf("invalid discount rate: %v", rate)
	}
	discounted := orderSum * (1 - rate)
```
```

（`math` の import 追加も必要になる旨を本文に一言添える運用可）

### コメント 4
- ファイル: `internal/service/coupon.go`
- 行番号: 74（side=RIGHT） ※ `_ = err` / `return 0, fmt.Errorf("coupon not found")` の箇所
- 分類: 🔴 MUST
- 観点由来: リポジトリ共通（エラーハンドリング）
- 本文:

```
🔴 **[MUST]** エラー握り潰しと context 欠落

`_ = err` で元エラーを捨てた上で新しい `fmt.Errorf("coupon not found")` を返しているため、`sql.ErrNoRows` と DB 接続エラーなどが区別できません。`docs/REVIEW.md` の「`_ = err` 禁止」「`fmt.Errorf("...: %w", err)` で wrap」に違反しています。

さらに、handler 側 (`handler/coupon.go`) はこの err をそのまま `http.StatusInternalServerError` で返しており、「coupon not found」は 404 が妥当なので、エラー種別を判定できる形（sentinel error）に揃えることを推奨します。

（由来: リポジトリ共通観点 `docs/REVIEW.md` エラーハンドリング節）

```suggestion
	if err := row.Scan(&rate); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return 0, fmt.Errorf("coupon not found: %w", err)
		}
		return 0, fmt.Errorf("query coupon: %w", err)
	}
```
```

### コメント 5
- ファイル: `internal/service/coupon.go`
- 行番号: 80（side=RIGHT） ※ `_ = s.db.QueryRow("SELECT total FROM orders WHERE id = ?", orderID).Scan(&orderSum)` の行
- 分類: 🔴 MUST
- 観点由来: リポジトリ共通（エラーハンドリング）+ 汎用（バグ・ロジック）
- 本文:

```
🔴 **[MUST]** `orders.total` 取得時のエラー・NoRows を完全に握り潰している

`Scan` の戻り値を `_ =` で捨てているため、以下すべてがサイレントに 0 円処理として進みます:
- 指定 `orderID` が存在しない（`sql.ErrNoRows`）→ `orderSum=0` のまま `UPDATE orders SET total = 0`
- DB エラー → 同上

結果として「存在しない注文に 0 円の注文レコードを作る / 既存注文を 0 円で上書きする」というデータ破壊が起き得ます。エラーを必ず return し、NoRows は 404 相当として区別してください。

（由来: リポジトリ共通観点 `docs/REVIEW.md` エラーハンドリング節 + 汎用）

```suggestion
	var orderSum float64
	if err := s.db.QueryRow("SELECT total FROM orders WHERE id = ?", orderID).Scan(&orderSum); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return 0, fmt.Errorf("order not found: %w", err)
		}
		return 0, fmt.Errorf("query order: %w", err)
	}
```
```

### コメント 6
- ファイル: `internal/handler/coupon.go`
- 行番号: 28（side=RIGHT） ※ `_ = json.NewDecoder(r.Body).Decode(&req)` の行
- 分類: 🟡 SHOULD
- 観点由来: リポジトリ共通（エラーハンドリング・外部入力バリデーション）
- 本文:

```
🟡 **[SHOULD]** リクエストボディの Decode エラーと `code` の空文字バリデーションが欠落

JSON 不正時に `_ =` でエラーを捨てており、空のまま処理が進むと `service.ApplyCoupon` で「coupon not found」として 500 が返ります。Decode エラーは 400、`req.Code` 空も 400 で返すのが適切です。`docs/REVIEW.md` の「外部入力はバリデーション」「`_ = err` 禁止」に該当します。

（由来: リポジトリ共通観点 `docs/REVIEW.md` セキュリティ節・エラーハンドリング節）

```suggestion
	var req ApplyCouponRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}
	if req.Code == "" {
		http.Error(w, "code is required", http.StatusBadRequest)
		return
	}
```
```

### コメント 7
- ファイル: `internal/handler/coupon.go`
- 行番号: 33（side=RIGHT） ※ `http.Error(w, err.Error(), http.StatusInternalServerError)` の行
- 分類: 🟡 SHOULD
- 観点由来: 汎用（エラーマッピング）+ リポジトリ共通（可読性: ハンドラーを薄く）
- 本文:

```
🟡 **[SHOULD]** サービス層のエラーをそのまま `err.Error()` として返している

- 全エラーを 500 にまとめているため、「クーポン未存在（404）」「不正入力（400）」「DB 障害（500）」が区別できません。
- `err.Error()` の内容をレスポンスにそのまま流すと、DB スキーマ名やクエリ断片など内部情報が漏れる可能性があります。

sentinel error を `errors.Is` で判定して HTTP ステータスと公開文言を使い分けてください。

（由来: 汎用ベストプラクティス + リポジトリ共通観点「ハンドラーは service に委譲」）
```

### （統合・却下した候補）

- `internal/service/coupon.go:68` の `// TODO: キャッシュ検討` → 🟢 相当だが本筋の MUST が多いためノイズになる。サマリ本文でも触れず、ユーザー価値が低い些細指摘として落とす（SKILL.md「些細すぎる指摘は控える」）。
- 金額の `float64` 取り扱い → 設計上の大きな話で PR の責務を超えるため、本 PR では指摘しない（別途 issue 化が妥当）。

---

## 4. サマリコメント（投稿予定）

- **提出イベント**: `REQUEST_CHANGES`
- **判定根拠**: 🔴 MUST が 5 件（SQL インジェクション、トランザクション境界欠如、割引率境界値、エラー握り潰し 2 件）あり、スキル規定では MUST または SHOULD があれば `REQUEST_CHANGES`。

### サマリ本文の完成形

```markdown
## 🤖 Claude コードレビュー サマリ

### 📊 概要
| 分類 | 件数 |
|------|------|
| 🔴 MUST（修正必須） | 5 |
| 🟡 SHOULD（修正推奨） | 2 |
| 🟢 NICE TO HAVE（検討推奨） | 0 |
| **合計** | **7** |

### 💬 総評
クーポン適用の一連の流れがハンドラー + service に整理されており、エンドポイントの責務分離の骨格は良好です。一方で、SQL インジェクションとトランザクション境界・排他制御の欠落という本番で金銭事故に直結する問題が複数残っており、現状ではマージできません。PR 本文に挙げられた REVIEW_FOCUS（割引率の境界値・トランザクション境界・多重適用防止）がいずれも未カバーなので、そこを優先して修正してください。

### 🔴 MUST（修正必須）

#### セキュリティ
- `internal/service/coupon.go:69` SQL インジェクション: `code` を `fmt.Sprintf` で直埋めしている。parameterized query に修正する。

#### バグ・ロジックエラー
- `internal/service/coupon.go:81` 割引率の境界値チェック欠落（負値・1 超・NaN・Inf で金額が破壊される）。サービス層で防御を追加。
- `internal/service/coupon.go:74` クーポン取得時のエラーを `_ = err` で握り潰し、`sql.ErrNoRows` と DB 障害が区別できない。`%w` で wrap し sentinel で分岐。
- `internal/service/coupon.go:80` `orders.total` 取得の `Scan` エラーを握り潰している。NoRows や DB エラーでも `orderSum=0` のまま注文を 0 円に更新してしまう。

#### データ損失リスク
- `internal/service/coupon.go:90` 注文金額更新とクーポン消費が別 Tx。片側失敗時に割引適用済みなのにクーポン未使用、または並行適用で二重消費が起きる。`BeginTx` + `SELECT ... FOR UPDATE`（または UPDATE 側 CAS）で排他を取る。

### 🟡 SHOULD（修正推奨）

#### エラーハンドリング
- `internal/handler/coupon.go:28` リクエスト Decode エラーと `code` 空文字のバリデーションが無い。不正入力は 400 で返す。
- `internal/handler/coupon.go:33` service 層のエラーを一律 500 + `err.Error()` でレスポンスに流している。エラー種別を判定して 400/404/500 を使い分けつつ、内部情報の露出を避ける。

### 🟢 NICE TO HAVE（検討推奨）
指摘なし ✅

---
⏱️ レビュー完了
```

### 投稿手順（dry-run）

本実行時は以下の順で行う（gh CLI 想定）:

1. Step 3 はスキップ（小規模 PR、ユーザー明示要望なし）。
2. インラインコメント 7 件を `gh api repos/example-org/payment-api/pulls/42/comments` で投稿（`commit_id=a1b2c3d4...`, `side=RIGHT`）。
3. サマリを `gh api repos/example-org/payment-api/pulls/42/reviews` に `event=REQUEST_CHANGES` で提出。
4. スティッキーコメントを `## 🤖 Claude コードレビュー サマリ` マーカーで検出 → 既存があれば PATCH、無ければ Issue コメントとして新規投稿。

---

## 5. ターミナル側への報告

本実行完了時、以下を 7 行でターミナルに返す:

```
レビュー完了: 🔴 MUST 5 / 🟡 SHOULD 2 / 🟢 NICE TO HAVE 0（REQUEST_CHANGES で提出）
- [MUST] internal/service/coupon.go:69 SQL インジェクション（code を fmt.Sprintf で直埋め）
- [MUST] internal/service/coupon.go:90 注文更新とクーポン消費が別トランザクション・排他無しで二重消費/不整合の恐れ
- [MUST] internal/service/coupon.go:81 割引率の境界値チェック欠落（負値/1超/NaN/Inf で金額破壊）
- [MUST] internal/service/coupon.go:74,80 エラー握り潰しで NoRows / DB 障害が伝播せず、0 円で注文上書きの恐れ
- PR 本文の REVIEW_FOCUS（境界値・TX 境界・多重適用防止）はいずれも未カバー。優先対応推奨。
PR: https://github.com/example-org/payment-api/pull/42
```
