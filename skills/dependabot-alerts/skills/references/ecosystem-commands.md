# エコシステム別 修正コマンドリファレンス

`SKILL.md` の Step 6（修正方針検討）と Step 9（修正実行）で参照する、エコシステム別の更新・検証コマンド集。アラートのパッケージの `ecosystem` フィールドに応じて該当セクションを参照する。

## 目次

- [npm / yarn / pnpm](#npm--yarn--pnpm)
- [pip / poetry](#pip--poetry)
- [bundler](#bundler)
- [go modules](#go-modules)
- [cargo](#cargo)
- [composer](#composer)
- [maven / gradle](#maven--gradle)
- [整合性チェック・テスト実行](#整合性チェックテスト実行)

---

## npm / yarn / pnpm

```bash
# 特定バージョンへ更新
npm install <package>@<patched-version>
# 脆弱性自動修正（Breaking あり）
npm audit fix
npm audit fix --force

# yarn の場合
yarn upgrade <package>@<patched-version>

# pnpm の場合
pnpm update <package>@<patched-version>
```

## pip / poetry

```bash
# pip
pip install --upgrade <package>==<patched-version>
# requirements.txt の更新も忘れずに
pip freeze > requirements.txt
# もしくは requirements.txt を直接書き換える
sed -i '' 's/<package>==<old-version>/<package>==<new-version>/' requirements.txt

# poetry
poetry add "<package>@^<patched-version>"
poetry update <package>
```

## bundler

```bash
bundle update <package>
# Gemfile.lock の差分を確認
git diff Gemfile.lock
```

## go modules

```bash
go get <package>@<patched-version>
go mod tidy
go mod verify
```

## cargo

```bash
cargo update -p <package>
cargo update -p <package> --precise <patched-version>
```

## composer

```bash
composer require <package>:<patched-version>
composer update <package>
```

## maven / gradle

```bash
# Maven: pom.xml の <version> を書き換えた後
mvn versions:display-dependency-updates
mvn dependency:tree

# Gradle: build.gradle / build.gradle.kts の version を書き換えた後
./gradlew dependencies
./gradlew dependencyUpdates
```

## 整合性チェック・テスト実行

修正後は依存関係の整合性を確認し、テストを走らせて回帰がないことを確認する。

```bash
# 依存整合性
npm ls 2>&1 | grep "ERESOLVE\|ERR!" | head -10
pip check 2>&1 | head -10
bundle check
go mod verify
cargo check

# ピア依存の衝突確認
npm ls --all 2>&1 | grep "ERESOLVE\|peer dep\|invalid" | head -20
pipdeptree --warn silence 2>/dev/null | grep -i <package> || pip check 2>&1 | head -20

# テスト実行（存在する場合）
npm test
pytest
bundle exec rspec
go test ./...
cargo test
```
