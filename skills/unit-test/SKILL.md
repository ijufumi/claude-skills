---
name: unit-test
description: ユニットテストの作成・修正を支援するスキル。テスト対象コードの特定、テストケース設計（正常系・異常系）、テストコード実装、テスト実行までを一貫して行う。データベースアクセスがある場合はテスト用DBを使った統合テストを作成し、それ以外はモックを使用する。ユーザーが「ユニットテスト」「unit test」「テスト作成」「テストコード」「テストケース」「テスト追加」「テスト修正」「テストを書いて」「テストカバレッジ」「正常系テスト」「異常系テスト」「モックテスト」「テスト設計」「TDD」「テスト駆動」などに言及した場合にこのスキルを使うこと。
---

# ユニットテスト作成・修正スキル

テスト対象コードの分析からテストケース設計、テストコード実装、テスト実行までを一貫して支援するスキル。

## 前提条件

- テスト対象のプロジェクトがカレントディレクトリまたはユーザーが指定するディレクトリに存在すること
- ソースコードが読み取り可能であること
- テストフレームワークがプロジェクトに導入済みであること（未導入の場合はユーザーに確認の上セットアップする）

## テスト方針

本スキルは以下の方針に基づいてテストを作成する:

1. **正常系と異常系の両方を網羅**: 期待通りの動作だけでなく、エラーケースや境界値も必ずテストする
2. **データベースアクセスはリアルDB**: DBにアクセスするコードは、テスト用のデータベースを使って実際にアクセスするテストを書く。通常実行用DBとは別のテスト用DBを用意する
3. **それ以外はモック**: DB以外の外部依存（API呼び出し、ファイルI/O等）はモックを使用する
4. **テストの独立性**: 各テストケースは他のテストに依存せず、単独で実行可能にする
5. **テストデータのクリーンアップ**: DBテストではテスト前後にデータをクリーンアップし、テスト間の副作用を防ぐ

## ワークフロー概要

```
[Step 1: プロジェクト構成の把握]
    → [Step 2: テスト対象コードの特定]
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

プロジェクトの言語、フレームワーク、テストフレームワーク、既存のテスト構成を把握する。

### 1-1: 言語・フレームワークの特定

```bash
# ビルドファイル・設定ファイルからの推定
ls package.json tsconfig.json go.mod go.sum Cargo.toml pom.xml build.gradle build.gradle.kts settings.gradle.kts build.sbt project/build.properties Gemfile requirements.txt pyproject.toml setup.py composer.json pubspec.yaml Makefile 2>/dev/null
```

### 1-2: テストフレームワークの特定

| 言語 | テストフレームワーク例 | 確認方法 |
|------|----------------------|----------|
| Go | testing（標準）, testify | `go.mod` で testify 等の依存を確認 |
| Java/Kotlin | JUnit 5, Mockito, MockK | `build.gradle` / `pom.xml` の testImplementation |
| Scala | ScalaTest, Specs2, MUnit | `build.sbt` の libraryDependencies |
| TypeScript/JavaScript | Jest, Vitest, Mocha | `package.json` の devDependencies / scripts |
| Python | pytest, unittest | `pyproject.toml` / `requirements.txt` / `setup.cfg` |
| Rust | cargo test（標準）| `Cargo.toml` |
| Ruby | RSpec, Minitest | `Gemfile` |
| PHP | PHPUnit | `composer.json` |

### 1-3: 既存テストの確認

```bash
# テストファイルの一覧を取得
# Go
find . -name "*_test.go" -not -path '*/vendor/*' | head -20

# Java/Kotlin/Scala
find . -path "*/test/*" -type f \( -name "*.java" -o -name "*.kt" -o -name "*.scala" \) | head -20

# TypeScript/JavaScript
find . -name "*.test.*" -o -name "*.spec.*" | grep -v node_modules | head -20

# Python
find . -name "test_*.py" -o -name "*_test.py" | grep -v __pycache__ | head -20
```

既存テストのスタイル（命名規則、ディレクトリ配置、ヘルパーの使い方等）を確認し、プロジェクトの慣習に合わせる。

### 1-4: テスト用DB構成の確認

データベースを使用するプロジェクトの場合、以下を確認する:

- テスト用DB設定ファイルの有無（`application-test.yml`, `.env.test`, `database_test.go` 等）
- テスト用DBのセットアップ方法（Docker Compose, テスト用マイグレーション等）
- 既存のテスト用DBヘルパーやフィクスチャの有無

```bash
# テスト用設定ファイルの検索
find . -name "*test*" -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.env" -o -name "*.conf" -o -name "*.properties" \) | grep -v node_modules | grep -v vendor | head -10

