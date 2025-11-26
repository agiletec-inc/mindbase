#!/bin/bash
set -euo pipefail

# Build macOS .app bundle for MindBase Menubar
# This script creates a proper macOS application bundle from Swift Package Manager executable
# Reference: Apple Bundle Programming Guide
# https://developer.apple.com/library/archive/documentation/CoreFoundation/Conceptual/CFBundles/BundleTypes/BundleTypes.html

APP_NAME="MindBaseMenubar"
BUNDLE_ID="com.agiletec.mindbase-menubar"
VERSION="${VERSION:-1.0.0}"
CONFIGURATION="${CONFIGURATION:-release}"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SWIFT_PACKAGE_DIR="$REPO_ROOT/apps/menubar-swift"
BUILD_DIR="$REPO_ROOT/build"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"

echo "🔨 Building MindBase Menubar App..."
echo "   App Name: $APP_NAME"
echo "   Bundle ID: $BUNDLE_ID"
echo "   Version: $VERSION"
echo "   Configuration: $CONFIGURATION"
echo ""

# 1. Build Swift executable
echo "📦 Building Swift executable..."
swift build \
    --package-path "$SWIFT_PACKAGE_DIR" \
    --configuration "$CONFIGURATION" \
    --disable-sandbox

EXECUTABLE_PATH="$SWIFT_PACKAGE_DIR/.build/$CONFIGURATION/$APP_NAME"
if [ ! -f "$EXECUTABLE_PATH" ]; then
    echo "❌ Error: Executable not found at $EXECUTABLE_PATH"
    exit 1
fi
echo "✅ Executable built: $EXECUTABLE_PATH"
echo ""

# 2. Create .app bundle structure
echo "📁 Creating .app bundle structure..."
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"
echo "✅ Bundle structure created: $APP_BUNDLE"
echo ""

# 3. Copy executable
echo "📋 Copying executable to bundle..."
cp "$EXECUTABLE_PATH" "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
chmod +x "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
echo "✅ Executable copied"
echo ""

# 4. Generate Info.plist
echo "📝 Generating Info.plist..."
cat > "$APP_BUNDLE/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>

    <key>CFBundlePackageType</key>
    <string>APPL</string>

    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>

    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>

    <key>CFBundleName</key>
    <string>$APP_NAME</string>

    <key>CFBundleDisplayName</key>
    <string>MindBase Menubar</string>

    <key>CFBundleVersion</key>
    <string>$VERSION</string>

    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>

    <key>LSMinimumSystemVersion</key>
    <string>15.0</string>

    <key>LSUIElement</key>
    <true/>

    <key>NSPrincipalClass</key>
    <string>NSApplication</string>

    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF
echo "✅ Info.plist generated"
echo ""

# 5. Verify bundle structure
echo "🔍 Verifying bundle structure..."
REQUIRED_FILES=(
    "$APP_BUNDLE/Contents/Info.plist"
    "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
)

ALL_VALID=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -e "$file" ]; then
        echo "❌ Missing: $file"
        ALL_VALID=false
    else
        echo "✅ Found: $file"
    fi
done

if [ "$ALL_VALID" = false ]; then
    echo ""
    echo "❌ Bundle validation failed"
    exit 1
fi

echo ""
echo "✅ Bundle validation passed"
echo ""

# 6. Display bundle info
echo "📊 Bundle Information:"
echo "   Path: $APP_BUNDLE"
echo "   Size: $(du -sh "$APP_BUNDLE" | cut -f1)"
echo "   Executable: $(file "$APP_BUNDLE/Contents/MacOS/$APP_NAME" | cut -d: -f2)"
echo ""

# 7. Success message
echo "🎉 Build completed successfully!"
echo ""
echo "To launch the app:"
echo "   open \"$APP_BUNDLE\""
echo ""
echo "To install to /Applications:"
echo "   cp -r \"$APP_BUNDLE\" /Applications/"
echo ""
