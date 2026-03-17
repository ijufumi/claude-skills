# claude-skills

Claude Code / Claude.ai 向けのカスタムスキルコレクション。

## スキル一覧

| スキル名 | 説明 | エコシステム |
|----------|------|-------------|
| [dependabot-alerts](./skills/dependabot-alerts/) | GitHub Dependabot alerts の調査・分析・修正方針の策定 | GitHub |

> 今後もスキルを追加予定です。

## インストール方法

### Claude Code（Plugin Marketplace 経由）

```bash
# このリポジトリを marketplace として登録
/plugin marketplace add YOUR_USERNAME/claude-skills

# 個別スキルをインストール
/plugin install dependabot-alerts@YOUR_USERNAME-claude-skills
```

### Claude Code（手動インストール）

```bash
# 全スキルを個人用ディレクトリに配置
git clone https://github.com/YOUR_USERNAME/claude-skills.git
cp -r claude-skills/skills/* ~/.claude/skills/

# または特定のスキルだけ
cp -r claude-skills/skills/dependabot-alerts ~/.claude/skills/
```

### プロジェクト固有（チーム共有）

```bash
# プロジェクトルートに配置して Git 管理
mkdir -p .claude/skills
cp -r /path/to/claude-skills/skills/dependabot-alerts .claude/skills/
git add .claude/skills/
git commit -m "Add dependabot-alerts skill"
```

### Claude.ai（Web UI）

1. [Releases](../../releases) から `.skill` ファイルをダウンロード
2. Claude.ai の **Settings > Capabilities** で Code execution を有効化
3. **Customize > Skills** で `.skill` ファイルをアップロード

## スキルの使い方

インストール後は自然言語で依頼するだけで自動的にスキルが発動します。

```
このリポジトリの Dependabot alerts を調べて、修正計画を立ててください
```

スラッシュコマンドでも呼び出せます:

```
/dependabot-alerts
```

## 前提条件

各スキルの前提条件は個別の SKILL.md に記載しています。共通して必要なもの:

- Claude Code または Claude.ai（Pro / Max / Team / Enterprise プラン）
- Code execution が有効化されていること

## コントリビューション

Issue や Pull Request を歓迎します。新しいスキルを追加する場合は `skills/` 配下にディレクトリを作成し、[テンプレート](./template/) を参考にしてください。

## ライセンス

MIT License
