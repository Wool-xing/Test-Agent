//! Platform-specific sandbox abstraction.
//!
//! Provides OS-level sandboxing via platform-native mechanisms:
//! - **Linux**: landlock + seccomp (planned)
//! - **macOS**: sandbox-exec / Seatbelt (planned)
//! - **Windows**: Job Objects (planned)
//!
//! Currently all platforms use stub implementations that record config
//! but do not enforce restrictions. The API surface is stable so callers
//! can integrate now and get enforcement later without code changes.

use std::path::PathBuf;

// ---------------------------------------------------------------------------
// Sandbox error (lightweight, no thiserror needed for this module)
// ---------------------------------------------------------------------------

/// Errors specific to sandbox operations.
#[derive(Debug)]
pub struct SandboxError {
    pub message: String,
}

impl std::fmt::Display for SandboxError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for SandboxError {}

impl From<SandboxError> for crate::error::EngineError {
    fn from(e: SandboxError) -> Self {
        crate::error::EngineError::Sandbox(e.message)
    }
}

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/// Unified sandbox configuration shared across all platforms.
#[derive(Debug, Clone)]
pub struct SandboxConfig {
    /// Root workspace directory — all file access is restricted to this tree.
    pub workspace: PathBuf,
    /// Whether outbound network access is permitted.
    pub allow_network: bool,
    /// Whether writes are permitted outside `workspace`.
    pub allow_write_outside_workspace: bool,
    /// Explicitly allowed shell commands (e.g. `["git", "python", "node"]`).
    pub allowed_commands: Vec<String>,
}

impl Default for SandboxConfig {
    fn default() -> Self {
        Self {
            workspace: PathBuf::from("."),
            allow_network: false,
            allow_write_outside_workspace: false,
            allowed_commands: vec![],
        }
    }
}

// ---------------------------------------------------------------------------
// Platform-specific implementations
// ---------------------------------------------------------------------------

/// Platform-specific sandbox.
///
/// Use `PlatformSandbox::auto(config)` to create the correct variant for the
/// current OS.
pub enum PlatformSandbox {
    #[cfg(target_os = "linux")]
    Linux(LinuxSandbox),
    #[cfg(target_os = "macos")]
    Macos(MacosSandbox),
    #[cfg(target_os = "windows")]
    Windows(WindowsSandbox),
}

impl PlatformSandbox {
    /// Auto-detect the current platform and create the appropriate sandbox.
    pub fn auto(config: SandboxConfig) -> Self {
        #[cfg(target_os = "linux")]
        {
            PlatformSandbox::Linux(LinuxSandbox::new(config))
        }
        #[cfg(target_os = "macos")]
        {
            PlatformSandbox::Macos(MacosSandbox::new(config))
        }
        #[cfg(target_os = "windows")]
        {
            PlatformSandbox::Windows(WindowsSandbox::new(config))
        }
    }

    /// Apply sandbox restrictions.
    pub fn lock_down(&self) -> Result<(), SandboxError> {
        match self {
            #[cfg(target_os = "linux")]
            PlatformSandbox::Linux(s) => s.lock_down(),
            #[cfg(target_os = "macos")]
            PlatformSandbox::Macos(s) => s.lock_down(),
            #[cfg(target_os = "windows")]
            PlatformSandbox::Windows(s) => s.lock_down(),
        }
    }

    /// Toggle network access after creation.
    pub fn allow_network_access(&mut self, allow: bool) -> Result<(), SandboxError> {
        match self {
            #[cfg(target_os = "linux")]
            PlatformSandbox::Linux(s) => s.allow_network_access(allow),
            #[cfg(target_os = "macos")]
            PlatformSandbox::Macos(s) => s.allow_network_access(allow),
            #[cfg(target_os = "windows")]
            PlatformSandbox::Windows(s) => s.allow_network_access(allow),
        }
    }

    /// Restrict (or unrestrict) a filesystem path.
    pub fn restrict_path(&mut self, path: &str, write: bool) -> Result<(), SandboxError> {
        match self {
            #[cfg(target_os = "linux")]
            PlatformSandbox::Linux(s) => s.restrict_path(path, write),
            #[cfg(target_os = "macos")]
            PlatformSandbox::Macos(s) => s.restrict_path(path, write),
            #[cfg(target_os = "windows")]
            PlatformSandbox::Windows(s) => s.restrict_path(path, write),
        }
    }

    /// Returns true if the sandbox is currently enforcing restrictions.
    pub fn is_active(&self) -> bool {
        match self {
            #[cfg(target_os = "linux")]
            PlatformSandbox::Linux(s) => s.is_active(),
            #[cfg(target_os = "macos")]
            PlatformSandbox::Macos(s) => s.is_active(),
            #[cfg(target_os = "windows")]
            PlatformSandbox::Windows(s) => s.is_active(),
        }
    }
}

// ---------------------------------------------------------------------------
// Linux (landlock + seccomp — stubbed)
// ---------------------------------------------------------------------------

#[cfg(target_os = "linux")]
#[derive(Debug, Clone)]
pub struct LinuxSandbox {
    config: SandboxConfig,
    active: bool,
}

#[cfg(target_os = "linux")]
impl LinuxSandbox {
    pub fn new(config: SandboxConfig) -> Self {
        Self {
            config,
            active: false,
        }
    }

