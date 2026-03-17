---
name: dependabot-alerts
description: GitHub Dependabot alerts の調査・分析・修正方針の策定を行うスキル。`gh` CLI を使って Dependabot alerts の一覧取得、詳細調査、重大度別の分類、影響範囲の分析を行い、さらに拡張思考（extended thinking）を用いて各脆弱性に対する修正方針を深く検討する。ユーザーが「Dependabot」「脆弱性」「vulnerability」「security alerts」「依存関係の脆弱性」「CVE」「セキュリティアラート」「パッケージの更新」「セキュリティ修正」「脆弱性の対応方針」「依存関係の棚卸し」などに言及した場合にこのスキルを使うこと。dependabot alerts を確認したい、脆弱性を調べたい、セキュリティ状況を把握したい、修正計画を立てたい、といったリクエストにも対応する。
---

# Dependabot Alerts 調査・修正方針策定スキル

GitHub の Dependabot alerts を `gh` CLI で取得・分析し、脆弱性の状況を調査した上で、拡張思考を活用して修正方針を深く検討・策定するためのスキル。

## 前提条件

- `gh` CLI がインストールされ、`gh auth login` で認証済みであること
- トークンに `security_events` スコープ（または `repo` スコープ）が必要
  - 不足している場合: `gh auth refresh -s security_events` で追加を案内する

## ワークフロー概要

このスキルは大きく「調査フェーズ」と「修正方針策定フェーズ」の2段階で構成される。調査フェーズでアラートの全体像を把握した後、修正方針策定フェーズで拡張思考を用いて各脆弱性への対応を深く検討する。

```
[Step 1: 認証確認] → [Step 2: リポジトリ特定] → [Step 3: アラート取得]
    → [Step 4: 分析・分類] → [Step 5: 詳細調査]
    → [Step 6: 拡張思考による修正方針の検討]
    → [Step 7: 修正計画書の生成]
```

---

## 調査フェーズ

### Step 1: 認証・権限の確認

まず `gh` CLI が利用可能か確認する。

```bash
gh auth status
```

エラーが出た場合はユーザーに認証手順を案内する。

### Step 2: リポジトリの特定

ユーザーがリポジトリを指定していない場合、カレントディレクトリの Git リモートから推定する。

```bash
gh repo view --json nameWithOwner -q '.nameWithOwner'
```

取得できなければユーザーに `owner/repo` を尋ねる。

### Step 3: Alerts の一覧取得

スクリプトを使ってアラートを取得・整形する。

```bash
python3 SKILL_DIR/scripts/fetch_alerts.py --repo OWNER/REPO --format json
```

`SKILL_DIR` はこのスキルのディレクトリパス。もしスクリプトが利用できない場合は、以下の `gh api` コマンドで直接取得する。

```bash
gh api "repos/OWNER/REPO/dependabot/alerts?state=open&per_page=100" \
  --jq '.[] | {
    number,
    state,
    severity: .security_vulnerability.severity,
    package: .security_vulnerability.package.name,
    ecosystem: .security_vulnerability.package.ecosystem,
    summary: .security_advisory.summary,
    cve: (.security_advisory.identifiers[] | select(.type == "CVE") | .value),
    vulnerable_range: .security_vulnerability.vulnerable_version_range,
    patched_version: .security_vulnerability.first_patched_version.identifier,
    created_at,
    url: .html_url
  }'
```

### Step 4: 分析と分類

取得したアラートを以下の観点で分析する。

#### 重大度別の集計
severity（critical / high / medium / low）ごとにアラート数を集計し、全体像を把握する。

#### 優先度の判定
以下の基準で対応優先度を判定する:
- **即時対応（P0）**: critical で、パッチバージョンが存在する
- **早期対応（P1）**: high で、パッチバージョンが存在する
- **計画的対応（P2）**: medium / low で、パッチが存在する
- **調査必要（P3）**: パッチが存在せず、ワークアラウンドの確認が必要

#### パッケージ・エコシステム別の分類
同一パッケージに複数のアラートがある場合はまとめて報告する。

#### 依存関係の深さ確認
可能であれば、脆弱なパッケージが直接依存（direct）か推移的依存（transitive）かを確認する。

```bash
# npm の場合
npm ls <package-name> 2>/dev/null || true

# pip の場合
pip show <package-name> 2>/dev/null || true

# bundler の場合
bundle show <package-name> 2>/dev/null || true
```

### Step 5: 個別アラートの詳細調査

優先度 P0 / P1 のアラートについて、詳細情報を取得する。

```bash
gh api "repos/OWNER/REPO/dependabot/alerts/ALERT_NUMBER"
```

