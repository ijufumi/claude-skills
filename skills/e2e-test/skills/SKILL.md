---
name: e2e-test
description: HTTPエンドポイント・API単位のE2E/結合テストを作成・修正するスキル。ルーティング定義から全エンドポイントを洗い出し、実際のHTTPリクエスト・レスポンスサイクルを通じて正常系・異常系を網羅的にテストする。DBアクセスがあるエンドポイントはテスト用DBを使った実DBテスト、それ以外の外部依存はモックを使用する。ユーザーが「E2Eテスト」「e2e test」「エンドツーエンド」「end-to-end」「APIテスト」「エンドポイントテスト」「結合テスト」「integration test」「HTTPテスト」「リクエストテスト」「レスポンステスト」「API結合テスト」「シナリオテスト」「E2E追加」「E2E修正」「コントローラのテスト」などに言及した場合にこのスキルを使うこと。個別の関数・クラス単位のテストを求められた場合は unit-test スキルを優先する。
---

# E2Eテスト作成・修正スキル

APIエンドポイントの特定からテストケース設計、テストコード実装、テスト実行までを一貫して支援するスキル。各エンドポイントに対して正常系・異常系の両方をカバーするE2Eテストを作成する。

## 前提条件

- テスト対象のプロジェクトがカレントディレクトリまたはユーザーが指定するディレクトリに存在すること
- ソースコードが読み取り可能であること
- テストフレームワークがプロジェクトに導入済みであること（未導入の場合はユーザーに確認の上セットアップする）
- アプリケーションがローカルで起動可能であること（または テストクライアント経由でリクエストを送信可能であること）

## テスト方針

本スキルは以下の方針に基づいてE2Eテストを作成する:

1. **全エンドポイントを網羅**: 各エンドポイントに対して少なくとも1つのテストケースを作成する
2. **正常系と異常系の両方を網羅**: 期待通りのレスポンスだけでなく、エラーレスポンスも必ずテストする
3. **データベースアクセスはリアルDB**: DBにアクセスするエンドポイントは、テスト用のデータベースを使って実際にアクセスするテストを書く。通常実行用DBとは別のテスト用DBを用意する
4. **それ以外はモック**: DB以外の外部依存（外部APIコール、メール送信等）はモックを使用する
5. **テストの独立性**: 各テストケースは他のテストに依存せず、単独で実行可能にする
6. **テストデータのクリーンアップ**: DBテストではテスト前後にデータをクリーンアップし、テスト間の副作用を防ぐ
7. **実際のHTTPリクエスト**: 可能な限り実際のHTTPリクエスト/レスポンスサイクルを通じてテストする

## ワークフロー概要

```
[Step 1: プロジェクト構成の把握]
    → [Step 2: エンドポイントの特定]
    → [Step 3: テストケースの設計]
    → [Step 4: ユーザーにテストケース設計を確認]
    → [Step 5: 作業ブランチの作成]
    → [Step 6: テストコードの実装]
    → [Step 7: テストの実行と品質確認]
    → [Step 8: ユーザーにテストコードを確認]
    → [Step 9: 修正・追加対応]
    → [Step 10: リモートプッシュとPR作成]
```

---

## Step 1: プロジェクト構成の把握

プロジェクトの言語、Webフレームワーク、テストフレームワーク、既存のテスト構成を把握する。

### 1-1: 言語・Webフレームワークの特定

```bash
# ビルドファイル・設定ファイルからの推定
ls package.json tsconfig.json go.mod go.sum Cargo.toml pom.xml build.gradle build.gradle.kts settings.gradle.kts build.sbt project/build.properties Gemfile requirements.txt pyproject.toml setup.py composer.json pubspec.yaml Makefile 2>/dev/null
```

Webフレームワークの特定:

| 言語 | Webフレームワーク例 | 確認方法 |
|------|-------------------|----------|
| Go | Echo, Gin, Chi, net/http | `go.mod` の依存、ルーター定義ファイル |
| Java/Kotlin | Spring Boot, Micronaut, Quarkus | `build.gradle` / `pom.xml` の依存 |
| Scala | Scalatra, Play, Akka HTTP, http4s | `build.sbt` の libraryDependencies |
| TypeScript/JavaScript | Express, Fastify, NestJS, Hono, Next.js | `package.json` の dependencies |
| Python | FastAPI, Django, Flask, Starlette | `pyproject.toml` / `requirements.txt` |
| Rust | Actix-web, Axum, Rocket | `Cargo.toml` の dependencies |
| Ruby | Rails, Sinatra, Hanami | `Gemfile` |
| PHP | Laravel, Symfony, Slim | `composer.json` |

