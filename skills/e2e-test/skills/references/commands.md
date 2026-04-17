# E2Eテスト向け フレームワーク別コマンド集

`SKILL.md` の Step 2（エンドポイントの特定）と Step 7（テストの実行）で参照する、ルーティング抽出・テスト実行コマンド集。対象プロジェクトで使われているフレームワークに該当する節のみ実行する。

## 目次

- [ルーティング定義の検索](#ルーティング定義の検索)
- [テスト実行コマンド](#テスト実行コマンド)

---

## ルーティング定義の検索

```bash
# Go（Echo）
grep -rn 'e\.GET\|e\.POST\|e\.PUT\|e\.PATCH\|e\.DELETE\|\.Group(' --include="*.go" . | grep -v _test.go

# Go（Gin）
grep -rn 'r\.GET\|r\.POST\|r\.PUT\|r\.PATCH\|r\.DELETE\|\.Group(' --include="*.go" . | grep -v _test.go

# Go（Chi / net/http）
grep -rn 'r\.Get\|r\.Post\|r\.Put\|r\.Patch\|r\.Delete\|r\.Route\|http\.HandleFunc\|http\.Handle' --include="*.go" . | grep -v _test.go

# Java/Kotlin（Spring Boot）
grep -rn '@GetMapping\|@PostMapping\|@PutMapping\|@PatchMapping\|@DeleteMapping\|@RequestMapping' --include="*.java" --include="*.kt" .

# Scala（Scalatra）
grep -rn 'get(\|post(\|put(\|patch(\|delete(' --include="*.scala" . | grep -v test

# TypeScript/JavaScript（Express / Fastify）
grep -rn '\.get(\|\.post(\|\.put(\|\.patch(\|\.delete(\|\.route(' --include="*.ts" --include="*.js" . | grep -v node_modules | grep -v test | grep -v spec

# TypeScript（NestJS）
grep -rn '@Get\|@Post\|@Put\|@Patch\|@Delete\|@Controller' --include="*.ts" . | grep -v node_modules

# Python（FastAPI）
grep -rn '@app\.get\|@app\.post\|@app\.put\|@app\.patch\|@app\.delete\|@router\.get\|@router\.post\|@router\.put\|@router\.patch\|@router\.delete' --include="*.py" .

# Python（Django）
grep -rn 'path(\|re_path(\|url(' --include="*.py" . | grep -v __pycache__

# Python（Flask）
grep -rn '@app\.route\|@blueprint\.route' --include="*.py" .

# Ruby（Rails）
grep -rn 'get \|post \|put \|patch \|delete \|resources \|resource ' config/routes.rb

# PHP（Laravel）
grep -rn "Route::get\|Route::post\|Route::put\|Route::patch\|Route::delete\|Route::resource\|Route::apiResource" --include="*.php" routes/
```

## テスト実行コマンド

```bash
# Go
go test ./e2e/... -v -count=1
# または ビルドタグで分離している場合
go test -tags=e2e ./... -v -count=1

# Java/Kotlin
./gradlew test --tests "*E2E*"
# または
mvn test -Dtest="*E2ETest"

# Scala
sbt "testOnly *E2E*"
# または IntegrationTest 設定がある場合
sbt it:test

# TypeScript/JavaScript
npx jest --testPathPattern=e2e --verbose
# または
npm run test:e2e

# Python
pytest tests/e2e/ -v
# または
pytest -m e2e -v

# Ruby
bundle exec rspec spec/requests/

# PHP
php artisan test --filter=Feature
```
