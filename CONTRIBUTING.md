# コントリビューションガイド

新しいスキルの追加や既存スキルの改善を歓迎します。

## 新しいスキルを追加する場合

1. `skills/` 配下にスキル名のディレクトリを作成する
2. `template/SKILL.md` を参考に `SKILL.md` を作成する
3. スクリプトがある場合は `scripts/` サブディレクトリに配置する
4. `.claude-plugin/marketplace.json` の `plugins` 配列にエントリを追加する
5. ルートの `README.md` のスキル一覧テーブルを更新する
6. Pull Request を作成する

## ディレクトリ構成

```
skills/your-skill-name/
├── SKILL.md              # 必須: スキル本体
├── scripts/              # 任意: ヘルパースクリプト
│   └── helper.py
└── references/           # 任意: 参考ドキュメント
    └── guide.md
```

## SKILL.md のルール

- YAML frontmatter に `name` と `description` を必ず含める
- `description` はスキルのトリガーとなるキーワードを豊富に含める
- SKILL.md 本体は 500 行以内を目安にする
- 長くなる場合は `references/` に分割してポインタを記載する

## スクリプトのルール

- 可能な限り標準ライブラリのみで動作するようにする
- 外部依存が必要な場合は SKILL.md の前提条件に明記する
- `python3 -m py_compile` で構文チェックが通ること
