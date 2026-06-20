# Homebrew Formula for Test-Agent V2.0.0
# Install: brew install Wool-xing/test-agent/test-agent
# Or locally: brew install --build-from-source ./deploy/marketplace/test-agent.rb

class TestAgent < Formula
  include Language::Python::Virtualenv

  desc "AI-powered multi-platform test framework — describe tests in natural language"
  homepage "https://github.com/Wool-xing/Test-Agent"
  url "https://github.com/Wool-xing/Test-Agent/archive/refs/tags/v2.0.0.tar.gz"
  sha256 "PLACEHOLDER_REPLACE_WITH_ACTUAL_SHA256_AFTER_RELEASE"
  license "MIT"
  version "2.0.0"

  depends_on "python@3.12"

  resource "typer" do
    url "https://files.pythonhosted.org/packages/source/t/typer/typer-0.15.2.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources
    bin.install_symlink libexec/"bin/tagent"
  end

  test do
    system "#{bin}/tagent", "--version"
  end
end
