# MindBase Menubar App - Release Guide

このドキュメントは、MindBase Menubar appのリリース手順を説明します。

## アーキテクチャ概要

### ビルド＆配布戦略

**方針**: GitHub Releasesでビルド済み.appバンドルを配布

```
Local Development → GitHub Release → Homebrew Tap
        ↓                 ↓               ↓
   make menubar-run   .app bundle    brew install
```

### ファイル構成

```
mindbase/
├── apps/menubar-swift/                    # Swift Package
│   ├── Package.swift
│   └── Sources/MindBaseMenubar/
│       ├── MindBaseMenubar.swift         # Main app
│       ├── ChatWindow.swift              # Chat UI
│       └── ConversationWatcher.swift     # File watcher
├── scripts/build-menubar-app.sh          # .appバンドル生成スクリプト
├── Formula/mindbase-menubar.rb           # Homebrew Formula
└── .github/workflows/release-menubar.yml # CI/CD

homebrew-tap/
└── Formula/mindbase-menubar.rb           # 自動更新される
```

## リリース手順

### 1. ローカルビルド＆テスト

```bash
# ビルド
make menubar-build

# ローカルで起動確認
make menubar-run

# 動作確認
# - メニューバーにbrainアイコン表示
# - Auto-Collection トグル動作
# - Chat window 起動 (Cmd+Space)
# - Health check 正常
```

### 2. GitHub Release作成

**タグ形式**: `menubar-v{MAJOR}.{MINOR}.{PATCH}`

#### 手動リリース（推奨）

```bash
# 1. バージョン決定（例: 1.0.0）
VERSION="1.0.0"

# 2. タグ作成
git tag -a "menubar-v${VERSION}" -m "Release MindBase Menubar v${VERSION}"
git push origin "menubar-v${VERSION}"

# 3. GitHub Actionsが自動実行
# - macOS 15でSwiftビルド
# - .appバンドル生成
# - tarball作成（mindbase-menubar-1.0.0-universal.tar.gz）
# - GitHub Releaseに公開
# - homebrew-tapを自動更新
```

#### GitHub UI経由（代替）

1. GitHub Actions → `Release Menubar App` → `Run workflow`
2. バージョン入力（例: `1.0.0`）
3. `Run workflow` クリック

### 3. Homebrew Tap 自動更新

GitHub Actionsが以下を自動実行：

```bash
# 1. リリースtarballダウンロード
curl -L "https://github.com/agiletec-inc/mindbase/releases/download/menubar-v1.0.0/mindbase-menubar-1.0.0-universal.tar.gz"

# 2. SHA256計算
shasum -a 256 mindbase-menubar-1.0.0-universal.tar.gz

# 3. Formula更新
# - url: GitHub Release URL
# - sha256: 計算値
# - version: タグから抽出

# 4. homebrew-tapにcommit & push
git commit -m "Update mindbase-menubar to menubar-v1.0.0"
git push
```

**必要なシークレット**:
- `TAP_GITHUB_TOKEN`: agiletec-inc/homebrew-tapへのwrite権限

### 4. ユーザーインストール

```bash
# 1. tap追加（初回のみ）
brew tap agiletec-inc/tap

# 2. インストール
brew install mindbase-menubar

# 3. 起動
open /Applications/MindBaseMenubar.app
```

## GitHub Actions設定

### release-menubar.yml

**トリガー**:
- タグpush: `menubar-v*.*.*`
- 手動実行: `workflow_dispatch`

**ジョブ**:

#### 1. build-and-release
- **runner**: `macos-15` (Apple Silicon + Xcode 16)
- **ステップ**:
  1. Swift Packageビルド（`scripts/build-menubar-app.sh`）
  2. .appバンドル検証（plutil, file）
  3. tarball作成
  4. SHA256計算
  5. GitHub Release作成

#### 2. update-homebrew-tap
- **runner**: `ubuntu-latest`
- **ステップ**:
  1. homebrew-tapチェックアウト
  2. リリースtarballダウンロード
  3. Formula更新（url, sha256, version）
  4. commit & push

### 必要なシークレット

GitHub Repository Settings → Secrets and variables → Actions:

```yaml
TAP_GITHUB_TOKEN:
  description: Personal Access Token for agiletec-inc/homebrew-tap
  permissions:
    - repo (full)
    - workflow (optional)
  scopes: public_repo
```

