#!/usr/bin/env python3
"""
Dependabot alerts を取得・分析し、修正方針検討に必要な情報を収集するスクリプト。
gh CLI が認証済みの環境で動作する。

Usage:
    python3 fetch_alerts.py --repo OWNER/REPO [OPTIONS]

Options:
    --state open|dismissed|fixed|auto_dismissed  (default: open)
    --severity critical,high,...                  カンマ区切りで重大度フィルタ
    --ecosystem npm|pip|...                      エコシステムフィルタ
    --format table|json|markdown|plan            出力形式 (plan=修正計画テンプレート)
    --output FILE                                ファイルに出力
    --detail NUMBER                              特定アラートの詳細表示
    --analyze-deps                               依存関係の深さ・利用状況を調査
    --scan-usage                                 ソースコード中の利用箇所をスキャン
    --check-tests                                テスト・CI設定の存在確認
"""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone


def run_gh_api(endpoint: str) -> list | dict:
    """gh api コマンドを実行して JSON を返す。"""
    cmd = ["gh", "api", endpoint, "--paginate"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        if not output:
            return []
        if output.startswith("["):
            output = output.replace("]\n[", ",").replace("][", ",")
        return json.loads(output)
    except subprocess.CalledProcessError as e:
        print(f"Error calling gh api: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'gh' CLI not found. Please install GitHub CLI.", file=sys.stderr)
        sys.exit(1)


def run_command(cmd: str, cwd: str = ".") -> str:
    """シェルコマンドを実行して標準出力を返す。エラー時は空文字。"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=cwd
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, Exception):
        return ""


def fetch_alerts(repo: str, state: str = "open") -> list:
    """Dependabot alerts を取得する。"""
    endpoint = f"repos/{repo}/dependabot/alerts?state={state}&per_page=100"
    return run_gh_api(endpoint)


def parse_alert(alert: dict) -> dict:
    """アラートから必要な情報を抽出する。"""
    vuln = alert.get("security_vulnerability", {})
    advisory = alert.get("security_advisory", {})
    package = vuln.get("package", {})

    cve_ids = [
        ident.get("value", "")
        for ident in advisory.get("identifiers", [])
        if ident.get("type") == "CVE"
    ]

    ghsa_ids = [
        ident.get("value", "")
        for ident in advisory.get("identifiers", [])
        if ident.get("type") == "GHSA"
    ]

    patched = vuln.get("first_patched_version")
    patched_version = patched.get("identifier") if patched else None

    cvss = advisory.get("cvss", {})

    # CWE 情報の抽出
    cwes = [cwe.get("cwe_id", "") for cwe in advisory.get("cwes", [])]

    # 経過日数の計算
    created_at = alert.get("created_at", "")
    days_open = None
    if created_at:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            days_open = (datetime.now(timezone.utc) - created).days
        except (ValueError, TypeError):
            pass

    return {
        "number": alert.get("number"),
        "state": alert.get("state"),
        "severity": vuln.get("severity", "unknown"),
        "package": package.get("name", "unknown"),
        "ecosystem": package.get("ecosystem", "unknown"),
        "summary": advisory.get("summary", ""),
        "description": advisory.get("description", ""),
        "cve_ids": cve_ids,
        "ghsa_ids": ghsa_ids,
        "cwes": cwes,
        "vulnerable_range": vuln.get("vulnerable_version_range", ""),
        "patched_version": patched_version,
        "cvss_score": cvss.get("score"),
        "cvss_vector": cvss.get("vector_string"),
        "created_at": created_at,
        "days_open": days_open,
        "dismissed_reason": alert.get("dismissed_reason"),
        "auto_dismissed_at": alert.get("auto_dismissed_at"),
        "html_url": alert.get("html_url", ""),
        "references": [ref.get("url", "") for ref in advisory.get("references", [])],
        # 修正方針検討用のフィールド（後から埋める）
        "dependency_depth": None,       # direct / transitive
        "usage_locations": [],           # ソースコード中の利用箇所
        "update_type": None,            # patch / minor / major
    }


def classify_update_type(alert: dict) -> str | None:
    """パッチバージョンへの更新がどの程度の変更を伴うか推定する。"""
    patched = alert.get("patched_version")
    vuln_range = alert.get("vulnerable_range", "")
    if not patched:
        return None
    # 簡易的な判定: vulnerable_range からメジャーバージョンを推定
    # 正確な判定にはインストール済みバージョンとの比較が必要
    return "patch_available"


def analyze_alerts(alerts: list[dict]) -> dict:
    """アラートを分析してサマリーを生成する。"""
    severity_counts = Counter()
    ecosystem_counts = Counter()
    cwe_counts = Counter()
    package_alerts = defaultdict(list)
    priority_groups = {
        "P0_immediate": [],
        "P1_early": [],
        "P2_planned": [],
        "P3_investigate": [],
    }

    for alert in alerts:
        severity_counts[alert["severity"]] += 1
        ecosystem_counts[alert["ecosystem"]] += 1
        package_alerts[alert["package"]].append(alert)
        for cwe in alert.get("cwes", []):
            cwe_counts[cwe] += 1

        has_patch = alert["patched_version"] is not None
        sev = alert["severity"]

        if sev == "critical" and has_patch:
            priority_groups["P0_immediate"].append(alert)
        elif sev == "high" and has_patch:
            priority_groups["P1_early"].append(alert)
        elif has_patch:
            priority_groups["P2_planned"].append(alert)
        else:
            priority_groups["P3_investigate"].append(alert)

    # 同一パッケージの複数アラートをグルーピング
    grouped_packages = {}
    for pkg, pkg_alerts in package_alerts.items():
        grouped_packages[pkg] = {
            "count": len(pkg_alerts),
            "max_severity": max(
                pkg_alerts,
                key=lambda a: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(a["severity"], 0),
            )["severity"],
            "alert_numbers": [a["number"] for a in pkg_alerts],
            "ecosystem": pkg_alerts[0]["ecosystem"],
            "all_patchable": all(a["patched_version"] is not None for a in pkg_alerts),
        }

    # 経過日数の統計
    days_list = [a["days_open"] for a in alerts if a["days_open"] is not None]
    age_stats = {}
    if days_list:
        age_stats = {
            "oldest_days": max(days_list),
            "newest_days": min(days_list),
            "average_days": round(sum(days_list) / len(days_list), 1),
            "over_30_days": sum(1 for d in days_list if d > 30),
            "over_90_days": sum(1 for d in days_list if d > 90),
        }

    return {
        "total": len(alerts),
        "severity_counts": dict(severity_counts),
        "ecosystem_counts": dict(ecosystem_counts),
        "cwe_counts": dict(cwe_counts.most_common(10)),
        "grouped_packages": grouped_packages,
        "priority_groups": {
            k: [a["number"] for a in v] for k, v in priority_groups.items()
        },
        "priority_counts": {k: len(v) for k, v in priority_groups.items()},
        "age_stats": age_stats,
    }


def scan_package_usage(package_name: str, ecosystem: str, search_dir: str = ".") -> list[str]:
    """ソースコード中でパッケージがどこで使われているかスキャンする。"""
    results = []

    # エコシステムに応じた検索パターン
    patterns = {
        "npm": [
            f'import.*["\'{package_name}',
            f'require.*["\'{package_name}',
            f'from ["\'{package_name}',
        ],
        "pip": [
            f"import {package_name}",
            f"from {package_name}",
        ],
        "rubygems": [
            f'require ["\'{package_name}',
            f"gem ['\"{package_name}",
        ],
        "go": [
            f'"{package_name}',
        ],
        "cargo": [
            f"use {package_name}",
        ],
    }

    search_patterns = patterns.get(ecosystem.lower(), [f"{package_name}"])
    excludes = "--exclude-dir=node_modules --exclude-dir=.git --exclude-dir=vendor --exclude-dir=__pycache__ --exclude-dir=.venv --exclude-dir=venv"

    for pattern in search_patterns:
        output = run_command(
            f'grep -rn "{pattern}" {excludes} --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" --include="*.rb" --include="*.go" --include="*.rs" . 2>/dev/null | head -10',
            cwd=search_dir,
        )
        if output:
            results.extend(output.split("\n"))

    return list(set(results))[:20]


def check_dependency_depth(package_name: str, ecosystem: str) -> str | None:
    """パッケージが直接依存か推移的依存かを確認する。"""
    if ecosystem.lower() == "npm":
        # package.json に直接記載されているか確認
        try:
            with open("package.json", "r") as f:
                pkg_json = json.load(f)
            all_deps = {
                **pkg_json.get("dependencies", {}),
                **pkg_json.get("devDependencies", {}),
            }
            return "direct" if package_name in all_deps else "transitive"
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    elif ecosystem.lower() == "pip":
        # requirements.txt / setup.py / pyproject.toml を確認
        for req_file in ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.py", "setup.cfg"]:
            try:
                with open(req_file, "r") as f:
                    content = f.read().lower()
                if package_name.lower() in content:
                    return "direct"
            except FileNotFoundError:
                continue
        return "transitive"

    elif ecosystem.lower() == "rubygems":
        try:
            with open("Gemfile", "r") as f:
                content = f.read()
            return "direct" if package_name in content else "transitive"
        except FileNotFoundError:
            pass

    return None


def check_test_infrastructure() -> dict:
    """テスト・CI 設定の存在を確認する。"""
    info = {"test_files": [], "ci_configs": [], "has_tests": False, "has_ci": False}

    # テストファイル
    output = run_command(
        'find . -type f \\( -name "*test*" -o -name "*spec*" \\) '
        '-not -path "*/node_modules/*" -not -path "*/.git/*" '
        '-not -path "*/vendor/*" -not -path "*/__pycache__/*" 2>/dev/null | head -15'
    )
    if output:
        info["test_files"] = output.split("\n")
        info["has_tests"] = True

    # CI 設定
    ci_paths = [
        ".github/workflows",
        ".circleci",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        ".travis.yml",
        "azure-pipelines.yml",
        "bitbucket-pipelines.yml",
    ]
    for path in ci_paths:
        if os.path.exists(path):
            info["ci_configs"].append(path)
            info["has_ci"] = True
            if os.path.isdir(path):
                files = run_command(f"ls {path}")
                if files:
                    info["ci_configs"].extend([f"{path}/{f}" for f in files.split("\n")])

    return info


def check_dependabot_config() -> dict | None:
    """dependabot.yml の設定を確認する。"""
    for path in [".github/dependabot.yml", ".github/dependabot.yaml"]:
        try:
            with open(path, "r") as f:
                return {"path": path, "content": f.read()}
        except FileNotFoundError:
            continue
    return None


# ---------- 出力フォーマッター ----------

def format_table(alerts: list[dict]) -> str:
    """テーブル形式で出力する。"""
    if not alerts:
        return "No alerts found."

    header = f"{'#':<6} {'Sev':<10} {'Package':<30} {'Eco':<10} {'Patched':<15} {'Days':<6} {'CVE':<20}"
    separator = "-" * len(header)
    lines = [header, separator]

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for a in sorted(alerts, key=lambda x: sev_order.get(x["severity"], 4)):
        cve = ", ".join(a["cve_ids"]) if a["cve_ids"] else "-"
        patched = a["patched_version"] or "N/A"
        days = str(a["days_open"]) if a["days_open"] is not None else "?"
        lines.append(
            f"{a['number']:<6} {a['severity']:<10} {a['package']:<30} {a['ecosystem']:<10} {patched:<15} {days:<6} {cve:<20}"
        )

    return "\n".join(lines)


def format_markdown(alerts: list[dict], analysis: dict) -> str:
    """Markdown 形式でレポートを生成する。"""
    lines = []

    lines.append("# Dependabot Alerts レポート\n")
    lines.append(f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"**Open アラート総数**: {analysis['total']}\n")

    # 重大度
    lines.append("## 重大度別の内訳\n")
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    for sev in ["critical", "high", "medium", "low"]:
        count = analysis["severity_counts"].get(sev, 0)
        emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(sev, "")
        lines.append(f"| {emoji} {sev} | {count} |")

    # 優先度別
    lines.append("\n## 優先度別の内訳\n")
    lines.append("| Priority | Count | Description |")
    lines.append("|----------|-------|-------------|")
    priority_desc = {
        "P0_immediate": "即時対応 (Critical + パッチあり)",
        "P1_early": "早期対応 (High + パッチあり)",
        "P2_planned": "計画的対応 (Medium/Low + パッチあり)",
        "P3_investigate": "調査必要 (パッチなし)",
    }
    for key, desc in priority_desc.items():
        count = analysis["priority_counts"].get(key, 0)
        lines.append(f"| {key.split('_')[0]} | {count} | {desc} |")

    # 経過日数
    age = analysis.get("age_stats", {})
    if age:
        lines.append("\n## アラートの経過日数\n")
        lines.append(f"- 最古: {age.get('oldest_days', '?')} 日")
        lines.append(f"- 最新: {age.get('newest_days', '?')} 日")
        lines.append(f"- 平均: {age.get('average_days', '?')} 日")
        lines.append(f"- 30日超: {age.get('over_30_days', 0)} 件")
        lines.append(f"- 90日超: {age.get('over_90_days', 0)} 件")

    # エコシステム別
    lines.append("\n## エコシステム別の内訳\n")
    lines.append("| Ecosystem | Count |")
    lines.append("|-----------|-------|")
    for eco, count in sorted(analysis["ecosystem_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"| {eco} | {count} |")

    # パッケージグループ
    lines.append("\n## パッケージ別グループ\n")
    lines.append("| Package | Alerts | Max Severity | All Patchable | Ecosystem |")
    lines.append("|---------|--------|-------------|---------------|-----------|")
    for pkg, info in sorted(
        analysis["grouped_packages"].items(),
        key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x[1]["max_severity"], 4),
    ):
        patchable = "✅" if info["all_patchable"] else "❌"
        lines.append(f"| {pkg} | {info['count']} | {info['max_severity']} | {patchable} | {info['ecosystem']} |")

    # 優先対応リスト詳細
    for key, label in priority_desc.items():
        group_numbers = set(analysis["priority_groups"].get(key, []))
        group_alerts = [a for a in alerts if a["number"] in group_numbers]
        if group_alerts:
            lines.append(f"\n## {key.split('_')[0]}: {label}\n")
            lines.append("| # | Package | Severity | Vulnerable Range | Patched | Days Open | CVE |")
            lines.append("|---|---------|----------|-----------------|---------|-----------|-----|")
            for a in group_alerts:
                cve = ", ".join(a["cve_ids"]) if a["cve_ids"] else "-"
                patched = a["patched_version"] or "N/A"
                days = str(a["days_open"]) if a["days_open"] is not None else "?"
                lines.append(
                    f"| {a['number']} | {a['package']} | {a['severity']} "
                    f"| {a['vulnerable_range']} | {patched} | {days} | {cve} |"
                )

    return "\n".join(lines)


def format_plan_template(alerts: list[dict], analysis: dict, extra_info: dict) -> str:
    """修正計画書テンプレートを生成する。拡張思考で埋める部分を明示。"""
    lines = []
    lines.append("# Dependabot Alerts 修正計画書\n")
    lines.append(f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # エグゼクティブサマリー
    lines.append("## 1. エグゼクティブサマリー\n")
    lines.append(f"- **Open アラート総数**: {analysis['total']}")
    for sev in ["critical", "high", "medium", "low"]:
        count = analysis["severity_counts"].get(sev, 0)
        if count > 0:
            lines.append(f"  - {sev}: {count} 件")

    age = analysis.get("age_stats", {})
    if age.get("over_90_days", 0) > 0:
        lines.append(f"- ⚠️ **90日以上未対応のアラート**: {age['over_90_days']} 件")

    lines.append(f"- **全体的なリスク評価**: [拡張思考で評価]")
    lines.append(f"- **推奨対応タイムライン**: [拡張思考で策定]\n")

    # 優先度グループごとの詳細
    priority_desc = {
        "P0_immediate": ("2. 即時対応が必要なアラート（P0）", "🔴"),
        "P1_early": ("3. 早期対応が必要なアラート（P1）", "🟠"),
        "P2_planned": ("4. 計画的に対応するアラート（P2）", "🟡"),
        "P3_investigate": ("5. 調査が必要なアラート（P3）", "🔵"),
    }

    for key, (section_title, emoji) in priority_desc.items():
        group_numbers = set(analysis["priority_groups"].get(key, []))
        group_alerts = [a for a in alerts if a["number"] in group_numbers]
        if not group_alerts:
            continue

        lines.append(f"## {section_title}\n")

        for a in group_alerts:
            cve_str = ", ".join(a["cve_ids"]) if a["cve_ids"] else "N/A"
            cwe_str = ", ".join(a.get("cwes", [])) if a.get("cwes") else "N/A"
            lines.append(f"### {emoji} アラート #{a['number']}: {a['package']} - {a['summary']}\n")
            lines.append(f"- **CVE**: {cve_str}")
            lines.append(f"- **CWE**: {cwe_str}")
            if a["cvss_score"]:
                lines.append(f"- **CVSS**: {a['cvss_score']} ({a['severity']})")
            lines.append(f"- **脆弱なバージョン範囲**: {a['vulnerable_range']}")
            lines.append(f"- **修正済みバージョン**: {a['patched_version'] or 'なし'}")
            lines.append(f"- **経過日数**: {a['days_open'] or '不明'} 日")
            lines.append(f"- **エコシステム**: {a['ecosystem']}")

            # 依存関係の深さ
            if a.get("dependency_depth"):
                lines.append(f"- **依存の種類**: {a['dependency_depth']}")

            # 利用箇所
            if a.get("usage_locations"):
                lines.append(f"- **利用箇所** ({len(a['usage_locations'])} 件):")
                for loc in a["usage_locations"][:5]:
                    lines.append(f"  - `{loc}`")

            lines.append(f"- **実影響度評価**: [拡張思考で評価]")
            lines.append(f"- **推奨修正方針**: [拡張思考で決定]")
            lines.append(f"- **修正コマンド**: [拡張思考で提示]")
            lines.append(f"- **Breaking Changes リスク**: [拡張思考で評価]")
            lines.append(f"- **必要なテスト**: [拡張思考で策定]")
            lines.append(f"- **見積もり工数**: [拡張思考で判定]\n")

    # テスト・CI情報
    test_info = extra_info.get("test_info", {})
    lines.append("## 6. 修正作業の推奨進め方\n")
    if test_info.get("has_ci"):
        lines.append(f"- **CI 設定**: {', '.join(test_info.get('ci_configs', []))}")
    else:
        lines.append("- **CI 設定**: 未検出 ⚠️")
    if test_info.get("has_tests"):
        lines.append(f"- **テストファイル**: {len(test_info.get('test_files', []))} 件検出")
    else:
        lines.append("- **テストファイル**: 未検出 ⚠️")

    lines.append("- **PR 分割方針**: [拡張思考で策定]")
    lines.append("- **作業の依存関係**: [拡張思考で整理]")
    lines.append("- **ロールバック計画**: [拡張思考で策定]\n")

    # Dependabot 設定
    dep_config = extra_info.get("dependabot_config")
    lines.append("## 7. 中長期的な改善提案\n")
    if dep_config:
        lines.append(f"- **dependabot.yml**: `{dep_config['path']}` に設定あり")
    else:
        lines.append("- **dependabot.yml**: 未設定 → 作成を推奨")
    lines.append("- [拡張思考で中長期改善を提案]\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch, analyze, and plan fixes for Dependabot alerts")
    parser.add_argument("--repo", required=True, help="Repository (OWNER/REPO)")
    parser.add_argument("--state", default="open",
                        choices=["open", "dismissed", "fixed", "auto_dismissed"],
                        help="Alert state filter (default: open)")
    parser.add_argument("--severity", default=None,
                        help="Comma-separated severity filter (e.g., critical,high)")
    parser.add_argument("--ecosystem", default=None,
                        help="Ecosystem filter (e.g., npm, pip, bundler)")
    parser.add_argument("--format", dest="fmt", default="table",
                        choices=["table", "json", "markdown", "plan"],
                        help="Output format (default: table, plan=修正計画テンプレート)")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--detail", type=int, default=None,
                        help="Show detail for specific alert number")
    parser.add_argument("--analyze-deps", action="store_true",
                        help="Analyze dependency depth for each alert")
    parser.add_argument("--scan-usage", action="store_true",
                        help="Scan source code for package usage locations")
    parser.add_argument("--check-tests", action="store_true",
                        help="Check for test files and CI configurations")

    args = parser.parse_args()

    # 個別アラート詳細
    if args.detail:
        raw = run_gh_api(f"repos/{args.repo}/dependabot/alerts/{args.detail}")
        alert = parse_alert(raw)
        if args.scan_usage:
            alert["usage_locations"] = scan_package_usage(alert["package"], alert["ecosystem"])
        if args.analyze_deps:
            alert["dependency_depth"] = check_dependency_depth(alert["package"], alert["ecosystem"])
        print(json.dumps(alert, indent=2, ensure_ascii=False))
        return

    # アラート一覧取得
    raw_alerts = fetch_alerts(args.repo, args.state)
    alerts = [parse_alert(a) for a in raw_alerts]

    # フィルタリング
    if args.severity:
        severities = set(args.severity.split(","))
        alerts = [a for a in alerts if a["severity"] in severities]
    if args.ecosystem:
        alerts = [a for a in alerts if a["ecosystem"].lower() == args.ecosystem.lower()]

    # オプション: 依存関係の深さ分析
    if args.analyze_deps:
        print("Analyzing dependency depth...", file=sys.stderr)
        for alert in alerts:
            alert["dependency_depth"] = check_dependency_depth(alert["package"], alert["ecosystem"])

    # オプション: ソースコード利用箇所スキャン
    if args.scan_usage:
        print("Scanning package usage in source code...", file=sys.stderr)
        for alert in alerts:
            alert["usage_locations"] = scan_package_usage(alert["package"], alert["ecosystem"])

    # 分析
    analysis = analyze_alerts(alerts)

    # 追加情報の収集
    extra_info = {}
    if args.check_tests or args.fmt == "plan":
        extra_info["test_info"] = check_test_infrastructure()
        extra_info["dependabot_config"] = check_dependabot_config()

    # 出力
    if args.fmt == "json":
        output_data = {
            "alerts": alerts,
            "analysis": analysis,
        }
        if extra_info:
            output_data["extra_info"] = extra_info
        output = json.dumps(output_data, indent=2, ensure_ascii=False, default=str)
    elif args.fmt == "markdown":
        output = format_markdown(alerts, analysis)
    elif args.fmt == "plan":
        # plan モードでは自動的に依存関係・利用箇所の分析を行う
        if not args.analyze_deps:
            for alert in alerts:
                alert["dependency_depth"] = check_dependency_depth(alert["package"], alert["ecosystem"])
        if not args.scan_usage:
            for alert in alerts:
                alert["usage_locations"] = scan_package_usage(alert["package"], alert["ecosystem"])
        if "test_info" not in extra_info:
            extra_info["test_info"] = check_test_infrastructure()
            extra_info["dependabot_config"] = check_dependabot_config()
        output = format_plan_template(alerts, analysis, extra_info)
    else:
        output = format_table(alerts)
        output += f"\n\nTotal: {analysis['total']} alerts"
        output += f"\nSeverity: " + ", ".join(f"{k}={v}" for k, v in sorted(analysis["severity_counts"].items()))
        output += f"\nPriority: " + ", ".join(f"{k}={v}" for k, v in sorted(analysis["priority_counts"].items()))

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
