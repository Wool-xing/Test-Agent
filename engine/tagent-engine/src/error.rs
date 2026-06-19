use thiserror::Error;

#[derive(Error, Debug)]
pub enum EngineError {
    #[error("routing error: {0}")]
    Routing(String),

    #[error("orchestration error: {0}")]
    Orchestration(String),

    #[error("graph error: {0}")]
    Graph(String),

    #[error("sandbox error: {0}")]
    Sandbox(String),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("serialization error: {0}")]
    Serde(#[from] serde_json::Error),

    #[error("internal error: {0}")]
    Internal(String),
}

pub type EngineResult<T> = Result<T, EngineError>;