### 1-2: テストフレームワーク・HTTPテストクライアントの特定

E2Eテストでは、テストフレームワークに加えてHTTPテストクライアントの確認が重要:

| 言語 | テストフレームワーク | HTTPテストクライアント |
|------|--------------------|-----------------------|
| Go | testing, testify | `net/http/httptest`, Echo の `test.NewRequest` |
| Java/Kotlin | JUnit 5 | `MockMvc`, `WebTestClient`, `RestAssured`, `TestRestTemplate` |
| Scala | ScalaTest | Scalatra の `ScalatraSuite`, `EmbeddedJetty`, sttp client |
| TypeScript/JavaScript | Jest, Vitest, Mocha | `supertest`, `axios` + テストサーバー |
| Python | pytest | `TestClient`（FastAPI/Starlette）, Django の `Client`, `requests` |
| Rust | tokio::test | `actix_web::test`, `axum::test` |
| Ruby | RSpec, Minitest | `rack-test`, Rails の `ActionDispatch::IntegrationTest` |
| PHP | PHPUnit | Laravel の `TestCase`, Symfony の `WebTestCase` |

### 1-3: 既存E2Eテストの確認

```bash
# E2Eテスト・統合テスト関連ファイルの検索
find . -type f \( -name "*e2e*" -o -name "*integration*" -o -name "*api_test*" -o -name "*endpoint*test*" -o -name "*handler*test*" -o -name "*controller*test*" -o -name "*route*test*" \) \
  -not -path '*/node_modules/*' \
  -not -path '*/.git/*' \
  -not -path '*/vendor/*' \
  | head -20
```

既存E2Eテストのスタイル（命名規則、ディレクトリ配置、テストサーバーの起動方法、ヘルパーの使い方等）を確認し、プロジェクトの慣習に合わせる。

### 1-4: テスト用DB構成の確認

データベースを使用するプロジェクトの場合、以下を確認する:

- テスト用DB設定ファイルの有無（`application-test.yml`, `.env.test` 等）
- テスト用DBのセットアップ方法（Docker Compose, テスト用マイグレーション等）
- 既存のテスト用DBヘルパーやフィクスチャの有無

```bash
# テスト用設定ファイルの検索
find . -name "*test*" -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.env" -o -name "*.conf" -o -name "*.properties" \) | grep -v node_modules | grep -v vendor | head -10

# Docker Compose でテスト用DBが定義されているか確認
find . -name "docker-compose*" -type f | head -5
```

テスト用DBが未構成の場合はユーザーに確認し、セットアップ方法を提案する。

### 1-5: API仕様書の確認

API仕様書が存在する場合は参照する:

```bash
# OpenAPI / Swagger 仕様ファイルの検索
find . -type f \( -name "openapi*" -o -name "swagger*" -o -name "api-spec*" \) \( -name "*.yml" -o -name "*.yaml" -o -name "*.json" \) | head -5
```

## Step 2: エンドポイントの特定

プロジェクト内のすべてのAPIエンドポイントを特定する。

### 2-1: ルーティング定義の検索

言語・フレームワーク別のルーティング抽出コマンド（Go/Echo・Gin・Chi、Spring Boot、Scalatra、Express・Fastify・NestJS、FastAPI・Django・Flask、Rails、Laravel）は `references/commands.md` の「ルーティング定義の検索」に収録。対象プロジェクトで使われているフレームワークの節を実行する。

### 2-2: エンドポイント一覧の整理

検出したエンドポイントを以下の形式で一覧化する:

```
| # | HTTPメソッド | パス | ハンドラー/コントローラー | 認証要否 | DB使用 | 既存テスト |
|---|------------|------|------------------------|---------|--------|----------|
| 1 | GET        | /api/users | UserController.List | 要 | 有 | 無 |
| 2 | POST       | /api/users | UserController.Create | 要 | 有 | 無 |
| 3 | GET        | /api/users/:id | UserController.Get | 要 | 有 | 無 |
| 4 | PUT        | /api/users/:id | UserController.Update | 要 | 有 | 無 |
| 5 | DELETE     | /api/users/:id | UserController.Delete | 要 | 有 | 無 |
| 6 | POST       | /api/auth/login | AuthController.Login | 不要 | 有 | 無 |
| 7 | GET        | /health | HealthController.Check | 不要 | 無 | 無 |
```

