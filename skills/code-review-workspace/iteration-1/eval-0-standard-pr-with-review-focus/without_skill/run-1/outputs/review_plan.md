# Review Plan: PR #42 `Add coupon application endpoint`

- Repository: `example-org/payment-api`
- PR: https://github.com/example-org/payment-api/pull/42
- Head SHA: `a1b2c3d4e5f6789012345678901234567890abcd`
- Base: `main` ← Head: `feat/coupon-endpoint`
- Author: `alice-dev` (MEMBER)
- Changed files: 2 / +117 / -0
- モード: **dry-run**（GitHub には投稿しない）

---

## 1. 観点の整理

PR 本文の `<!-- REVIEW_FOCUS -->` で指定された観点:

1. 割引率の境界値チェック（0% 未満、100% 超え、NaN、無限大）
2. 注文更新のトランザクション境界（クーポン消費と注文金額更新が別 TX に分かれていないか）
3. 同一クーポンの多重適用を防ぐ排他制御

リポジトリガイド (`docs/REVIEW.md`) から追加で適用する観点:

- SQL は必ず parameterized query（文字列連結禁止）
- 外部入力はバリデーションする
- エラーを握り潰さない（`_ = err` 禁止）、`%w` で wrap
- 金銭系は transaction 必須、`SELECT ... FOR UPDATE` で排他
- ハンドラは薄く、ビジネスロジックは service へ

---

## 2. インラインコメント計画

投稿モード（dry-run 時）: すべて `side=RIGHT`、対象 SHA = `a1b2c3d4e5f6789012345678901234567890abcd`。

### 2-1. `internal/service/coupon.go` L19（最重要：SQL インジェクション）

```go
query := fmt.Sprintf("SELECT discount_rate FROM coupons WHERE code = '%s' AND used = false", code)
row := s.db.QueryRow(query)
```

**severity: blocker / category: security**

> **SQL インジェクション脆弱性です。** `code` は HTTP リクエストボディ由来の外部入力で、`fmt.Sprintf` による文字列連結で SQL を組み立てているため、`' OR '1'='1` のような入力で任意の行を取得・更新できてしまいます。`docs/REVIEW.md` のセキュリティ規約「SQL クエリは必ず parameterized query を使う」にも違反しています。
>
> 以下のように placeholder (`?`) を使ってください:
>
> ```go
> row := s.db.QueryRow(
>     "SELECT discount_rate FROM coupons WHERE code = ? AND used = false",
>     code,
> )
> ```
>
> この修正は他のコメントに先行して必須です。

---

### 2-2. `internal/service/coupon.go` L14〜L36 全体（トランザクション欠落・排他制御欠落）

コメント対象行: `func (s *CouponService) ApplyCoupon(...)` 冒頭 (L14) を起点にレンジコメント (L14–L36)。

**severity: blocker / category: data-integrity, concurrency**

