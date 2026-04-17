---
name: clean-architecture-check
description: プロジェクトのパッケージ構成がクリーンアーキテクチャに沿っているかを検証するスキル。ディレクトリ構造の分析、レイヤー間の依存関係チェック、違反箇所の特定と改善提案を行う。ユーザーが「クリーンアーキテクチャ」「Clean Architecture」「レイヤー構成」「パッケージ構成チェック」「依存関係の方向」「依存性逆転」「DIP」「ヘキサゴナルアーキテクチャ」「オニオンアーキテクチャ」「ポートアンドアダプター」「アーキテクチャ違反」「レイヤー違反」「import方向」などに言及した場合にこのスキルを使うこと。
---

# クリーンアーキテクチャ パッケージ構成チェックスキル

プロジェクトのディレクトリ構造と import/依存関係を分析し、クリーンアーキテクチャの原則に沿っているかを検証するスキル。違反箇所を特定し、改善提案を行う。

## 前提条件

- チェック対象のプロジェクトがカレントディレクトリまたはユーザーが指定するディレクトリに存在すること
- ソースコードが読み取り可能であること

## クリーンアーキテクチャの基本原則

本スキルは以下の原則に基づいてチェックを行う:

1. **依存性の方向**: 外側のレイヤーから内側のレイヤーへのみ依存する（内側は外側を知らない）
2. **レイヤー構成**: Enterprise Business Rules（Entity） → Application Business Rules（Use Case） → Interface Adapters（Controller/Gateway/Presenter） → Frameworks & Drivers（DB/Web/UI/External）
3. **依存性逆転の原則（DIP）**: 内側のレイヤーがインターフェースを定義し、外側がそれを実装する

```
[Frameworks & Drivers]  →  [Interface Adapters]  →  [Use Cases]  →  [Entities]
      (外側)                                                          (内側)
  依存の方向 ──────────────────────────────────────────────────→
```

## ワークフロー概要

```
[Step 1: 言語・フレームワーク特定]
    → [Step 2: ディレクトリ構造の取得]
    → [Step 3: レイヤーマッピング]
    → [Step 4: 依存関係の解析]
    → [Step 5: 違反の検出]
    → [Step 6: 拡張思考による総合評価]
    → [Step 7: レポート生成]
    → [Step 8: 修正実行の確認（ユーザー判断）]
    → [Step 9: 作業ブランチ作成・コード修正]
    → [Step 10: コミット・プッシュ]
```

---

## Step 1: 言語・フレームワークの特定

プロジェクトの言語とフレームワークを特定する。これにより import 文の解析方法やパッケージの命名慣習を判断する。

```bash
# ビルドファイル・設定ファイルからの推定
ls package.json tsconfig.json go.mod go.sum Cargo.toml pom.xml build.gradle build.gradle.kts settings.gradle.kts build.sbt project/build.properties project/plugins.sbt Gemfile requirements.txt pyproject.toml setup.py composer.json pubspec.yaml 2>/dev/null
```

以下の言語・エコシステムに対応する:

| 言語 | import 解析対象 | パッケージ構造 |
|------|----------------|---------------|
| Go | `import` 文 | ディレクトリ = パッケージ |
| Java/Kotlin | `import` 文 | パッケージ宣言に基づく |
| Scala | `import` 文 | パッケージ宣言に基づく（sbt プロジェクト / Scalatra 等） |
| TypeScript/JavaScript | `import`/`require` 文 | ディレクトリ構造 |
| Python | `import`/`from ... import` 文 | ディレクトリ構造 |
| Rust | `use`/`mod` 文 | モジュール構造 |
| Dart/Flutter | `import` 文 | ディレクトリ構造 |
| Ruby | `require`/`require_relative` 文 | ディレクトリ構造 |
| PHP | `use`/`namespace` 文 | namespace/ディレクトリ構造 |

## Step 2: ディレクトリ構造の取得

プロジェクトのディレクトリ構造を取得して全体像を把握する。

```bash
# ソースコードのディレクトリ構造を取得（言語に応じて除外パターンを調整）
find . -type d \
  -not -path '*/node_modules/*' \
  -not -path '*/.git/*' \
  -not -path '*/vendor/*' \
  -not -path '*/build/*' \
  -not -path '*/dist/*' \
  -not -path '*/.gradle/*' \
  -not -path '*/target/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/.venv/*' \
  -not -path '*/venv/*' \
  | sort
```