# Docker Compose でテスト用DBが定義されているか確認
find . -name "docker-compose*" -type f | head -5
```

テスト用DBが未構成の場合はユーザーに確認し、セットアップ方法を提案する。

## Step 2: テスト対象コードの特定

ユーザーが指定したコードまたは自動的に検出した対象を分析する。

### 2-1: 対象の特定

ユーザーが明示的に指定しない場合、以下の基準で対象を提案する:

- テストが存在しないソースファイル
- 最近変更されたファイル（`git diff` / `git log` ベース）
- ビジネスロジック層（UseCase / Service / Domain）のコード

```bash
# テストが無いファイルの検出例（Go）
for f in $(find . -name "*.go" -not -name "*_test.go" -not -path '*/vendor/*'); do
  test_file="${f%.go}_test.go"
  if [ ! -f "$test_file" ]; then
    echo "テスト無し: $f"
  fi
done
```

### 2-2: 対象コードの分析

テスト対象のコードを読み込み、以下を分析する:

- **公開関数/メソッドの一覧**: テスト対象となる公開インターフェース
- **依存関係**: 外部依存（DB、API、ファイルシステム等）
- **分岐条件**: if/switch/match 等の分岐パターン
- **エラーハンドリング**: エラーが返される条件
- **入出力の型**: 引数と戻り値の型情報

分析結果に基づき、各依存を以下に分類する:

| 依存の種類 | テスト方法 |
|-----------|-----------|
| データベースアクセス | テスト用DBに実際にアクセス |
| 外部APIコール | モック |
| ファイルI/O | モックまたはテスト用一時ファイル |
| 時刻取得 | モック（固定時刻を注入） |
| ランダム値生成 | モック（固定値を注入） |
| 他の内部モジュール | 原則モック（対象の単体テストに集中） |

## Step 3: テストケースの設計

分析結果に基づき、各関数/メソッドに対するテストケースを設計する。

### 3-1: テストケース設計の原則

各関数について以下の観点でテストケースを洗い出す:

#### 正常系（Happy Path）

- 典型的な入力に対する期待出力
- 複数の正常パターン（入力のバリエーション）
- 境界値での正常動作

#### 異常系（Error Path）

- 不正な入力（nil/null、空文字、範囲外の値）
- 必須パラメータの欠落
- 外部依存のエラー（DB接続失敗、API タイムアウト等）
- ビジネスルール違反（重複登録、権限不足等）
- 同時実行時の競合

#### 境界値

- 最小値/最大値
- 空コレクション / 1要素 / 多数要素
- 文字列の長さ制限

### 3-2: テストケース一覧の作成

以下の形式でテストケース一覧を作成する:

```
## テスト対象: <ファイルパス>

### 関数: <関数名>

| # | カテゴリ | テストケース名 | 入力 | 期待結果 | モック/DB |
|---|---------|--------------|------|---------|----------|
| 1 | 正常系  | 有効なユーザーを作成できる | name="John", email="john@example.com" | User オブジェクトが返る | DB |
| 2 | 正常系  | 名前が最大長でも作成できる | name="A"*255, email="test@example.com" | 正常に作成される | DB |
| 3 | 異常系  | メールが空の場合エラー | name="John", email="" | ValidationError | モック |
| 4 | 異常系  | 重複メールの場合エラー | name="John", email="existing@example.com" | DuplicateError | DB |
| 5 | 異常系  | DB接続失敗時にエラー | name="John", email="john@example.com" | DBConnectionError | モック |
```

## Step 4: ユーザーにテストケース設計を確認

**必ずユーザーにテストケース設計を提示し、承認を得てからコード実装に進む。** 確認なしに実装を開始してはならない。

以下の形式でユーザーに確認する:

```
上記のテストケース設計について確認をお願いします。

1. テストケースの追加・削除はありますか？
2. テスト方法（モック/DB）の変更はありますか？
3. その他、修正点はありますか？

問題なければ実装に進みます。
```

ユーザーからのフィードバックがあれば、テストケース設計を修正して再度確認する。

## Step 5: 作業ブランチの作成

テストケース設計が承認されたら、作業ブランチを作成する。

```bash
# 最新の状態を取得
git fetch origin