> **トランザクション境界がなく、同一クーポンの多重適用が防げません。** レビュー観点 2 および 3、`docs/REVIEW.md`「金銭に関わる処理は必ず database transaction」「SELECT 後に UPDATE するパターンは `SELECT ... FOR UPDATE` で排他を取る」に該当します。
>
> 現状の処理は以下 4 本のクエリが**別々のコネクション・別々の暗黙 TX** で走ります:
> 1. `SELECT discount_rate FROM coupons WHERE code = ? AND used = false`
> 2. `SELECT total FROM orders WHERE id = ?`
> 3. `UPDATE orders SET total = ? WHERE id = ?`
> 4. `UPDATE coupons SET used = true WHERE code = ?`
>
> 問題:
> - (3) 成功後に (4) が失敗すると、**注文は割引され、クーポンは未使用のまま**残る。
> - 並行リクエストが (1) をほぼ同時に通過すると、両方 `used = false` を見るため、**同一クーポンが 2 回適用**される。`UPDATE coupons SET used = true` に `WHERE used = false` 条件もなく、かつ `RowsAffected` も見ていない。
> - `orders.total` も SELECT → UPDATE の間に他トランザクションが total を変更すると lost update が起きる。
>
> 修正案（最小）:
>
> ```go
> tx, err := s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
> if err != nil {
>     return 0, fmt.Errorf("begin tx: %w", err)
> }
> defer tx.Rollback()
>
> var rate float64
> if err := tx.QueryRowContext(ctx,
>     "SELECT discount_rate FROM coupons WHERE code = ? AND used = false FOR UPDATE",
>     code,
> ).Scan(&rate); err != nil {
>     if errors.Is(err, sql.ErrNoRows) {
>         return 0, ErrCouponNotFound
>     }
>     return 0, fmt.Errorf("select coupon: %w", err)
> }
>
> var orderSum float64
> if err := tx.QueryRowContext(ctx,
>     "SELECT total FROM orders WHERE id = ? FOR UPDATE",
>     orderID,
> ).Scan(&orderSum); err != nil { ... }
>
> discounted := orderSum * (1 - rate)
>
> if _, err := tx.ExecContext(ctx,
>     "UPDATE orders SET total = ? WHERE id = ?", discounted, orderID,
> ); err != nil { ... }
>
> res, err := tx.ExecContext(ctx,
>     "UPDATE coupons SET used = true WHERE code = ? AND used = false", code,
> )
> if err != nil { ... }
> if n, _ := res.RowsAffected(); n != 1 {
>     return 0, ErrCouponAlreadyUsed
> }
>
> if err := tx.Commit(); err != nil {
>     return 0, fmt.Errorf("commit: %w", err)
> }
> ```
>
> ポイント:
> - 単一 TX にまとめる
> - `SELECT ... FOR UPDATE` で coupons 行と orders 行の両方をロック
> - `UPDATE coupons ... WHERE used = false` + `RowsAffected == 1` で多重適用を検出
> - ctx を渡してキャンセル伝播を有効化

---

### 2-3. `internal/service/coupon.go` L18（割引率の境界値）

```go
var rate float64
if err := row.Scan(&rate); err != nil {
    _ = err
    return 0, fmt.Errorf("coupon not found")
}

// 割引率を適用
var orderSum float64
_ = s.db.QueryRow("SELECT total FROM orders WHERE id = ?", orderID).Scan(&orderSum)
discounted := orderSum * (1 - rate)
```