```bash
# ソースファイルの一覧も取得（レイヤー分類の手がかり）
find . -type f \( -name "*.go" -o -name "*.java" -o -name "*.kt" -o -name "*.scala" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" -o -name "*.rs" -o -name "*.dart" -o -name "*.rb" -o -name "*.php" \) \
  -not -path '*/node_modules/*' \
  -not -path '*/.git/*' \
  -not -path '*/vendor/*' \
  -not -path '*/test*/*' \
  -not -path '*/__pycache__/*' \
  | sort
```

## Step 3: レイヤーマッピング

ディレクトリ構造から各ディレクトリをクリーンアーキテクチャの 4 レイヤー（Entity / Use Case / Interface Adapter / Frameworks & Drivers）にマッピングする。

典型的な命名パターン（レイヤー名・含まれる要素・判断基準）は `references/layer-names.md` にまとめてあるので、対象プロジェクトのディレクトリ名をこの辞書に当てて推定する。辞書に載っていない命名や判断が曖昧な場合は、代表ファイルの内容・import 先・フレームワーク固有のアノテーションを合わせて確認し、なお決めきれない場合はユーザーに確認する。

## Step 4: 依存関係の解析

各レイヤーのファイルから import/依存文を抽出し、レイヤー間の依存関係を分析する。

### 言語別の import 抽出

```bash
# Go
grep -rn '^import' --include="*.go" <target-dir> | grep -v '_test.go'

# Java/Kotlin/Scala
grep -rn '^import ' --include="*.java" --include="*.kt" --include="*.scala" <target-dir>

# TypeScript/JavaScript
grep -rn "import .* from\|require(" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" <target-dir>

# Python
grep -rn "^import \|^from .* import" --include="*.py" <target-dir>

# Rust
grep -rn "^use \|^mod " --include="*.rs" <target-dir>

# Dart
grep -rn "^import " --include="*.dart" <target-dir>

# PHP
grep -rn "^use \|^namespace " --include="*.php" <target-dir>

# Ruby
grep -rn "require \|require_relative " --include="*.rb" <target-dir>
```

### 依存関係マトリクスの構築

抽出した import 文をもとに、レイヤー間の依存関係マトリクスを構築する:

```
              │ Entity │ UseCase │ Adapter │ Infra │
──────────────┼────────┼─────────┼─────────┼───────┤
Entity        │   -    │    ✗    │    ✗    │   ✗   │  ← 何にも依存しない
UseCase       │   ✓    │    -    │    ✗    │   ✗   │  ← Entity のみに依存
Adapter       │   ✓    │    ✓    │    -    │   ✗   │  ← Entity, UseCase に依存
Infra         │   ✓    │    ✓    │    ✓    │   -   │  ← すべてに依存可能
```

✓ = 許可される依存、✗ = 違反

## Step 5: 違反の検出

Step 4 で構築した依存関係マトリクスに基づき、以下の違反パターンを検出する。

### 違反パターン一覧

#### V1: 内側から外側への依存（最重要）

```
Entity → UseCase, Adapter, Infra  （すべて違反）
UseCase → Adapter, Infra           （違反）
Adapter → Infra                     （違反）
```

具体例:
- Entity パッケージが DB ライブラリを import している
- UseCase が HTTP フレームワークのリクエスト型を import している
- UseCase がリポジトリの具象実装を import している

#### V2: レイヤースキップ（注意）

```
Infra → Entity（Adapter, UseCase を経由すべき場合がある）
```

厳密には違反ではないが、設計上の問題を示唆する場合がある。

#### V3: 循環依存

パッケージ A → パッケージ B → パッケージ A のような循環。

#### V4: インターフェース定義の配置違反

- リポジトリインターフェースが Infra 層に定義されている（UseCase 層またはドメイン層に定義すべき）
- ポート（入力/出力）が Adapter 層に定義されている（UseCase 層に定義すべき）

#### V5: レイヤー構造の欠如

- 明確なレイヤー分けがされていない（フラットな構成）
- 一部のレイヤーが存在しない

### 各違反の検出方法

違反ごとに、具体的なファイルパス・行番号・import 文を記録する:

```
[V1] UseCase → Infra 違反
  ファイル: src/usecase/create_user.go:15
  import: "github.com/example/app/infrastructure/postgres"
  説明: UseCase 層が Infrastructure 層の具象実装に直接依存しています
```

## Step 6: 拡張思考による総合評価

検出結果を踏まえ、拡張思考で以下を検討する。

### 6-1: プロジェクトの成熟度評価