### 2-3: ハンドラー/コントローラーの分析

各エンドポイントのハンドラーを読み込み、以下を分析する:

- **リクエスト**: HTTPメソッド、パスパラメータ、クエリパラメータ、リクエストボディ、ヘッダー（認証トークン等）
- **レスポンス**: ステータスコード、レスポンスボディの構造、エラーレスポンスの形式
- **バリデーション**: 入力バリデーションのルール
- **依存関係**: DB、外部API、認証/認可
- **ビジネスロジック**: 分岐条件やエラーケース

## Step 3: テストケースの設計

各エンドポイントに対するテストケースを設計する。**各エンドポイントに少なくとも1つのテストケースを設計する。**

### 3-1: テストケース設計の原則

各エンドポイントについて以下の観点でテストケースを洗い出す:

#### 正常系（Happy Path）

- 有効なリクエストに対する期待レスポンス（ステータスコード、ボディ）
- パスパラメータ、クエリパラメータのバリエーション
- ページネーション（一覧系エンドポイント）
- 認証済みユーザーでのアクセス

#### 異常系（Error Path）

- 認証なし / 無効なトークンでのアクセス（401）
- 権限不足でのアクセス（403）
- 存在しないリソースへのアクセス（404）
- 不正なリクエストボディ（400）
  - 必須フィールドの欠落
  - 型の不一致
  - バリデーションエラー（範囲外の値、不正なフォーマット）
- 重複データの登録（409）
- サーバーエラー（500） — 外部依存のモック失敗でシミュレーション

#### CRUDシナリオ

リソースのCRUDを持つエンドポイント群では、一連の操作を通じたシナリオも検討する:
1. リソースを作成（POST）→ 作成されたことを確認（GET）
2. リソースを更新（PUT/PATCH）→ 更新されたことを確認（GET）
3. リソースを削除（DELETE）→ 削除されたことを確認（GET → 404）

### 3-2: テストケース一覧の作成

以下の形式でテストケース一覧を作成する:

```
## テスト対象エンドポイント: POST /api/users

### ハンドラー: UserController.Create

| # | カテゴリ | テストケース名 | リクエスト | 期待ステータス | 期待レスポンス | テスト方法 |
|---|---------|--------------|-----------|--------------|--------------|----------|
| 1 | 正常系  | ユーザーを作成できる | Body: {"name":"John","email":"john@example.com"} | 201 | 作成されたUserが返る | DB |
| 2 | 異常系  | nameが空の場合400エラー | Body: {"name":"","email":"john@example.com"} | 400 | バリデーションエラー | モック |
| 3 | 異常系  | emailが重複する場合409エラー | Body: {"name":"John","email":"existing@example.com"} | 409 | 重複エラー | DB |
| 4 | 異常系  | 認証なしで401エラー | Header: Authorization なし | 401 | 認証エラー | モック |
| 5 | 異常系  | リクエストボディが不正JSON | Body: "invalid json" | 400 | パースエラー | モック |

## テスト対象エンドポイント: GET /api/users/:id

### ハンドラー: UserController.Get

| # | カテゴリ | テストケース名 | リクエスト | 期待ステータス | 期待レスポンス | テスト方法 |
|---|---------|--------------|-----------|--------------|--------------|----------|
| 1 | 正常系  | IDでユーザーを取得できる | Path: id=1 | 200 | Userが返る | DB |
| 2 | 異常系  | 存在しないIDで404エラー | Path: id=99999 | 404 | Not Found | DB |
| 3 | 異常系  | 不正なID形式で400エラー | Path: id=abc | 400 | バリデーションエラー | モック |
```

## Step 4: ユーザーにテストケース設計を確認

**必ずユーザーにテストケース設計を提示し、承認を得てからコード実装に進む。** 確認なしに実装を開始してはならない。

以下の形式でユーザーに確認する:

```
上記のテストケース設計について確認をお願いします。

1. テスト対象エンドポイントに漏れはありませんか？
2. テストケースの追加・削除はありますか？
3. テスト方法（モック/DB）の変更はありますか？
4. その他、修正点はありますか？

問題なければ実装に進みます。
```

ユーザーからのフィードバックがあれば、テストケース設計を修正して再度確認する。

## Step 5: 作業ブランチの作成

