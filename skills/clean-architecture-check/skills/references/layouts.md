# クリーンアーキテクチャ 言語別ディレクトリ構成例

`SKILL.md` の Step 7（レポート生成）および Step 9（コード修正）で参照する、言語・フレームワーク別の推奨ディレクトリ構成。プロジェクトの既存構成が大きく異なる場合は無理に合わせず、既存慣習を尊重した上で依存方向が正しくなるように調整する。

## 目次

- [Go](#go)
- [Java / Kotlin（Spring Boot）](#java--kotlinspring-boot)
- [Scala（sbt / Scalatra）](#scalasbt--scalatra)
- [TypeScript（Node.js / NestJS）](#typescriptnodejs--nestjs)
- [Python](#python)

---

## Go

```
project/
├── cmd/                    # Frameworks & Drivers（エントリポイント）
│   └── server/
│       └── main.go
├── internal/
│   ├── domain/             # Entity
│   │   ├── model/
│   │   ├── repository/     # リポジトリインターフェース
│   │   └── service/        # ドメインサービス
│   ├── usecase/            # Use Case
│   ├── adapter/            # Interface Adapters
│   │   ├── controller/
│   │   ├── presenter/
│   │   └── gateway/        # リポジトリ実装
│   └── infrastructure/     # Frameworks & Drivers
│       ├── database/
│       ├── router/
│       └── config/
├── go.mod
└── go.sum
```

## Java / Kotlin（Spring Boot）

```
src/main/java/com/example/app/
├── domain/                 # Entity
│   ├── model/
│   ├── repository/         # リポジトリインターフェース
│   └── service/            # ドメインサービス
├── application/            # Use Case
│   ├── usecase/
│   ├── dto/
│   └── port/               # 入力/出力ポート
├── adapter/                # Interface Adapters
│   ├── controller/
│   ├── presenter/
│   └── gateway/
└── infrastructure/         # Frameworks & Drivers
    ├── persistence/
    ├── configuration/
    └── external/
```

## Scala（sbt / Scalatra）

```
src/main/scala/com/example/app/
├── domain/                 # Entity
│   ├── model/              # case class によるドメインモデル
│   ├── repository/         # リポジトリ trait（インターフェース）
│   ├── service/            # ドメインサービス
│   └── value/              # 値オブジェクト
├── application/            # Use Case
│   ├── usecase/            # ユースケース実装
│   ├── dto/                # 入出力 DTO（case class）
│   └── port/               # 入力/出力ポート（trait）
├── adapter/                # Interface Adapters
│   ├── controller/         # Scalatra サーブレット（ScalatraServlet 継承）
│   ├── presenter/          # レスポンス整形
│   └── gateway/            # リポジトリ trait の具象実装
└── infrastructure/         # Frameworks & Drivers
    ├── persistence/        # Slick / ScalikeJDBC 等の DB アクセス実装
    ├── config/             # 設定（application.conf / typesafe config）
    ├── servlet/            # ScalatraBootstrap / web.xml 設定
    ├── json/               # json4s / circe 等の JSON シリアライズ設定
    └── external/           # 外部 API クライアント
```

Scala / Scalatra 固有のポイント:

- **trait を活用した DIP**: Scala の `trait` はインターフェースとして自然に使える。リポジトリや外部サービスの抽象を `domain` / `application` 層に trait として定義し、`infrastructure` 層で実装する。
- **case class の配置**: ドメインモデルの `case class` は `domain/model`、DTO 用の `case class` は `application/dto` に配置する。Scalatra のリクエスト/レスポンス用 case class は `adapter/controller` に配置する。
- **ScalatraBootstrap**: `ScalatraBootstrap`（`init` でサーブレットをマウントする）は `infrastructure/servlet` に配置する。ここで DI コンテナからユースケースを取得してコントローラーに注入する。
- **JSON シリアライズ**: json4s の `DefaultFormats` や circe の Encoder/Decoder はフレームワーク依存のため `infrastructure/json` に配置する。コントローラーはこれを利用するが、ドメイン層やユースケース層には持ち込まない。
- **Slick / ScalikeJDBC**: DB アクセスライブラリの Table 定義やクエリは `infrastructure/persistence` に閉じ込め、ドメイン層の `repository` trait を実装する形にする。
- **implicit / given の配置**: Scala の暗黙パラメータによる DI 自体は問題ないが、`implicit` の定義場所がレイヤー違反を引き起こしていないか確認する（例: Infra 層の implicit を UseCase 層で直接 import していたら違反）。

## TypeScript（Node.js / NestJS）

```
src/
├── domain/                 # Entity
│   ├── entity/
│   ├── value-object/
│   ├── repository/         # リポジトリインターフェース
│   └── service/
├── application/            # Use Case
│   ├── use-case/
│   ├── dto/
│   └── port/
├── adapter/                # Interface Adapters
│   ├── controller/
│   ├── presenter/
│   └── gateway/
└── infrastructure/         # Frameworks & Drivers
    ├── database/
    ├── config/
    └── external/
```

## Python

```
src/
├── domain/                 # Entity
│   ├── model/
│   ├── repository/         # リポジトリインターフェース（ABC）
│   └── service/
├── application/            # Use Case
│   ├── usecase/
│   ├── dto/
│   └── port/
├── adapter/                # Interface Adapters
│   ├── controller/
│   ├── presenter/
│   └── gateway/
└── infrastructure/         # Frameworks & Drivers
    ├── database/
    ├── config/
    └── external/
```
