//! Routes user intent to a DAG of agents/skills.

use crate::error::EngineResult;
use serde::{Deserialize, Serialize};

/// A decision about how to route a user request through the agent/skill DAG.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingDecision {
    pub dag: Vec<DagNode>,
    pub rationale: String,
    pub confidence: f64,
}

/// A single node in the execution DAG.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DagNode {
    pub id: String,
    pub kind: NodeKind,
    pub name: String,
    pub depends_on: Vec<String>,
    pub inputs: serde_json::Value,
}

/// The type of a DAG node.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NodeKind {
    Expert,
    Skill,
    Script,
}

/// Trait for routing user intent to a DAG of agents and skills.
pub trait IntentRouter: Send + Sync {
    /// Analyze a user request and produce a routing decision.
    fn route(&self, intent: &str) -> EngineResult<RoutingDecision>;
}