- レイヤー構造がどの程度確立されているか
- 違反の数と深刻度から見た全体的な健全性
- クリーンアーキテクチャの意図はあるが実装が追いついていないのか、そもそも別のアーキテクチャパターンを採用しているのか

### 6-2: 違反の深刻度評価

各違反について:
- **Critical（構造的問題）**: レイヤーの依存方向が逆転しており、修正に大幅なリファクタリングが必要
- **Warning（改善推奨）**: 依存方向は概ね正しいが、一部で不適切な結合がある
- **Info（軽微）**: 命名規則の不統一やレイヤー配置の微調整で解消可能

### 6-3: 改善提案の検討

違反ごとに具体的な改善方法を検討する:
- インターフェースの導入による依存性逆転
- パッケージの移動・再配置
- DTO の導入によるレイヤー間のデータ変換
- DI コンテナの活用

### 6-4: 段階的な改善計画

一度にすべてを修正するのではなく、段階的に改善するロードマップを検討する:
- Phase 1: Critical 違反の修正
- Phase 2: Warning レベルの改善
- Phase 3: 命名・構造の統一

## Step 7: レポート生成

以下の構成でレポートを出力する。

### 出力構成

```
# クリーンアーキテクチャ適合性チェックレポート

## 1. プロジェクト概要
- 言語/フレームワーク: <検出結果>
- ソースファイル数: <数>
- 検出レイヤー数: <数>

## 2. レイヤーマッピング結果

| レイヤー | ディレクトリ | ファイル数 |
|----------|------------|-----------|
| Entity   | domain/    | XX        |
| UseCase  | usecase/   | XX        |
| Adapter  | adapter/   | XX        |
| Infra    | infra/     | XX        |

## 3. 依存関係マトリクス

（Step 4 のマトリクス表示）

## 4. 検出された違反

### Critical（XX 件）
| # | 種別 | ファイル | 行 | 内容 |
|---|------|---------|-----|------|
| 1 | V1   | path    | XX  | ...  |

### Warning（XX 件）
（同様の表形式）

### Info（XX 件）
（同様の表形式）

## 5. 適合スコア

**XX / 100 点**

- レイヤー構造の明確さ: XX / 25
- 依存方向の正しさ: XX / 35
- インターフェース分離: XX / 20
- 命名・配置の一貫性: XX / 20

## 6. 改善提案

### 優先度: 高
（Critical 違反への具体的な改善手順）

### 優先度: 中
（Warning への改善手順）

### 優先度: 低
（Info への改善手順）

## 7. 推奨ディレクトリ構成

（プロジェクトの言語に合わせた理想的なディレクトリ構成を提案）

## 8. 段階的改善ロードマップ

- Phase 1: ...
- Phase 2: ...
- Phase 3: ...
```

ユーザーの要望に応じて Markdown ファイルとして出力する。

---

## 修正フェーズ

### Step 8: 修正実行の確認

レポートを提示した後、**必ずユーザーに修正を実行するかどうかを確認する**。確認なしに修正を開始してはならない。

以下の形式でユーザーに確認を求める:

```
上記のレポートに基づいて、違反箇所の修正を実行しますか？

対応オプション:
1. すべての違反を修正する
2. Critical のみ修正する
3. Critical + Warning を修正する
4. 特定の違反のみ修正する（番号を指定）
5. 修正は行わない（レポートのみ）

どのオプションで進めますか？
```

ユーザーが「5. 修正は行わない」を選択した場合はここで終了する。それ以外の場合は Step 9 に進む。

### Step 9: 作業ブランチの作成とコード修正

ユーザーが修正を承認したら、**作業ブランチを作成してから修正を行う**。現在のブランチで直接修正してはならない。

#### 9-1: 最新の状態を取得

```bash
git fetch origin
```

#### 9-2: 作業ブランチを作成

```bash
# ブランチ名は修正内容がわかる命名にする
git checkout -b refactor/clean-architecture-<date>
```

`<date>` は `YYYYMMDD` 形式（例: `refactor/clean-architecture-20260319`）。

#### 9-3: 修正の実行

レポートの違反内容と改善提案に基づき、以下の種類の修正を実施する。修正は影響範囲が小さいものから順に行い、各修正後にビルドが通ることを確認する。

**ディレクトリ・ファイルの移動（レイヤー配置の修正）:**

違反 V5（レイヤー構造の欠如）や配置が不適切なファイルに対して:

```bash
# 必要なディレクトリの作成
mkdir -p src/domain/model src/domain/repository src/application/usecase src/adapter/controller src/infrastructure/persistence

# ファイルの移動（例: Infra 層に置かれていたリポジトリインターフェースを Domain 層へ）
git mv src/infrastructure/UserRepository.scala src/domain/repository/UserRepository.scala
```

