# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Code / Claude.ai 向けのカスタムスキルコレクション。各スキルは `skills/<skill-name>/` 配下に配置され、SKILL.md（YAML frontmatter + Markdown）とオプションのヘルパースクリプトで構成される。

## Architecture

```
skills/<skill-name>/
├── SKILL.md              # スキル本体（必須）。YAML frontmatter に name, description を持つ
├── scripts/              # ヘルパースクリプト（任意）
└── references/           # 参考ドキュメント（任意）
.claude-plugin/
└── marketplace.json      # Plugin Marketplace 用のスキル登録情報
```

- **SKILL.md**: スキルのトリガー条件（description 内のキーワード）と実行手順を定義。500行以内が目安。
- **scripts/**: 標準ライブラリのみで動作するスクリプトを推奨。外部依存がある場合は SKILL.md の前提条件に明記。
- **marketplace.json**: 新スキル追加時に `plugins` 配列へのエントリ追加が必要。

## Adding a New Skill

1. `skills/<name>/` にディレクトリを作成
2. `SKILL.md` を作成（frontmatter に `name` と `description` を必須で含める）
3. `.claude-plugin/marketplace.json` の `plugins` に追加
4. `README.md` のスキル一覧テーブルを更新

## Validation

```bash
# Python スクリプトの構文チェック
python3 -m py_compile skills/*/scripts/*.py
```