    pub fn lock_down(&self) -> Result<(), SandboxError> {
        // TODO: Apply landlock ruleset for filesystem restrictions
        // TODO: Apply seccomp-bpf filter for syscall allowlist
        let _ = &self.config;
        Ok(())
    }

    pub fn allow_network_access(&mut self, allow: bool) -> Result<(), SandboxError> {
        // TODO: Update seccomp filter to allow/deny socket syscalls
        self.config.allow_network = allow;
        Ok(())
    }

    pub fn restrict_path(&mut self, _path: &str, _write: bool) -> Result<(), SandboxError> {
        // TODO: Add landlock access rule for path
        Ok(())
    }

    pub fn is_active(&self) -> bool {
        self.active
    }
}

// ---------------------------------------------------------------------------
// macOS (sandbox-exec / Seatbelt — stubbed)
// ---------------------------------------------------------------------------

#[cfg(target_os = "macos")]
#[derive(Debug, Clone)]
pub struct MacosSandbox {
    config: SandboxConfig,
    active: bool,
}

#[cfg(target_os = "macos")]
impl MacosSandbox {
    pub fn new(config: SandboxConfig) -> Self {
        Self {
            config,
            active: false,
        }
    }

    pub fn lock_down(&self) -> Result<(), SandboxError> {
        // TODO: Generate and apply a Seatbelt profile via sandbox-exec
        let _ = &self.config;
        Ok(())
    }

    pub fn allow_network_access(&mut self, allow: bool) -> Result<(), SandboxError> {
        self.config.allow_network = allow;
        Ok(())
    }

    pub fn restrict_path(&mut self, _path: &str, _write: bool) -> Result<(), SandboxError> {
        Ok(())
    }

    pub fn is_active(&self) -> bool {
        self.active
    }
}

// ---------------------------------------------------------------------------
// Windows (Job Objects — stubbed)
// ---------------------------------------------------------------------------

#[cfg(target_os = "windows")]
#[derive(Debug, Clone)]
pub struct WindowsSandbox {
    config: SandboxConfig,
    active: bool,
}

#[cfg(target_os = "windows")]
impl WindowsSandbox {
    pub fn new(config: SandboxConfig) -> Self {
        Self {
            config,
            active: false,
        }
    }

    pub fn lock_down(&self) -> Result<(), SandboxError> {
        // TODO: Create a Job Object with resource limits and restrictions
        let _ = &self.config;
        Ok(())
    }

    pub fn allow_network_access(&mut self, allow: bool) -> Result<(), SandboxError> {
        self.config.allow_network = allow;
        Ok(())
    }

    pub fn restrict_path(&mut self, _path: &str, _write: bool) -> Result<(), SandboxError> {
        Ok(())
    }

    pub fn is_active(&self) -> bool {
        self.active
    }
}

// ---------------------------------------------------------------------------
// Noop sandbox (convenience fallback)
// ---------------------------------------------------------------------------

/// A no-op sandbox that allows everything — used when sandboxing is disabled.
pub struct NoopSandbox;

impl NoopSandbox {
    pub fn lock_down(&self) -> Result<(), SandboxError> {
        Ok(())
    }

    pub fn allow_network_access(&mut self, _allow: bool) -> Result<(), SandboxError> {
        Ok(())
    }

    pub fn restrict_path(&mut self, _path: &str, _write: bool) -> Result<(), SandboxError> {
        Ok(())
    }

    pub fn is_active(&self) -> bool {
        false
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = SandboxConfig::default();
        assert_eq!(config.workspace, PathBuf::from("."));
        assert!(!config.allow_network);
        assert!(!config.allow_write_outside_workspace);
        assert!(config.allowed_commands.is_empty());
    }

    #[test]
    fn test_platform_sandbox_auto_creates() {
        let config = SandboxConfig {
            workspace: PathBuf::from("/tmp/test-workspace"),
            allow_network: true,
            allow_write_outside_workspace: false,
            allowed_commands: vec!["git".into(), "python".into()],
        };

        let mut sandbox = PlatformSandbox::auto(config);
        // All stub implementations start inactive
        assert!(!sandbox.is_active());

        // lock_down should succeed (stub)
        sandbox.lock_down().unwrap();

        // allow_network_access should update config
        sandbox.allow_network_access(false).unwrap();
        assert!(!sandbox.is_active()); // stubs don't activate

        // restrict_path should succeed
        sandbox.restrict_path("/tmp/extra", true).unwrap();
    }

    #[test]
    fn test_noop_sandbox() {
        let mut s = NoopSandbox;
        assert!(!s.is_active());
        s.lock_down().unwrap();
        s.allow_network_access(true).unwrap();
        s.restrict_path("/anything", true).unwrap();
    }

    #[test]
    fn test_sandbox_error_display() {
        let err = SandboxError {
            message: "test error".into(),
        };
        assert_eq!(err.to_string(), "test error");
    }

    #[test]
    fn test_sandbox_error_into_engine_error() {
        let err = SandboxError {
            message: "sandbox failed".into(),
        };
        let engine_err: crate::error::EngineError = err.into();
        assert!(matches!(engine_err, crate::error::EngineError::Sandbox(_)));
        assert_eq!(engine_err.to_string(), "sandbox error: sandbox failed");
    }
}