ファイル移動後は、そのファイルを参照しているすべての import 文を更新する:

```bash
# 移動したファイルの旧パッケージ名で import している箇所を検索
grep -rn "import.*infrastructure.*UserRepository" --include="*.scala" --include="*.java" --include="*.kt" --include="*.go" --include="*.ts" --include="*.py" .
```

検索結果に基づき、各ファイルの import 文を新しいパッケージパスに書き換える。

**import 文の修正（依存方向の修正）:**

違反 V1（内側から外側への依存）を解消する手順と言語別コード例は `references/refactoring-workflow.md` の「依存方向の修正例」を参照する。

**循環依存の解消（V3）:**

1. 循環しているパッケージ間の依存を洗い出す
2. 共通のインターフェースや DTO を抽出して中間レイヤーに配置する
3. 依存の方向が一方向になるように import を整理する

**インターフェース配置の修正（V4）:**

外側のレイヤーに定義されているインターフェースを内側のレイヤーに移動する。

#### 9-4: ビルド・テストの確認

修正後、プロジェクトのビルドとテストを実行して回帰がないことを確認する。言語別コマンドは `references/refactoring-workflow.md` の「ビルド・テスト確認コマンド」を参照する。

ビルドエラーやテスト失敗が発生した場合は、原因を調査して修正する。多くの場合、import パスの更新漏れやパッケージ宣言の変更忘れが原因。

### Step 10: コミット・プッシュ

修正が完了しビルド・テストが通ったら、変更をコミットし、リモートへプッシュする。

#### 10-1: 変更内容の確認

```bash
git status
git diff --stat
```

変更内容をユーザーに提示し、意図通りの修正になっているか確認する。

#### 10-2: コミット

変更をステージングしてコミットする。コミットメッセージには修正した違反の概要を記載する。単一コミット・分割コミット双方のテンプレートは `references/refactoring-workflow.md` の「コミットメッセージ例」を参照する。修正範囲が広い場合はレイヤーごと・違反種別ごとにコミットを分けることを検討する。

#### 10-3: プッシュの確認

コミット後、**リモートにプッシュするかどうかをユーザーに確認する**:

```
変更をコミットしました。リモートリポジトリにプッシュしますか？

1. プッシュする
2. プッシュしない（ローカルのみ）

どちらで進めますか？
```

ユーザーが「1. プッシュする」を選択した場合:

```bash
git push -u origin <branch-name>
```

プッシュ完了後、ブランチ名とプッシュ先を報告する。必要に応じて Pull Request の作成も提案する。

ユーザーが「2. プッシュしない」を選択した場合はここで終了する。

---

## 言語別の推奨ディレクトリ構成例

Step 7 のレポート末尾で「推奨ディレクトリ構成」を提示する際、および Step 9 で実際にファイルを配置し直す際は、言語・フレームワーク別の構成例を `references/layouts.md` から参照する。収録しているのは Go / Java・Kotlin (Spring Boot) / Scala (sbt・Scalatra) / TypeScript (Node.js・NestJS) / Python。対象プロジェクトの言語に該当する節のみ読み込む。

既存プロジェクトが別スタイル（例: Rails の MVC、ヘキサゴナル／オニオンの厳格な別名レイヤー）を採用している場合は無理に `references/layouts.md` の構成に合わせず、既存スタイルを尊重した上で「依存方向が正しいか」に議論を集中させる。

---

## 注意事項

- クリーンアーキテクチャは厳密な「正解」があるわけではない。プロジェクトの規模やチームの慣習に応じた柔軟な適用が重要。
- 小規模プロジェクトでは過度なレイヤー分けはオーバーエンジニアリングになりうる。その場合はレポートにその旨を記載する。
- ユーザーがクリーンアーキテクチャではなくヘキサゴナルアーキテクチャやオニオンアーキテクチャを意図している場合は、それぞれの原則に合わせて評価を調整する（基本的な依存方向のルールは共通）。
- フレームワーク固有の制約（例: Spring の `@Component` スキャン、NestJS のモジュール構成）により、純粋なクリーンアーキテクチャから逸脱せざるを得ない場合がある。そのような場合はプラグマティックな判断を記載する。
- Scalatra 特有の配置やScala の `implicit` / `given` を使った DI の注意点は `references/layouts.md` の Scala 節にまとめてあるので、Scala プロジェクトを扱う際は必ず参照する。