テストケース設計が承認されたら、作業ブランチを作成する。

```bash
# 最新の状態を取得
git fetch origin

# 作業ブランチを作成
git checkout -b test/add-e2e-tests-<target>-<date>
```

- `<target>`: テスト対象の概要（例: `user-api`, `auth-endpoints`）
- `<date>`: `YYYYMMDD` 形式（例: `test/add-e2e-tests-user-api-20260321`）

## Step 6: テストコードの実装

### 6-1: テストファイルの配置

プロジェクトの慣習に従ってテストファイルを配置する。E2Eテストは通常、ユニットテストとは別のディレクトリに配置する:

| 言語 | E2Eテストファイル配置例 |
|------|----------------------|
| Go | `e2e/`, `test/e2e/`, または `*_test.go`（ビルドタグで分離） |
| Java/Kotlin | `src/test/java/` 配下に `e2e/` または `integration/` パッケージ |
| Scala | `src/test/scala/` 配下に `e2e/` パッケージ、または `src/it/scala/` |
| TypeScript/JavaScript | `test/e2e/`, `__tests__/e2e/`, または `*.e2e.test.ts` |
| Python | `tests/e2e/`, `tests/integration/` |
| Ruby | `spec/requests/`, `spec/integration/` |
| PHP | `tests/Feature/` |

既存のE2Eテストがある場合は、そのディレクトリ構成に合わせる。

### 6-2: テストサーバー/アプリケーションのセットアップ

E2Eテストでは、テスト用のアプリケーションインスタンスを起動してHTTPリクエストを送信する。言語・フレームワーク別の具体的なコード例（Go/Echo・Gin、Java/Kotlin/Spring Boot、Scala/Scalatra、TypeScript/Express、Python/FastAPI）は `references/test-servers.md` にまとめてあるので、対象プロジェクトの該当セクションのみを参照する。

テストサーバーを組み立てる際の共通ポイント:

- **本番と同じ構成で起動する**: DI コンテナやルーティングは可能な限り本番と同じ経路で組み立てる。外部依存だけ差し替える。
- **DB 接続はテスト用DBに向ける**: 設定ファイル・環境変数の上書きで接続先を切り替える（`spring.datasource.url`、`TEST_DATABASE_URL` など）。
- **各テストでクリーンな状態を保つ**: `@BeforeEach` / `beforeEach` などでテーブルの初期化を行うか、トランザクションロールバックを活用する。

### 6-3: テスト用DB設定

E2Eテストで使用するテスト用DBは通常のDBとは分離する。

#### テスト用DB設定の原則

1. **テスト用DBの分離**: 通常のDBとは異なるデータベース名を使用する（例: `myapp_test`）
2. **テスト前のマイグレーション**: テスト開始前にスキーマのマイグレーションを実行する
3. **テスト間のクリーンアップ**: 各テストの前後にデータをクリーンアップして独立性を保つ
4. **トランザクションロールバック**: 可能であればテストをトランザクション内で実行し、終了後にロールバックする

### 6-4: 認証/認可のテスト対応

認証が必要なエンドポイントのテストでは以下 3 点をワンセットで書く:

1. **テスト用トークン/セッション**: テスト用の認証トークンを発行するヘルパーを作成する（Go のサンプルは `references/test-servers.md` の「認証ヘルパー例」を参照）
2. **認証なしテスト**: 認証ヘッダーを付けずにリクエストし、401 が返ることを確認する
3. **権限不足テスト**: 権限が不十分なユーザーでリクエストし、403 が返ることを確認する

### 6-5: モックを使用するテスト

DB以外の外部依存（外部APIコール、メール送信等）にはモックを使用する。E2Eテストでモックを使う場合は、本番と同じルーティング・DI 構成を保ったまま、DI の差し替えポイントだけをモックに切り替えるのが原則（スタブにしすぎると E2E の価値が薄れる）。Go での具体的なコード例は `references/test-servers.md` の「外部APIモック例」を参照する。

### 6-6: レスポンス検証

E2Eテストではレスポンスを包括的に検証する:

- **ステータスコード**: 正確なHTTPステータスコードを確認
- **レスポンスボディ**: JSON構造とフィールド値を確認
- **レスポンスヘッダー**: Content-Type、CORS ヘッダー等を確認
- **データベース状態**: リクエスト後のDB状態を確認（CUD操作の場合）

## Step 7: テストの実行と品質確認

### 7-1: テストの実行