**severity: major / category: correctness (review-focus #1)**

> **割引率の境界値チェックが一切ありません。** レビュー観点 1 に該当します。
>
> `rate` は DB 値とはいえ、マイグレーション事故やオペミスで不正値が入る可能性があります:
>
> - `rate < 0` → 値引きどころか**増額**される
> - `rate > 1` → `discounted` が負になり、後工程（返金処理等）で不整合
> - `math.IsNaN(rate)` → `orderSum * (1 - NaN) = NaN` が `UPDATE orders SET total = NaN` で書き込まれる
> - `math.IsInf(rate, 0)` → 同上
>
> Scan 直後に以下を入れてください:
>
> ```go
> if math.IsNaN(rate) || math.IsInf(rate, 0) || rate < 0 || rate > 1 {
>     return 0, fmt.Errorf("invalid discount_rate %v for code=%s", rate, code)
> }
> ```
>
> 併せて、`coupons.discount_rate` 列に DB 制約 (`CHECK (discount_rate BETWEEN 0 AND 1)`) を入れておくとより安全です（本 PR 範囲外でも Issue 化推奨）。
>
> なお、金額を `float64` で扱うこと自体もリスクです（丸め誤差）。将来的には integer minor unit (例: 銭) か `decimal` 型への移行を検討してください（こちらは本 PR ではスコープ外で OK、FYI）。

---

### 2-4. `internal/service/coupon.go` L19–L21（エラー握り潰し + wrap 欠落）

```go
if err := row.Scan(&rate); err != nil {
    _ = err
    return 0, fmt.Errorf("coupon not found")
}
```

**severity: major / category: error-handling**

> `docs/REVIEW.md`「`_ = err` は禁止。ログ or 再 return が必須」「`fmt.Errorf("...: %w", err)` で wrap」に違反しています。
>
> - `_ = err` は明示的な握り潰しで、ガイドで禁止
> - `fmt.Errorf("coupon not found")` は元エラーを消しており、DB 障害（接続断など）と「クーポン未発見」を区別できません。運用時の原因切り分け不可
>
> 修正:
>
> ```go
> if err := row.Scan(&rate); err != nil {
>     if errors.Is(err, sql.ErrNoRows) {
>         return 0, ErrCouponNotFound  // sentinel を定義
>     }
>     return 0, fmt.Errorf("scan coupon: %w", err)
> }
> ```

---

### 2-5. `internal/service/coupon.go` L25（エラー完全無視）

```go
_ = s.db.QueryRow("SELECT total FROM orders WHERE id = ?", orderID).Scan(&orderSum)
```

**severity: blocker / category: error-handling, correctness**

> **エラーを完全に捨てているため、注文が存在しない／DB エラー時にも `orderSum = 0` のまま処理が続行します。** 結果として `discounted = 0` で `orders.total = 0` を実行し、存在しない注文に対して副作用（なお該当行がないのでロウは更新されないが、後続の coupons.used = true は実行される）を起こしえます。
>
> 必ずエラーを受け、`sql.ErrNoRows` は 404、それ以外は 500 相当の扱いに:
>
> ```go
> if err := tx.QueryRowContext(ctx,
>     "SELECT total FROM orders WHERE id = ? FOR UPDATE", orderID,
> ).Scan(&orderSum); err != nil {
>     if errors.Is(err, sql.ErrNoRows) {
>         return 0, ErrOrderNotFound
>     }
>     return 0, fmt.Errorf("scan order: %w", err)
> }
> ```

---

### 2-6. `internal/handler/coupon.go` L22–L24（リクエストの decode エラー無視 + バリデーション欠落）

```go
var req ApplyCouponRequest
_ = json.NewDecoder(r.Body).Decode(&req)
```

**severity: major / category: input-validation, error-handling**

> decode エラーを無視しているため、壊れた JSON やボディ欠落でも `req.Code = ""` のまま service に渡り、「coupon not found」500 が返ります。`docs/REVIEW.md`「外部入力は使う前にバリデーションする」「エラー握り潰し禁止」に該当。
>
> ```go
> if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
>     http.Error(w, "invalid request body", http.StatusBadRequest)
>     return
> }
> if req.Code == "" {
>     http.Error(w, "code is required", http.StatusBadRequest)
>     return
> }
> // orderID の空チェックも同様に
> ```

---

### 2-7. `internal/handler/coupon.go` L27–L30（エラーを一律 500 + 生メッセージ露出）

```go
discounted, err := svc.ApplyCoupon(orderID, req.Code)
if err != nil {
    http.Error(w, err.Error(), http.StatusInternalServerError)
    return
}
```

**severity: major / category: api-design, security**

> 2 つの問題:
>
> 1. **全エラーが 500**: 「coupon not found」「order not found」「coupon already used」など**ユーザー起因の 4xx**も 500 になります。service 側の sentinel エラー（`ErrCouponNotFound` 等）で分岐してください。
> 2. **`err.Error()` をそのままレスポンスに返している**: ラップ後の内部情報（SQL エラー文言、スタック的ヒント）が外部に漏れます。クライアントには固定メッセージを返し、詳細はサーバログへ。
>
> ```go
> switch {
> case errors.Is(err, service.ErrCouponNotFound):
>     http.Error(w, "coupon not found", http.StatusNotFound)
> case errors.Is(err, service.ErrCouponAlreadyUsed):
>     http.Error(w, "coupon already used", http.StatusConflict)
> case errors.Is(err, service.ErrOrderNotFound):
>     http.Error(w, "order not found", http.StatusNotFound)
> default:
>     log.Printf("apply coupon: %v", err)  // PII を含めない
>     http.Error(w, "internal error", http.StatusInternalServerError)
> }
> ```

---

### 2-8. `internal/service/coupon.go` L13（TODO コメント）

```go
// TODO: キャッシュ検討
```

**severity: minor / category: housekeeping**

> 本 PR のスコープ外 TODO は Issue 化して追跡可能にし、コードからは削除推奨です（コード中の TODO は放置されやすい）。blocker ではありません。

---

### 2-9. `internal/handler/coupon.go` L17（金額を float64 で返している）

```go
DiscountedSum float64 `json:"discounted_sum"`
```

**severity: minor / category: design (FYI)**

> 金額の `float64` 表現は丸め誤差の温床です（`0.1 + 0.2` 問題）。本 PR で既存の `orders.total` と揃える選択なら現状維持で構いませんが、型を統一する別 PR で整理することを推奨します。ブロッカーではありません。

---

### 2-10. `internal/service/coupon.go` L6（`NewCouponService` が毎回 `db.Conn()` を掴む）

```go
func NewCouponService() *CouponService {
    return &CouponService{db: db.Conn()}
}
```

**severity: minor / category: design**

> ハンドラから毎リクエスト `service.NewCouponService()` が呼ばれていますが、`db.Conn()` の実装によっては接続プールの使い方が非効率になります。DI（例えば `NewCouponService(db *sql.DB)`）にして、起動時に作った 1 つの `*sql.DB` を渡す方が望ましいです（`*sql.DB` 自体がプールなのでシングルトンで十分）。本 PR のスコープ外として Issue 化でも可。

---

## 3. インラインコメントのサマリ（投稿予定一覧）

| # | File | Line | Severity | Category | 要点 |
|---|------|------|----------|----------|------|
| 2-1 | internal/service/coupon.go | 19 | **blocker** | security | SQL インジェクション（文字列連結） |
| 2-2 | internal/service/coupon.go | 14–36 | **blocker** | data-integrity, concurrency | TX 欠落 + `SELECT ... FOR UPDATE` 欠落 + 多重適用検出なし |
| 2-3 | internal/service/coupon.go | 18 | major | correctness (focus#1) | 割引率の境界値 (NaN/Inf/<0/>1) チェックなし |
| 2-4 | internal/service/coupon.go | 19–21 | major | error-handling | `_ = err` + `%w` なし |
| 2-5 | internal/service/coupon.go | 25 | **blocker** | error-handling | QueryRow のエラーを完全無視 |
| 2-6 | internal/handler/coupon.go | 22–24 | major | input-validation | decode エラー無視 + Code 未バリデーション |
| 2-7 | internal/handler/coupon.go | 27–30 | major | api-design, security | 全エラー 500 + 生メッセージ露出 |
| 2-8 | internal/service/coupon.go | 13 | minor | housekeeping | TODO コメント |
| 2-9 | internal/handler/coupon.go | 17 | minor | design (FYI) | 金額 float64 |
| 2-10 | internal/service/coupon.go | 6 | minor | design | DB を DI に |

blocker 3 件 / major 4 件 / minor 3 件。**blocker が解消されるまで approve しない。**

---

## 4. PR 全体のサマリコメント（完成形・投稿予定）

````markdown
## Review Summary — changes requested

PR 本文で指定された 3 観点について、**3 件すべてで対応が不足**しています。加えて SQL インジェクションとエラー握り潰しが重なっており、現状ではマージできません。

### Blockers（マージ前に必須）

1. **SQL インジェクション** `internal/service/coupon.go` の `SELECT discount_rate ...` が `fmt.Sprintf` による文字列連結。外部入力 `code` がそのまま SQL に埋め込まれています。placeholder (`?`) に置き換えてください。
2. **トランザクション境界なし + 多重適用防止なし**（観点 2・3）。`orders` 更新と `coupons.used` 更新が別 TX、かつ `SELECT ... FOR UPDATE` も `WHERE used = false` ガードも `RowsAffected` チェックもないため、並行リクエストで同一クーポンが複数回適用されえます。単一 TX にまとめ、`FOR UPDATE` でロックし、`UPDATE coupons ... WHERE used = false` + `RowsAffected == 1` で多重適用を検出してください。
3. **注文取得のエラー無視** `_ = s.db.QueryRow("SELECT total FROM orders ...").Scan(&orderSum)`。注文が存在しない／DB 障害でも処理が継続し、誤った金額更新と coupon 消費が起きえます。

### Major

4. **割引率の境界値チェックなし**（観点 1）。`rate < 0`, `rate > 1`, `NaN`, `Inf` いずれも防げていません。Scan 後に検証を追加、かつ DB 制約の追加も検討してください。
5. **エラー握り潰し・wrap 欠落** `_ = err`、`fmt.Errorf("coupon not found")` による元エラー破棄。`docs/REVIEW.md` の規約どおり `%w` で wrap し、`sql.ErrNoRows` を sentinel で区別してください。
6. **リクエスト decode のエラー無視 + 入力バリデーション不足** 壊れた JSON や空 `code` が到達しえます。400 を返す分岐を追加してください。
7. **全エラー 500 + 生エラーメッセージ露出** ユーザー起因のエラーも 500 扱い、かつ `err.Error()` をそのまま返しており情報漏洩の懸念。sentinel エラーでステータス分岐し、クライアントには定型文を返す構成に。

### Minor / FYI

8. `// TODO: キャッシュ検討` は Issue 化して削除。
9. 金額を `float64` で扱うことの丸め誤差リスク（別 PR で型整理を推奨）。
10. `NewCouponService` が `db.Conn()` を内部で掴んでいる設計は DI に寄せると単体テストが書きやすくなります。

### テスト

- PR 記載が「手動で正常系のみ確認」のみ。最低限、以下のユニット／結合テストを追加してください:
  - 正常系（割引適用、orders.total 更新、coupons.used 更新、レスポンス）
  - 異常系: 存在しない coupon / 既に used / 存在しない order / 割引率 (<0, >1, NaN, Inf) / DB エラー
  - 並行適用: 同一コードで 2 リクエスト同時 → 片方のみ成功、もう片方は 409

### 観点カバレッジ

| 観点 | 状態 |
|---|---|
| 1. 割引率の境界値チェック | NG（未実装） |
| 2. TX 境界 | NG（別 TX に分散） |
| 3. 多重適用の排他 | NG（`FOR UPDATE` なし、`RowsAffected` 未確認） |

Blocker を解消し、観点 3 件をカバーするテストが揃った段階で再レビューします。
````

---

## 5. ユーザー（ターミナル）への最終報告（完成形）

```
PR #42 (example-org/payment-api) "Add coupon application endpoint" のレビュー計画を作成しました。
dry-run のため GitHub への投稿は行っていません。

総評: changes requested
  blocker: 3 / major: 4 / minor: 3

blocker:
  1. internal/service/coupon.go:19  SQL インジェクション (fmt.Sprintf による SQL 組み立て)
  2. internal/service/coupon.go:14-36  トランザクション境界なし + SELECT FOR UPDATE なし
                                         → 同一クーポンの多重適用を防げない (PR 観点 2, 3)
  3. internal/service/coupon.go:25  QueryRow エラーを _ で握り潰し (orders の不在を検知不能)

major (抜粋):
  - 割引率の境界値 (NaN/Inf/<0/>1) チェックなし (PR 観点 1)
  - _ = err / fmt.Errorf("...") の wrap なし (docs/REVIEW.md 違反)
  - リクエスト decode エラー無視 + Code 未バリデーション
  - 全エラー一律 500 + err.Error() 露出

PR 本文の REVIEW_FOCUS 3 観点はすべて未対応の状態です。
上記 blocker の解消とユニット／並行テスト追加後に再レビュー推奨。

出力: skills/code-review-workspace/iteration-1/eval-0-standard-pr-with-review-focus/without_skill/outputs/review_plan.md
```
