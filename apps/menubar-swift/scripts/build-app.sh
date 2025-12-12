#!/bin/bash
# Build MindBase apps from Swift Package Manager project
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_DIR}/.build"

# Default output directory
OUTPUT_DIR="${1:-${PROJECT_DIR}/build}"

echo "Building MindBase apps..."
echo "Project: ${PROJECT_DIR}"
echo "Output: ${OUTPUT_DIR}"

cd "$PROJECT_DIR"

# Build both targets
swift build --configuration release

mkdir -p "$OUTPUT_DIR"

# Function to create .app bundle
create_app_bundle() {
    local EXECUTABLE_NAME=$1
    local APP_NAME=$2
    local INFO_PLIST=$3

    echo ""
    echo "Creating ${APP_NAME}..."

    local APP_BUNDLE="${OUTPUT_DIR}/${APP_NAME}"
    rm -rf "$APP_BUNDLE"
    mkdir -p "${APP_BUNDLE}/Contents/MacOS"
    mkdir -p "${APP_BUNDLE}/Contents/Resources"

    # Copy executable
    cp "${BUILD_DIR}/release/${EXECUTABLE_NAME}" "${APP_BUNDLE}/Contents/MacOS/"

    # Copy Info.plist
    cp "${PROJECT_DIR}/Resources/${INFO_PLIST}" "${APP_BUNDLE}/Contents/Info.plist"

    # Copy icon if exists
    if [ -f "${PROJECT_DIR}/Resources/AppIcon.icns" ]; then
        cp "${PROJECT_DIR}/Resources/AppIcon.icns" "${APP_BUNDLE}/Contents/Resources/"
    fi

    # Create PkgInfo
    echo -n "APPL????" > "${APP_BUNDLE}/Contents/PkgInfo"

    # Sign the app (ad-hoc for local use)
    codesign --force --deep --sign - "$APP_BUNDLE" 2>/dev/null || true

    echo "  Created: ${APP_BUNDLE}"
}

# Build MindBase Menubar (menu bar app)
create_app_bundle "MindBaseMenubar" "MindBase.app" "Info.plist"

# Build MindBase Chat (standalone chat app)
create_app_bundle "MindBaseChat" "MindBase Chat.app" "ChatInfo.plist"

echo ""
echo "Build complete!"
echo ""
echo "Apps created:"
echo "  ${OUTPUT_DIR}/MindBase.app (menubar)"
echo "  ${OUTPUT_DIR}/MindBase Chat.app (chat)"
echo ""
echo "To install to ~/Applications:"
echo "  cp -r '${OUTPUT_DIR}/MindBase.app' ~/Applications/"
echo "  cp -r '${OUTPUT_DIR}/MindBase Chat.app' ~/Applications/"
