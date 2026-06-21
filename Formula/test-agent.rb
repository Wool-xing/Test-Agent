# Homebrew formula for Test-Agent V2.0.0
# Usage: brew install ./Formula/test-agent.rb
# Or once published to a tap: brew install wool-xing/tap/test-agent

class TestAgent < Formula
  desc "AI-powered testing framework — natural language driven, multi-platform CLI + TUI"
  homepage "https://github.com/Wool-xing/Test-Agent"
  url "https://github.com/Wool-xing/Test-Agent/archive/refs/tags/v2.0.0.tar.gz"
  sha256 "PLACEHOLDER"  # Replace with actual sha256 on release
  license "MIT"
  version "2.0.0"

  depends_on "python@3.12"

  def install
    venv = libexec/"venv"
    system "python3", "-m", "venv", venv
    system venv/"bin/pip", "install", "-e", "."

    bin.install_symlink venv/"bin/tagent" => "tagent"
  end

  test do
    system "#{bin}/tagent", "--version"
  end
end