**作成方法**:
1. GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. `Generate new token (classic)`
3. Scopes: `public_repo` にチェック
4. `Generate token`
5. トークンをコピー
6. mindbaseリポジトリ Settings → Secrets → New repository secret
7. Name: `TAP_GITHUB_TOKEN`, Value: 貼り付け

## トラブルシューティング

### ビルドエラー: Xcode not found

```bash
# ローカル確認
xcode-select -p
swift --version

# GitHub Actions: setup-xcode@v1で解決済み
```

### Formula更新失敗: Permission denied

```bash
# TAP_GITHUB_TOKENのpermissions確認
# - repo: フル権限が必要
# - Fine-grained tokenは未対応（classic tokenを使用）
```

### brew install失敗: SHA256 mismatch

```bash
# 1. GitHub Release tarball再確認
curl -L "https://github.com/agiletec-inc/mindbase/releases/download/menubar-v1.0.0/mindbase-menubar-1.0.0-universal.tar.gz" -o test.tar.gz
shasum -a 256 test.tar.gz

# 2. Formula修正（手動）
cd ~/github/homebrew-tap
vim Formula/mindbase-menubar.rb
# sha256 "正しい値"
git commit -am "Fix SHA256 for mindbase-menubar"
git push
```

### アプリ起動エラー: Permission denied

```bash
# Gatekeeper対策（開発版のみ）
xattr -cr /Applications/MindBaseMenubar.app

# 本番: Code Signingが必要（将来実装）
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Agiletec Inc" \
  MindBaseMenubar.app
```

## ローカル開発

### ビルド＆テストサイクル

```bash
# 1. コード変更
vim apps/menubar-swift/Sources/MindBaseMenubar/ChatWindow.swift

# 2. クリーンビルド
make menubar-clean
make menubar-build

# 3. 起動確認
make menubar-run

# 4. インストールテスト（オプション）
make menubar-install
open /Applications/MindBaseMenubar.app
```

### Xcodeでのデバッグ（代替）

```bash
cd apps/menubar-swift
swift package generate-xcodeproj
open MindBaseMenubar.xcodeproj
```

注意: Xcodeプロジェクトは.gitignore済み（自動生成可能）

## バージョン管理戦略

### セマンティックバージョニング

```
menubar-v{MAJOR}.{MINOR}.{PATCH}

MAJOR: 破壊的変更（API変更、macOS要件変更）
MINOR: 新機能追加（後方互換）
PATCH: バグ修正
```

### 例

```
menubar-v1.0.0 - 初回リリース
menubar-v1.1.0 - Chat機能追加
menubar-v1.1.1 - Auto-collection修正
menubar-v2.0.0 - macOS 14サポート削除（破壊的変更）
```

## 今後の改善

### Code Signing（公式リリース時）

```bash
# Developer ID取得
# https://developer.apple.com/developer-id/

# 署名
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Agiletec Inc" \
  --options runtime \
  MindBaseMenubar.app

# Notarization
xcrun notarytool submit MindBaseMenubar.app.zip \
  --apple-id "your@email.com" \
  --password "@keychain:AC_PASSWORD" \
  --team-id "YOUR_TEAM_ID"
```

### Universal Binary対応確認

現在: Apple Siliconのみ対応（`swift build`がarm64）
将来: Lipo経由でIntel x86_64も含める

```bash
# Intel + Apple Silicon
lipo -create \
  .build/arm64-apple-macosx/release/MindBaseMenubar \
  .build/x86_64-apple-macosx/release/MindBaseMenubar \
  -output MindBaseMenubar-universal
```

### CI/CDパイプライン強化

- [ ] 自動テスト（Unit test + UI test）
- [ ] スクリーンショット自動生成
- [ ] リリースノート自動生成（conventional commits）
- [ ] Homebrew audit自動化

## 参考資料

### Apple公式ドキュメント

- [Bundle Programming Guide](https://developer.apple.com/library/archive/documentation/CoreFoundation/Conceptual/CFBundles/)
- [Info.plist Key Reference](https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/)
- [Code Signing Guide](https://developer.apple.com/documentation/xcode/code-signing-guide)

### Homebrew

- [Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Cask Cookbook](https://docs.brew.sh/Cask-Cookbook)
- [Creating Taps](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap)

### GitHub Actions

- [setup-xcode](https://github.com/maxim-lobanov/setup-xcode)
- [action-gh-release](https://github.com/softprops/action-gh-release)

---

**Last Updated**: 2025-01-21
**Maintainer**: Agiletec Inc.