詳細情報として以下を確認する:
- CVE ID とアドバイザリの説明
- 影響を受けるバージョン範囲
- 修正済みバージョン
- CVSS スコアとベクター
- 攻撃条件（ネットワーク経由か、ローカルか、認証が必要か等）
- 参考リンク（NVD、GitHub Advisory Database 等）

---

## 修正方針策定フェーズ

### Step 6: 拡張思考による修正方針の検討

ここが本スキルの核心部分。アラート情報を収集した後、拡張思考（extended thinking）を使って各脆弱性への修正方針を多角的に検討する。

Claude に対し、以下の手順で拡張思考を要求する。拡張思考では結論を急がず、各観点を丁寧に掘り下げること。

#### 6-1: 脆弱性の実影響度の評価

各アラートについて、以下を考慮して「このプロジェクトにおける実際のリスク」を評価する:

- **脆弱性の種類**: RCE、XSS、SQLi、DoS、情報漏洩など。攻撃が成立する条件は何か。
- **利用コンテキスト**: 脆弱なパッケージをどのように使っているか。脆弱な機能を呼び出しているか。
  - ソースコード中で該当パッケージの import/require を grep で確認する:
    ```bash
    grep -r "import.*<package>" --include="*.ts" --include="*.js" --include="*.py" --include="*.rb" . 2>/dev/null | head -20
    grep -r "require.*<package>" --include="*.ts" --include="*.js" . 2>/dev/null | head -20
    ```
- **公開面**: アプリケーションはインターネットに公開されているか、内部ツールか。
- **データの機密性**: 扱うデータの性質（個人情報、決済情報、機密情報等）。
- **CVSS 環境スコア**: 基本スコアだけでなく、実環境に即した評価。

#### 6-2: 修正オプションの洗い出し

各アラートに対して考えうる修正オプションを列挙する:

**オプション A: パッチバージョンへの更新**
- パッチバージョンが存在する場合の最も直接的な修正。
- メジャーバージョンの変更を伴うか（breaking changes のリスク）。
- エコシステム別の更新コマンド:
  - npm: `npm install <package>@<version>` / `npm audit fix`
  - pip: `pip install --upgrade <package>==<version>`
  - bundler: `bundle update <package>`
  - go: `go get <package>@<version>`
  - cargo: `cargo update -p <package>`
  - composer: `composer update <package>`
  - maven/gradle: pom.xml / build.gradle のバージョンを変更

**オプション B: メジャーバージョンアップ**
- パッチがメジャーバージョンアップを伴う場合の対応。
- API の互換性調査が必要。
- テスト範囲の見積もり。

**オプション C: 代替パッケージへの移行**
- パッチが存在せず、メンテナンスが停止している場合。
- 同等機能を持つ代替パッケージの候補。
- 移行工数の概算。

**オプション D: ワークアラウンドの適用**
- パッチが存在しない場合の一時的な緩和策。
- 入力バリデーションの強化、WAF ルールの追加、機能の無効化など。

**オプション E: リスクの受容**
- 脆弱性の攻撃条件が限定的で、実影響が低い場合。
- 受容する場合の根拠と再評価スケジュール。

#### 6-3: 依存関係の連鎖影響の検討

拡張思考で以下を検討する:

- パッケージ A を更新すると、パッケージ B のバージョン制約と衝突しないか。
- 複数のアラートが同一パッケージの異なるバージョン範囲に関わっている場合、一度の更新で複数アラートを解消できるか。
- lock ファイル（package-lock.json、Gemfile.lock、poetry.lock 等）の再生成が必要か。
- モノレポの場合、影響するワークスペースの特定。

実際の依存関係の衝突確認:
```bash
# npm の場合
npm ls --all 2>&1 | grep "ERESOLVE\|peer dep\|invalid" | head -20

# pip の場合（pipdeptree がある場合）
pipdeptree --warn silence 2>/dev/null | grep -i <package> || pip check 2>&1 | head -20
```

#### 6-4: テスト戦略の検討

拡張思考で修正後のテスト戦略を検討する:

- 既存のテストスイートでカバーされているか。
- 脆弱なパッケージの利用箇所に対する回帰テストの必要性。
- CI/CD パイプラインでの自動検証。
- ステージング環境での動作確認の要否。

テストの存在確認:
```bash
# テストファイルの有無を確認
find . -type f \( -name "*test*" -o -name "*spec*" \) -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null | head -20

# CI 設定の確認
ls -la .github/workflows/ 2>/dev/null || ls -la .circleci/ 2>/dev/null || ls -la .gitlab-ci.yml 2>/dev/null || true
```

#### 6-5: 修正の優先順序と作業計画の決定

全アラートの修正方針が出揃ったら、拡張思考で以下を総合的に判断する:

