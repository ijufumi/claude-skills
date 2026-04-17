# リファクタリング実行の参考資料

`SKILL.md` の Step 9（コード修正）と Step 10（コミット）で参照する、言語別コマンドと具体例。対象プロジェクトの言語・フレームワークに該当する箇所のみ読み込む。

## 目次

- [依存方向の修正例（Scala）](#依存方向の修正例scala)
- [ビルド・テスト確認コマンド](#ビルドテスト確認コマンド)
- [コミットメッセージ例](#コミットメッセージ例)

---

## 依存方向の修正例（Scala）

違反 V1（内側から外側への依存）を解消する典型的な流れ。他言語でも「trait → interface / ABC / protocol」に読み替えれば同じ構造で適用できる。

```scala
// 修正前: UseCase が Infrastructure に直接依存（V1 違反）
// src/application/usecase/CreateUserUseCase.scala
import com.example.infrastructure.persistence.SlickUserRepository  // ← 違反

// 修正後: Domain 層の trait に依存
// 1. src/domain/repository/UserRepository.scala に trait を定義
trait UserRepository {
  def save(user: User): Future[User]
  def findById(id: UserId): Future[Option[User]]
}

// 2. UseCase は trait を参照
// src/application/usecase/CreateUserUseCase.scala
import com.example.domain.repository.UserRepository  // ← 修正済み

// 3. Infrastructure 層で trait を実装
// src/infrastructure/persistence/SlickUserRepository.scala
import com.example.domain.repository.UserRepository
class SlickUserRepository extends UserRepository { ... }
```

ポイント:

1. 内側のレイヤーが外側の具象クラスに依存している箇所を特定する
2. 内側のレイヤーにインターフェース（trait / interface / ABC / protocol）を作成する
3. 外側のレイヤーでそのインターフェースを実装する
4. 内側のレイヤーの import を具象クラスからインターフェースに変更する

## ビルド・テスト確認コマンド

修正後、プロジェクトのビルドとテストを実行して回帰がないことを確認する。

```bash
# Scala/sbt の場合
sbt compile 2>&1 | tail -20
sbt test 2>&1 | tail -30

# Go の場合
go build ./...
go test ./...

# Java/Kotlin の場合
./gradlew build 2>&1 | tail -20
# または
mvn compile test 2>&1 | tail -30

# TypeScript の場合
npm run build 2>&1 | tail -20
npm test 2>&1 | tail -30

# Python の場合
python -m py_compile <changed-files>
pytest 2>&1 | tail -30
```

ビルドエラーやテスト失敗が発生した場合は、多くの場合 import パスの更新漏れやパッケージ宣言の変更忘れが原因。

## コミットメッセージ例

修正内容が多い場合は、レイヤーごとや違反種別ごとにコミットを分割することを検討する。

### 単一コミットの例

```bash
git commit -m "$(cat <<'EOF'
refactor: クリーンアーキテクチャに沿ったパッケージ構成に修正

- レイヤー間の依存方向を修正（内側→外側の依存を解消）
- リポジトリインターフェースを Domain 層に移動
- インフラ層の具象実装への直接依存をインターフェース経由に変更
- [修正した具体的な違反内容を記載]

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

### 分割コミットの例

```bash
# ディレクトリ構造の修正
git add <moved-files>
git commit -m "$(cat <<'EOF'
refactor: レイヤー構造に沿ったディレクトリ配置に変更

- Entity 層: domain/ 配下にモデルとリポジトリインターフェースを集約
- UseCase 層: application/ 配下にユースケースを集約
- Adapter 層: adapter/ 配下にコントローラーとゲートウェイを集約
- Infra 層: infrastructure/ 配下にフレームワーク依存を集約

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"

# import 修正
git add <import-fixed-files>
git commit -m "$(cat <<'EOF'
refactor: import 文を修正しレイヤー間の依存方向を正規化

- UseCase 層から Infrastructure 層への直接依存を解消
- Domain 層の trait 経由での依存に変更
- 循環依存を解消

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```
