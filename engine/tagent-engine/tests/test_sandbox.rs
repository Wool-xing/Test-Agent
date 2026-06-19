//! Integration tests for the platform sandbox.
//!
//! Tests sandbox configuration, platform auto-detection, and the noop fallback.

use std::path::PathBuf;

use tagent_engine::sandbox::{NoopSandbox, PlatformSandbox, SandboxConfig, SandboxError};

// ---------------------------------------------------------------------------
// SandboxConfig tests
// ---------------------------------------------------------------------------

#[test]
fn test_sandbox_config_defaults() {
    let config = SandboxConfig::default();
    assert_eq!(config.workspace, PathBuf::from("."));
    assert!(!config.allow_network);
    assert!(!config.allow_write_outside_workspace);
    assert!(config.allowed_commands.is_empty());
}

#[test]
fn test_sandbox_config_custom() {
    let config = SandboxConfig {
        workspace: PathBuf::from("/home/user/project"),
        allow_network: true,
        allow_write_outside_workspace: false,
        allowed_commands: vec!["git".into(), "python".into(), "cargo".into()],
    };

    assert_eq!(config.workspace, PathBuf::from("/home/user/project"));
    assert!(config.allow_network);
    assert!(!config.allow_write_outside_workspace);
    assert_eq!(config.allowed_commands.len(), 3);
    assert!(config.allowed_commands.contains(&"cargo".to_string()));
}

#[test]
fn test_sandbox_config_clone() {
    let config = SandboxConfig {
        workspace: PathBuf::from("/tmp"),
        allow_network: false,
        allow_write_outside_workspace: true,
        allowed_commands: vec!["ls".into()],
    };

    let cloned = config.clone();
    assert_eq!(cloned.workspace, PathBuf::from("/tmp"));
    assert_eq!(cloned.allowed_commands, vec!["ls"]);
}

// ---------------------------------------------------------------------------
// Platform auto-detection
// ---------------------------------------------------------------------------

#[test]
fn test_platform_sandbox_auto_creates_without_panic() {
    // auto() must never panic regardless of platform
    let config = SandboxConfig {
        workspace: PathBuf::from("/tmp/sandbox-test"),
        allow_network: true,
        allow_write_outside_workspace: false,
        allowed_commands: vec!["echo".into()],
    };

    let mut sandbox = PlatformSandbox::auto(config);
    assert!(!sandbox.is_active(), "new sandbox should be inactive");
}

#[test]
fn test_platform_sandbox_lock_down_succeeds() {
    let mut sandbox = PlatformSandbox::auto(SandboxConfig::default());
    sandbox.lock_down().unwrap();
    // lock_down succeeds on all stub implementations
}

#[test]
fn test_platform_sandbox_allow_network_access() {
    let mut sandbox = PlatformSandbox::auto(SandboxConfig::default());
    sandbox.allow_network_access(true).unwrap();
    sandbox.allow_network_access(false).unwrap();
    // should never panic or error
}

#[test]
fn test_platform_sandbox_restrict_path() {
    let mut sandbox = PlatformSandbox::auto(SandboxConfig::default());
    sandbox.restrict_path("/some/path", true).unwrap();
    sandbox.restrict_path("/some/path", false).unwrap();
    // should never panic or error
}

// ---------------------------------------------------------------------------
// Noop sandbox
// ---------------------------------------------------------------------------

#[test]
fn test_noop_sandbox_never_active() {
    let mut s = NoopSandbox;
    assert!(!s.is_active());
    s.lock_down().unwrap();
    assert!(!s.is_active()); // noop never activates
}

#[test]
fn test_noop_sandbox_all_operations_succeed() {
    let mut s = NoopSandbox;

    s.lock_down().unwrap();
    s.allow_network_access(true).unwrap();
    s.allow_network_access(false).unwrap();
    s.restrict_path("/any/path", true).unwrap();
    s.restrict_path("/other/path", false).unwrap();

    // All succeeded without panicking
}

// ---------------------------------------------------------------------------
// SandboxError
// ---------------------------------------------------------------------------

#[test]
fn test_sandbox_error_display() {
    let err = SandboxError {
        message: "something went wrong".into(),
    };
    assert_eq!(err.to_string(), "something went wrong");
}

#[test]
fn test_sandbox_error_is_std_error() {
    let err = SandboxError {
        message: "test".into(),
    };
    // SandboxError implements std::error::Error
    let _: &dyn std::error::Error = &err;
}

#[test]
fn test_sandbox_error_into_engine_error() {
    let err = SandboxError {
        message: "lockdown failed".into(),
    };
    let engine_err: tagent_engine::error::EngineError = err.into();

    let msg = engine_err.to_string();
    assert!(msg.contains("sandbox error"));
    assert!(msg.contains("lockdown failed"));
}

#[test]
fn test_sandbox_config_debug_format() {
    let config = SandboxConfig {
        workspace: PathBuf::from("/test"),
        allow_network: true,
        allow_write_outside_workspace: false,
        allowed_commands: vec!["cmd".into()],
    };
    let debug_str = format!("{:?}", config);
    assert!(debug_str.contains("/test"));
    assert!(debug_str.contains("allow_network"));
}
