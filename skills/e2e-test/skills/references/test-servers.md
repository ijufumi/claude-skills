# E2Eテスト 言語別テストサーバー実装例

`SKILL.md` の Step 6（テストコードの実装）で参照する、言語・フレームワーク別のテストサーバー起動・HTTPリクエスト送信パターン。

## 目次

- [Go（Echo）](#goecho)
- [Go（Gin）](#gogin)
- [Java / Kotlin（Spring Boot + MockMvc）](#java--kotlinspring-boot--mockmvc)
- [Java / Kotlin（Spring Boot + WebTestClient）](#java--kotlinspring-boot--webtestclient)
- [Scala（Scalatra + ScalatraSuite）](#scalascalatra--scalatrasuite)
- [TypeScript / JavaScript（Express + supertest）](#typescript--javascriptexpress--supertest)
- [Python（FastAPI + TestClient）](#pythonfastapi--testclient)
- [認証ヘルパー例（Go）](#認証ヘルパー例go)
- [外部APIモック例（Go）](#外部apiモック例go)

---

## Go（Echo）

```go
func setupTestServer(t *testing.T) *echo.Echo {
    t.Helper()
    e := echo.New()
    db := setupTestDB(t)
    // ルーティングとハンドラーの登録（本番と同じ構成）
    userRepo := repository.NewUserRepository(db)
    userUseCase := usecase.NewUserUseCase(userRepo)
    handler.RegisterUserRoutes(e, userUseCase)
    return e
}

func TestGetUser(t *testing.T) {
    e := setupTestServer(t)

    req := httptest.NewRequest(http.MethodGet, "/api/users/1", nil)
    req.Header.Set("Authorization", "Bearer test-token")
    rec := httptest.NewRecorder()
    e.ServeHTTP(rec, req)

    assert.Equal(t, http.StatusOK, rec.Code)
}
```

## Go（Gin）

```go
func setupTestRouter(t *testing.T) *gin.Engine {
    t.Helper()
    gin.SetMode(gin.TestMode)
    r := gin.New()
    db := setupTestDB(t)
    userRepo := repository.NewUserRepository(db)
    userUseCase := usecase.NewUserUseCase(userRepo)
    handler.RegisterUserRoutes(r, userUseCase)
    return r
}

func TestCreateUser(t *testing.T) {
    r := setupTestRouter(t)

    body := `{"name":"John","email":"john@example.com"}`
    req := httptest.NewRequest(http.MethodPost, "/api/users", strings.NewReader(body))
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Authorization", "Bearer test-token")
    rec := httptest.NewRecorder()
    r.ServeHTTP(rec, req)

    assert.Equal(t, http.StatusCreated, rec.Code)
    var resp map[string]interface{}
    json.Unmarshal(rec.Body.Bytes(), &resp)
    assert.Equal(t, "John", resp["name"])
}
```

## Java / Kotlin（Spring Boot + MockMvc）

```java
@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:postgresql://localhost:5432/myapp_test"
})
class UserControllerE2ETest {
    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private UserRepository userRepository;

    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
    }

    @Test
    void shouldCreateUser() throws Exception {
        mockMvc.perform(post("/api/users")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Authorization", "Bearer test-token")
                .content("{\"name\":\"John\",\"email\":\"john@example.com\"}"))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.name").value("John"))
            .andExpect(jsonPath("$.email").value("john@example.com"));
    }

    @Test
    void shouldReturn400WhenNameIsEmpty() throws Exception {
        mockMvc.perform(post("/api/users")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Authorization", "Bearer test-token")
                .content("{\"name\":\"\",\"email\":\"john@example.com\"}"))
            .andExpect(status().isBadRequest());
    }

    @Test
    void shouldReturn404WhenUserNotFound() throws Exception {
        mockMvc.perform(get("/api/users/99999")
                .header("Authorization", "Bearer test-token"))
            .andExpect(status().isNotFound());
    }
}
```

## Java / Kotlin（Spring Boot + WebTestClient）

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:postgresql://localhost:5432/myapp_test"
})
class UserControllerE2ETest {
    @Autowired
    private WebTestClient webTestClient;

    @Test
    void shouldCreateUser() {
        webTestClient.post().uri("/api/users")
            .contentType(MediaType.APPLICATION_JSON)
            .header("Authorization", "Bearer test-token")
            .bodyValue("{\"name\":\"John\",\"email\":\"john@example.com\"}")
            .exchange()
            .expectStatus().isCreated()
            .expectBody()
            .jsonPath("$.name").isEqualTo("John");
    }
}
```

## Scala（Scalatra + ScalatraSuite）

```scala
class UserControllerE2ETest extends ScalatraFunSuite {
  val testDb = setupTestDatabase()
  val userRepo = new SlickUserRepository(testDb)
  val userUseCase = new UserUseCase(userRepo)
  addServlet(new UserController(userUseCase), "/api/users/*")

  test("POST /api/users should create a user") {
    post("/api/users",
      body = """{"name":"John","email":"john@example.com"}""",
      headers = Map("Content-Type" -> "application/json", "Authorization" -> "Bearer test-token")
    ) {
      status should equal(201)
      val json = parse(body)
      (json \ "name").extract[String] should equal("John")
    }
  }

  test("GET /api/users/:id should return 404 for non-existent user") {
    get("/api/users/99999",
      headers = Map("Authorization" -> "Bearer test-token")
    ) {
      status should equal(404)
    }
  }

  override def afterEach(): Unit = {
    cleanupTestData(testDb)
    super.afterEach()
  }
}
```

## TypeScript / JavaScript（Express + supertest）

```typescript
import request from 'supertest';
import { app } from '../src/app';
import { prisma } from '../src/db';

describe('User API E2E', () => {
    beforeEach(async () => {
        await prisma.user.deleteMany();
    });

    afterAll(async () => {
        await prisma.$disconnect();
    });

    describe('POST /api/users', () => {
        it('should create a user', async () => {
            const response = await request(app)
                .post('/api/users')
                .set('Authorization', 'Bearer test-token')
                .send({ name: 'John', email: 'john@example.com' })
                .expect(201);

            expect(response.body.name).toBe('John');
            expect(response.body.email).toBe('john@example.com');
            expect(response.body.id).toBeDefined();
        });

        it('should return 400 when name is empty', async () => {
            await request(app)
                .post('/api/users')
                .set('Authorization', 'Bearer test-token')
                .send({ name: '', email: 'john@example.com' })
                .expect(400);
        });

        it('should return 401 without auth token', async () => {
            await request(app)
                .post('/api/users')
                .send({ name: 'John', email: 'john@example.com' })
                .expect(401);
        });
    });

    describe('GET /api/users/:id', () => {
        it('should return a user by id', async () => {
            const created = await prisma.user.create({
                data: { name: 'John', email: 'john@example.com' }
            });

            const response = await request(app)
                .get(`/api/users/${created.id}`)
                .set('Authorization', 'Bearer test-token')
                .expect(200);

            expect(response.body.name).toBe('John');
        });

        it('should return 404 for non-existent user', async () => {
            await request(app)
                .get('/api/users/99999')
                .set('Authorization', 'Bearer test-token')
                .expect(404);
        });
    });
});
```

## Python（FastAPI + TestClient）

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base

TEST_DATABASE_URL = "postgresql://localhost:5432/myapp_test"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture(autouse=True)
def test_db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    def override_get_db():
        yield session
    app.dependency_overrides[get_db] = override_get_db
    yield session
    session.rollback()
    session.close()
    app.dependency_overrides.clear()

client = TestClient(app)

class TestUserAPI:
    def test_create_user(self):
        response = client.post(
            "/api/users",
            json={"name": "John", "email": "john@example.com"},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John"
        assert data["email"] == "john@example.com"

    def test_create_user_empty_name_returns_400(self):
        response = client.post(
            "/api/users",
            json={"name": "", "email": "john@example.com"},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 400

    def test_get_user_not_found_returns_404(self):
        response = client.get(
            "/api/users/99999",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 404

    def test_create_user_without_auth_returns_401(self):
        response = client.post(
            "/api/users",
            json={"name": "John", "email": "john@example.com"}
        )
        assert response.status_code == 401
```

---

## 認証ヘルパー例（Go）

```go
// 認証ヘルパーの例（Go）
func generateTestToken(t *testing.T, userID int, role string) string {
    t.Helper()
    token, err := auth.GenerateToken(userID, role, "test-secret")
    if err != nil {
        t.Fatalf("failed to generate test token: %v", err)
    }
    return token
}
```

## 外部APIモック例（Go）

DB以外の外部依存はモックで差し替える。DI（依存性注入）の仕組みを介してテスト時に差し替えると、テストサーバーを本番とほぼ同じ構成で起動できる。

```go
type mockPaymentClient struct {
    mock.Mock
}

func (m *mockPaymentClient) Charge(amount int, token string) (*PaymentResult, error) {
    args := m.Called(amount, token)
    return args.Get(0).(*PaymentResult), args.Error(1)
}

func TestCreateOrder_WithPayment(t *testing.T) {
    mockPayment := new(mockPaymentClient)
    mockPayment.On("Charge", 1000, "tok_test").Return(&PaymentResult{ID: "pay_123"}, nil)

    e := setupTestServerWithMocks(t, WithPaymentClient(mockPayment))

    body := `{"items":[{"id":1,"qty":2}],"payment_token":"tok_test"}`
    req := httptest.NewRequest(http.MethodPost, "/api/orders", strings.NewReader(body))
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Authorization", "Bearer test-token")
    rec := httptest.NewRecorder()
    e.ServeHTTP(rec, req)

    assert.Equal(t, http.StatusCreated, rec.Code)
    mockPayment.AssertExpectations(t)
}
```