# 作業ブランチを作成
git checkout -b test/add-unit-tests-<target>-<date>
```

- `<target>`: テスト対象の概要（例: `user-service`, `order-usecase`）
- `<date>`: `YYYYMMDD` 形式（例: `test/add-unit-tests-user-service-20260321`）

## Step 6: テストコードの実装

### 6-1: テストファイルの配置

プロジェクトの慣習に従ってテストファイルを配置する:

| 言語 | テストファイル配置 |
|------|------------------|
| Go | 対象ファイルと同じディレクトリに `*_test.go` |
| Java/Kotlin | `src/test/java/` 配下に同パッケージ構造で配置 |
| Scala | `src/test/scala/` 配下に同パッケージ構造で配置 |
| TypeScript/JavaScript | 対象ファイルと同じディレクトリまたは `__tests__/` |
| Python | `tests/` ディレクトリまたは対象と同じディレクトリ |

### 6-2: モックを使用するテストの実装

DB以外の外部依存にはモックを使用する。

#### 言語別モックパターン

**Go（インターフェース + 構造体モック or testify/mock）:**

```go
// モックの定義
type mockEmailSender struct {
    mock.Mock
}

func (m *mockEmailSender) Send(to, subject, body string) error {
    args := m.Called(to, subject, body)
    return args.Error(0)
}

func TestCreateUser_SendsWelcomeEmail(t *testing.T) {
    mockSender := new(mockEmailSender)
    mockSender.On("Send", "john@example.com", mock.Anything, mock.Anything).Return(nil)

    svc := NewUserService(mockSender)
    err := svc.CreateUser("John", "john@example.com")

    assert.NoError(t, err)
    mockSender.AssertExpectations(t)
}
```

**Java/Kotlin（Mockito / MockK）:**

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {
    @Mock
    private EmailSender emailSender;

    @InjectMocks
    private UserService userService;

    @Test
    void shouldSendWelcomeEmail() {
        when(emailSender.send(anyString(), anyString(), anyString()))
            .thenReturn(true);

        userService.createUser("John", "john@example.com");

        verify(emailSender).send(eq("john@example.com"), anyString(), anyString());
    }
}
```

**TypeScript/JavaScript（Jest）:**

```typescript
describe('UserService', () => {
    let emailSender: jest.Mocked<EmailSender>;
    let userService: UserService;

    beforeEach(() => {
        emailSender = { send: jest.fn().mockResolvedValue(true) };
        userService = new UserService(emailSender);
    });

    it('should send welcome email', async () => {
        await userService.createUser('John', 'john@example.com');
        expect(emailSender.send).toHaveBeenCalledWith('john@example.com', expect.any(String), expect.any(String));
    });
});
```

**Python（pytest + unittest.mock）:**

```python
from unittest.mock import Mock, patch

class TestUserService:
    def test_sends_welcome_email(self):
        email_sender = Mock()
        email_sender.send.return_value = True
        service = UserService(email_sender=email_sender)

        service.create_user("John", "john@example.com")

        email_sender.send.assert_called_once_with("john@example.com", ANY, ANY)
```

### 6-3: データベースを使用するテストの実装

DBにアクセスするテストでは、テスト用DBを使用する。通常実行用のDBとは別に用意する。

#### テスト用DB設定の原則

1. **テスト用DBの分離**: 通常のDBとは異なるデータベース名を使用する（例: `myapp_test`）
2. **テスト前のセットアップ**: テーブル作成・マイグレーションを実行する
3. **テスト間のクリーンアップ**: 各テストの前後にデータをクリーンアップして独立性を保つ
4. **トランザクションロールバック**: 可能であればテストをトランザクション内で実行し、終了後にロールバックする

#### 言語別DBテストパターン

**Go:**

```go
func setupTestDB(t *testing.T) *sql.DB {
    t.Helper()
    db, err := sql.Open("postgres", "postgres://localhost:5432/myapp_test?sslmode=disable")
    if err != nil {
        t.Fatalf("failed to connect test DB: %v", err)
    }
    t.Cleanup(func() {
        db.Close()
    })
    return db
}

func TestUserRepository_Save(t *testing.T) {
    db := setupTestDB(t)
    // トランザクション内でテストを実行
    tx, _ := db.Begin()
    t.Cleanup(func() { tx.Rollback() })

    repo := NewUserRepository(tx)
    user := &User{Name: "John", Email: "john@example.com"}

    err := repo.Save(user)

    assert.NoError(t, err)
    assert.NotZero(t, user.ID)
}
```

