# ユニットテスト 言語別パターン集

`SKILL.md` の Step 6（テストコードの実装）で参照する、言語・フレームワーク別のモック／DBテスト実装例。

## 目次

- [Go](#go)
- [Java / Kotlin](#java--kotlin)
- [TypeScript / JavaScript](#typescript--javascript)
- [Python](#python)

---

## Go

### モック（インターフェース + testify/mock）

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

### DB テスト（トランザクションロールバック）

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
    tx, _ := db.Begin()
    t.Cleanup(func() { tx.Rollback() })

    repo := NewUserRepository(tx)
    user := &User{Name: "John", Email: "john@example.com"}

    err := repo.Save(user)

    assert.NoError(t, err)
    assert.NotZero(t, user.ID)
}
```

---

## Java / Kotlin

### モック（Mockito / MockK）

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

### DB テスト（Spring Boot + テスト用 PostgreSQL）

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

---

## TypeScript / JavaScript

### モック（Jest）

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

### DB テスト（Prisma / TypeORM + テスト用DB）

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

---

## Python

### モック（pytest + unittest.mock）

```python
from unittest.mock import Mock, ANY

class TestUserService:
    def test_sends_welcome_email(self):
        email_sender = Mock()
        email_sender.send.return_value = True
        service = UserService(email_sender=email_sender)

        service.create_user("John", "john@example.com")

        email_sender.send.assert_called_once_with("john@example.com", ANY, ANY)
```

### DB テスト（SQLAlchemy + テスト用DB）

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
