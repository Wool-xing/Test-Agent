use pyo3::prelude::*;

use tagent_engine::orchestrator::ExecNode;
use tagent_engine::sandbox::{PlatformSandbox, SandboxConfig};

// ---------------------------------------------------------------------------
// Python-facing sandbox wrappers
// ---------------------------------------------------------------------------

/// Python-exposed sandbox configuration.
#[pyclass(name = "SandboxConfig")]
#[derive(Clone)]
struct PySandboxConfig {
    inner: SandboxConfig,
}

#[pymethods]
impl PySandboxConfig {
    #[new]
    fn new(workspace: String, allow_network: bool, allow_write_outside: bool) -> Self {
        Self {
            inner: SandboxConfig {
                workspace: std::path::PathBuf::from(&workspace),
                allow_network,
                allow_write_outside_workspace: allow_write_outside,
                allowed_commands: vec![],
            },
        }
    }

    fn set_allowed_commands(&mut self, commands: Vec<String>) {
        self.inner.allowed_commands = commands;
    }

    fn __repr__(&self) -> String {
        format!(
            "SandboxConfig(workspace='{}', allow_network={}, allow_write_outside={})",
            self.inner.workspace.display(),
            self.inner.allow_network,
            self.inner.allow_write_outside_workspace,
        )
    }
}

/// Python-exposed platform sandbox (wraps the Rust PlatformSandbox enum).
#[pyclass(name = "PlatformSandbox")]
struct PyPlatformSandbox {
    inner: PlatformSandbox,
}

#[pymethods]
impl PyPlatformSandbox {
    /// Auto-detect the current platform and create a sandbox.
    #[staticmethod]
    fn auto(config: &PySandboxConfig) -> Self {
        Self {
            inner: PlatformSandbox::auto(config.inner.clone()),
        }
    }

    fn lock_down(&mut self) -> PyResult<()> {
        self.inner
            .lock_down()
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }

    fn allow_network_access(&mut self, allow: bool) -> PyResult<()> {
        self.inner
            .allow_network_access(allow)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }

    fn restrict_path(&mut self, path: &str, write: bool) -> PyResult<()> {
        self.inner
            .restrict_path(path, write)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }

    fn is_active(&self) -> bool {
        self.inner.is_active()
    }

    fn __repr__(&self) -> String {
        format!("PlatformSandbox(active={})", self.is_active())
    }
}

// ---------------------------------------------------------------------------
// Python-facing DAG executor wrappers
// ---------------------------------------------------------------------------

/// Python-exposed execution node.
#[pyclass(name = "ExecNode")]
#[derive(Clone)]
struct PyExecNode {
    inner: ExecNode,
}

#[pymethods]
impl PyExecNode {
    #[new]
    fn new(id: String, kind: String, name: String, depends_on: Vec<String>, timeout_secs: u64) -> Self {
        Self {
            inner: ExecNode {
                id,
                kind,
                name,
                depends_on,
                timeout_secs,
            },
        }
    }

    #[getter]
    fn id(&self) -> &str {
        &self.inner.id
    }

    #[getter]
    fn kind(&self) -> &str {
        &self.inner.kind
    }

    fn __repr__(&self) -> String {
        format!(
            "ExecNode(id='{}', kind='{}', depends_on={:?})",
            self.inner.id, self.inner.kind, self.inner.depends_on
        )
    }
}

// ---------------------------------------------------------------------------
// Module definition
// ---------------------------------------------------------------------------

/// Python bindings for the tagent-engine core library.
#[pymodule]
fn tagent_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", "0.1.0")?;

    // Sandbox types
    m.add_class::<PySandboxConfig>()?;
    m.add_class::<PyPlatformSandbox>()?;

    // Orchestrator types
    m.add_class::<PyExecNode>()?;

    Ok(())
}