**Java/Kotlin（Spring Boot + H2 or Testcontainers）:**

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:postgresql://localhost:5432/myapp_test"
})
class UserRepositoryTest {
    @Autowired
    private UserRepository userRepository;

    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
    }

    @Test
    void shouldSaveUser() {
        User user = new User("John", "john@example.com");

        User saved = userRepository.save(user);

        assertThat(saved.getId()).isNotNull();
        assertThat(saved.getName()).isEqualTo("John");
    }
}
```

**TypeScript（Prisma / TypeORM + テスト用DB）:**

```typescript
describe('UserRepository', () => {
    let prisma: PrismaClient;

    beforeAll(async () => {
        prisma = new PrismaClient({
            datasources: { db: { url: process.env.TEST_DATABASE_URL } }
        });
        await prisma.$connect();
    });

    afterAll(async () => {
        await prisma.$disconnect();
    });

    beforeEach(async () => {
        await prisma.user.deleteMany();
    });

    it('should save user', async () => {
        const repo = new UserRepository(prisma);
        const user = await repo.save({ name: 'John', email: 'john@example.com' });

        expect(user.id).toBeDefined();
        expect(user.name).toBe('John');
    });
});
```

**Python（SQLAlchemy + テスト用DB）:**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def test_db():
    engine = create_engine("postgresql://localhost:5432/myapp_test")
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

class TestUserRepository:
    def test_save_user(self, test_db):
        repo = UserRepository(session=test_db)
        user = repo.save(User(name="John", email="john@example.com"))

        assert user.id is not None
        assert user.name == "John"
```

### 6-4: テストヘルパー・フィクスチャの作成

テストの共通処理は、既存のヘルパーがあればそれに従い、無ければ必要に応じて共通化する。ただし過度な抽象化は避ける。

## Step 7: テストの実行と品質確認

### 7-1: テストの実行

```bash
# Go
go test ./... -v -count=1

# Java/Kotlin
./gradlew test
# または
mvn test

# Scala
sbt test

# TypeScript/JavaScript
npm test
# または
npx jest --verbose

# Python
pytest -v

# Rust
cargo test

# Ruby
bundle exec rspec
```

### 7-2: テスト結果の確認

- 全テストがパスしていること
- テスト実行時間が妥当であること
- DBテストでのデータクリーンアップが正しく行われていること

### 7-3: テスト失敗時の対応

テストが失敗した場合:

1. エラーメッセージを分析し、原因を特定する
2. テストコードのバグか、テスト対象コードのバグかを判断する
3. テストコードのバグの場合は修正して再実行する
4. テスト対象コードのバグを発見した場合はユーザーに報告し、対応を確認する

## Step 8: ユーザーにテストコードを確認

テストが全てパスしたら、**ユーザーにテストコードの確認を依頼する**。

以下の情報を提示する:

- 作成/修正したテストファイルの一覧
- テスト実行結果のサマリー
- テストケースの対応表（設計 vs 実装）

```
テストコードの実装が完了しました。確認をお願いします。

### 作成したテストファイル
- <ファイルパス1>
- <ファイルパス2>

### テスト実行結果
- 全 XX テスト: XX パス / XX 失敗

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
test: <テスト対象>のユニットテストを追加

- 正常系テスト: XX件
- 異常系テスト: XX件
- DB統合テスト: XX件
- モックテスト: XX件

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### 10-2: プッシュとPR作成

```bash
# リモートにプッシュ
git push -u origin <branch-name>

# PR作成
gh pr create --title "test: <テスト対象>のユニットテストを追加" --body "$(cat <<'EOF'
## Summary
- <テスト対象>に対するユニットテストを追加
- 正常系・異常系の両方をカバー
- DBアクセス部分はテスト用DBを使用した統合テスト
- 外部依存はモックを使用

## Test plan
- [ ] 全テストがCIでパスすること
- [ ] テスト用DB設定が正しいこと

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

PR作成後、PRのURLをユーザーに報告する。

---

## 注意事項

- プロジェクトの既存テストスタイル（命名規則、ディレクトリ構成、ヘルパーの使い方）に合わせること
- テストフレームワークが未導入の場合は、ユーザーに確認の上セットアップする
- テスト用DBが未構成の場合は、Docker Compose やテスト用設定ファイルの作成をユーザーに提案する
- テスト対象コードにバグを発見した場合は、テストコードでバグを記録しつつユーザーに報告する（テスト対象コードの修正は別タスクとする）
- テストの実行時間が長くなりすぎないよう、DBテストはトランザクションロールバックを活用する
- 秘密情報（パスワード、APIキー等）をテストコードにハードコードしない。環境変数やテスト用設定ファイルを使用する
