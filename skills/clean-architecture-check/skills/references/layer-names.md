# レイヤー名パターン集

`SKILL.md` の Step 3（レイヤーマッピング）で参照する、典型的なディレクトリ・パッケージ命名からクリーンアーキテクチャのレイヤーを推定するための辞書。対象プロジェクトの命名が一意に決まらない場合は、そのディレクトリ配下のファイル内容・import 先から判断する。

## Entities（Enterprise Business Rules）

最も内側のレイヤー。ビジネスルールを表現するドメインオブジェクト。

よくある命名:
- `entity`, `entities`
- `domain`, `domain/model`, `domain/entity`
- `model`, `models`
- `core`, `core/entity`
- `enterprise`

含まれるもの:
- ドメインモデル / エンティティ
- 値オブジェクト（Value Object）
- ドメインサービス
- ドメインイベント
- ドメインの例外

## Use Cases（Application Business Rules）

アプリケーション固有のビジネスルール。

よくある命名:
- `usecase`, `usecases`, `use_case`, `use_cases`
- `application`, `app`
- `service`, `services`（ドメインサービスと混同注意）
- `interactor`, `interactors`
- `core/usecase`

含まれるもの:
- ユースケースクラス / インタラクター
- 入力ポート（Input Port）/ 入力 DTO
- 出力ポート（Output Port）/ 出力 DTO
- リポジトリインターフェース（ポート）

## Interface Adapters

外部とユースケース層をつなぐアダプター。

よくある命名:
- `adapter`, `adapters`
- `interface`, `interfaces`
- `controller`, `controllers`
- `gateway`, `gateways`
- `presenter`, `presenters`
- `handler`, `handlers`
- `api`
- `web`
- `grpc`
- `graphql`

含まれるもの:
- コントローラー
- プレゼンター
- ゲートウェイの実装
- リポジトリの実装
- DTO 変換

## Frameworks & Drivers

最も外側のレイヤー。フレームワークやツールの詳細。

よくある命名:
- `infrastructure`, `infra`
- `framework`, `frameworks`
- `driver`, `drivers`
- `external`
- `db`, `database`, `persistence`
- `config`, `configuration`
- `di`（DI コンテナ）
- `cmd`（Go のエントリポイント）
- `main`
- `server`
- `migration`, `migrations`

含まれるもの:
- DB 接続・マイグレーション
- Web フレームワーク設定
- DI コンテナ設定
- 外部 API クライアント
- メール送信等の外部サービス

## マッピングが曖昧な場合の判断基準

ディレクトリ名だけでは判断できない場合、以下も確認する:

1. **ファイル内容のサンプリング**: 代表的なファイルを読み、何をしているか確認する
2. **import 先**: そのパッケージが何に依存しているかで位置づけを推定する（例: DB ライブラリを直接 import していれば Frameworks & Drivers 寄り）
3. **フレームワーク固有の構成**: Spring Boot の `@Entity` / `@Service` / `@Controller` アノテーション、Scalatra の `ScalatraServlet` / `ScalatraFilter` 継承、NestJS の `@Controller` / `@Injectable` などからレイヤーを推定
