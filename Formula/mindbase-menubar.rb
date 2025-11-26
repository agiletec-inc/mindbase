class MindbaseMenubar < Formula
  desc "MindBase Menubar - Auto-collection companion for AI conversations"
  homepage "https://github.com/agiletec-inc/mindbase"
  url "https://github.com/agiletec-inc/mindbase/releases/download/menubar-v1.0.0/mindbase-menubar-1.0.0-universal.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  version "1.0.0"
  license "MIT"

  depends_on :macos

  def install
    # Pre-built .app bundle from GitHub Release
    # No build required - just extract and install
    prefix.install "MindBaseMenubar.app"
  end

  def post_install
    # Create symlink to /Applications for easy access
    system "ln", "-sf", "#{prefix}/MindBaseMenubar.app", "/Applications/MindBaseMenubar.app"
  end

  def caveats
    <<~EOS
      MindBase Menubar has been installed!

      To launch it:
        open /Applications/MindBaseMenubar.app

      Or from the command line:
        open "#{prefix}/MindBaseMenubar.app"

      To add to Login Items (auto-start at login):
        1. Open System Settings
        2. Go to General → Login Items
        3. Click "+" and select "MindBaseMenubar.app"

      Prerequisites:
        - MindBase API must be running (brew install agiletec-inc/tap/mindbase)
        - Ollama with qwen2.5:3b model installed

      Quick Start:
        # Start MindBase API
        brew services start mindbase

        # Launch menubar app
        open /Applications/MindBaseMenubar.app
    EOS
  end

  def uninstall_postflight
    # Remove symlink on uninstall
    system "rm", "-f", "/Applications/MindBaseMenubar.app"
  end

  test do
    assert_predicate prefix/"MindBaseMenubar.app", :exist?
    assert_predicate prefix/"MindBaseMenubar.app/Contents/Info.plist", :exist?
    assert_predicate prefix/"MindBaseMenubar.app/Contents/MacOS/MindBaseMenubar", :exist?
  end
end