- どのアラートから着手すべきか（リスクの大きさ × 修正の容易さ）。
- 一括で対応可能なグループ（同一パッケージ系統、同一エコシステム）。
- 修正作業を PR にどう分割するか（1PR にまとめるか、パッケージごとに分けるか）。
- 見積もり工数（S / M / L の粒度で十分）。

### Step 7: 修正計画書の生成

拡張思考の検討結果を踏まえ、以下の構成でアクショナブルな修正計画書を生成する。

#### 出力構成

```
# Dependabot Alerts 修正計画書

## 1. エグゼクティブサマリー
- Open アラート総数と重大度別内訳
- 全体的なリスク評価（高/中/低）
- 推奨する対応タイムライン

## 2. 即時対応が必要なアラート（P0）
### アラート #XX: <パッケージ名> - <脆弱性サマリー>
- **CVE**: CVE-XXXX-XXXXX
- **CVSS**: X.X (Critical)
- **実影響度評価**: <拡張思考による評価結果>
- **推奨修正方針**: <オプション A/B/C/D/E>
- **修正コマンド**: `<具体的なコマンド>`
- **Breaking Changes リスク**: あり/なし（詳細）
- **必要なテスト**: <テスト戦略>
- **見積もり工数**: S/M/L
（P0 のアラートを繰り返す）

## 3. 早期対応が必要なアラート（P1）
（同様の構成で P1 アラートを記載）

## 4. 計画的に対応するアラート（P2）
（同様の構成で P2 アラートを記載）

## 5. 調査が必要なアラート（P3）
（パッチなしのアラートについて調査事項を記載）

## 6. 修正作業の推奨進め方
- PR の分割方針
- 作業の依存関係（A を先にやらないと B ができない等）
- CI/CD での検証手順
- ロールバック計画

## 7. 中長期的な改善提案
- Dependabot auto-merge の設定検討
- Renovate Bot 等の代替ツールの検討
- セキュリティポリシーの策定
- 定期的な依存関係の棚卸しプロセスの導入
```

この修正計画書はユーザーの要望に応じて Markdown ファイルとして出力する。

---

## 拡張思考の活用ガイドライン

修正方針の検討（Step 6）では、Claude は拡張思考を以下のように活用する:

1. **結論を急がない**: まずすべての情報を整理してから判断する。「このパッケージは更新するだけ」と安易に結論づけず、副作用を丁寧に検討する。

2. **トレードオフを明示する**: 各修正オプションのメリット・デメリットを比較する。例えば「すぐに更新すればリスクは解消するが、メジャーバージョンアップによる regression リスクがある」のようなトレードオフを可視化する。

3. **不確実性を認める**: 情報が不足している場合は推測で埋めず、「これは確認が必要」と明示する。特にコードベースの利用状況が不明な場合は、ユーザーへの確認事項としてリストアップする。

4. **実務的な視点を持つ**: 理論的な最善策だけでなく、チームのリソース、デプロイサイクル、ビジネスへの影響を考慮した現実的な提案を行う。

5. **複数アラートの相互関係を分析する**: アラートを個別に見るのではなく、依存関係のグラフ全体として捉え、効率的な修正順序を考える。

---

## 追加コマンド

### Organization 全体の alerts

```bash
gh api "orgs/ORG_NAME/dependabot/alerts?state=open&per_page=100" \
  --jq '.[] | {
    repo: .repository.full_name,
    number,
    severity: .security_vulnerability.severity,
    package: .security_vulnerability.package.name,
    summary: .security_advisory.summary
  }'
```

### フィルタリング

```bash
# severity でフィルタ
gh api "repos/OWNER/REPO/dependabot/alerts?severity=critical&state=open"

# ecosystem でフィルタ
gh api "repos/OWNER/REPO/dependabot/alerts?ecosystem=npm&state=open"
```

### Dependabot Security Updates の設定確認

```bash
# リポジトリの Dependabot 設定を確認
gh api "repos/OWNER/REPO/vulnerability-alerts" 2>&1 || true
cat .github/dependabot.yml 2>/dev/null || echo "dependabot.yml not found"
```

---

## エラーハンドリング

- `gh: Not Found (HTTP 404)`: リポジトリが存在しないか、アクセス権がない。リポジトリ名を確認し、private repo の場合は適切な権限があるか確認する。
- `gh: Resource not accessible by personal access token (HTTP 403)`: `security_events` スコープが不足している。`gh auth refresh -s security_events` を案内する。
- `gh: command not found`: `gh` CLI がインストールされていない。インストール手順を案内する。
- Dependabot が有効化されていない場合: リポジトリの Settings > Code security で有効化する手順を案内する。
- アラートが 0 件の場合: 正常な状態であることを伝え、予防的な改善提案（dependabot.yml の設定最適化など）を行う。