言語別のテスト実行コマンドは `references/commands.md` の「テスト実行コマンド」を参照する。

### 7-2: テスト結果の確認

- 全テストがパスしていること
- 全エンドポイントに対してテストが存在すること
- テスト実行時間が妥当であること（E2Eテストはユニットテストより遅くなるが過度に遅くないこと）
- DBテストでのデータクリーンアップが正しく行われていること

### 7-3: テスト失敗時の対応

テストが失敗した場合:

1. エラーメッセージとスタックトレースを分析し、原因を特定する
2. テストコードのバグか、テスト対象コードのバグかを判断する
3. テストコードのバグの場合は修正して再実行する
4. テスト対象コードのバグを発見した場合はユーザーに報告し、対応を確認する
5. テスト用DB接続の問題の場合は設定を見直す

## Step 8: ユーザーにテストコードを確認

テストが全てパスしたら、**ユーザーにテストコードの確認を依頼する**。

以下の情報を提示する:

- 作成/修正したテストファイルの一覧
- テスト実行結果のサマリー
- エンドポイント×テストケースの対応表

```
テストコードの実装が完了しました。確認をお願いします。

### 作成したテストファイル
- <ファイルパス1>
- <ファイルパス2>

### テスト実行結果
- 全 XX テスト: XX パス / XX 失敗

### エンドポイントカバレッジ
| エンドポイント | テストケース数 | 正常系 | 異常系 |
|--------------|--------------|--------|--------|
| POST /api/users | 5 | 1 | 4 |
| GET /api/users/:id | 3 | 1 | 2 |
| ... | ... | ... | ... |

### 確認事項
1. テストの内容に問題はありますか？
2. 追加が必要なテストケースはありますか？
3. テストコードのスタイルや命名に修正が必要ですか？

問題なければ、ブランチをリモートにプッシュしてPRを作成します。
```

## Step 9: 修正・追加対応

ユーザーからのフィードバックに基づき:

1. テストケースの追加・修正を行う
2. テストを再実行して全テストがパスすることを確認する
3. 必要に応じて再度ユーザーに確認する

このステップはユーザーが承認するまで繰り返す。

## Step 10: リモートプッシュとPR作成

ユーザーの承認が得られたら、作業ブランチをリモートにプッシュしてPRを作成する。

### 10-1: 変更のコミット

```bash
git add <test-files>
git commit -m "$(cat <<'EOF'
test: <テスト対象>のE2Eテストを追加

- 対象エンドポイント: XX件
- 正常系テスト: XX件
- 異常系テスト: XX件
- DB統合テスト: XX件
- モックテスト: XX件

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

### 10-2: プッシュとPR作成

```bash
# リモートにプッシュ
git push -u origin <branch-name>

# PR作成
gh pr create --title "test: <テスト対象>のE2Eテストを追加" --body "$(cat <<'EOF'
## Summary
- <テスト対象>の全エンドポイントに対するE2Eテストを追加
- 各エンドポイントに正常系・異常系のテストケースを網羅
- DBアクセス部分はテスト用DBを使用した実DBテスト
- 外部API等の依存はモックを使用

## Endpoints covered
| エンドポイント | テスト数 |
|--------------|---------|
| POST /api/users | XX |
| GET /api/users/:id | XX |
| ... | ... |

## Test plan
- [ ] 全テストがCIでパスすること
- [ ] テスト用DB設定が正しいこと
- [ ] 全エンドポイントにテストが存在すること

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

PR作成後、PRのURLをユーザーに報告する。

---

## 注意事項

- プロジェクトの既存テストスタイル（命名規則、ディレクトリ構成、ヘルパーの使い方）に合わせること
- テストフレームワークやHTTPテストクライアントが未導入の場合は、ユーザーに確認の上セットアップする
- テスト用DBが未構成の場合は、Docker Compose やテスト用設定ファイルの作成をユーザーに提案する
- テスト対象コードにバグを発見した場合は、テストコードでバグを記録しつつユーザーに報告する（テスト対象コードの修正は別タスクとする）
- E2Eテストはユニットテストより実行時間が長くなるため、テストの並列実行やDB接続の効率化を考慮する
- 秘密情報（パスワード、APIキー等）をテストコードにハードコードしない。環境変数やテスト用設定ファイルを使用する
- CIパイプラインでのE2Eテスト実行環境（テスト用DBの起動方法等）についてもユーザーに情報を提供する
