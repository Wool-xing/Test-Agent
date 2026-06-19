//! DAG executor with topological sort and parallel branch execution.
//!
//! Uses petgraph's toposort to determine execution order, then runs
//! independent branches concurrently via tokio::spawn. A circuit breaker
//! halts execution after `max_failures` node errors.

use petgraph::algo::toposort;
use petgraph::graph::DiGraph;
use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};

use crate::error::{EngineError, EngineResult};

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

/// A node in the execution DAG.
#[derive(Debug, Clone, serde::Deserialize, serde::Serialize)]
pub struct ExecNode {
    pub id: String,
    /// "expert", "skill", or "script"
    pub kind: String,
    pub name: String,
    pub depends_on: Vec<String>,
    /// Per-node timeout in seconds (0 = inherit from executor default)
    pub timeout_secs: u64,
}

/// Result of executing a single node.
#[derive(Debug, Clone)]
pub struct NodeResult {
    pub node_id: String,
    pub ok: bool,
    pub output: serde_json::Value,
    /// True when the node completed but with degraded quality.
    pub degraded: bool,
    pub error: Option<String>,
}

// ---------------------------------------------------------------------------
// Execution context
// ---------------------------------------------------------------------------

/// Thread-safe context passed through a DAG run.
pub struct ExecContext {
    pub run_id: String,
    results: Mutex<HashMap<String, NodeResult>>,
    circuit_broken: Mutex<bool>,
}

impl ExecContext {
    pub fn new(run_id: &str) -> Self {
        Self {
            run_id: run_id.to_string(),
            results: Mutex::new(HashMap::new()),
            circuit_broken: Mutex::new(false),
        }
    }

    /// Store a node's result so dependents can inspect it.
    pub fn store_result(&self, result: NodeResult) {
        let mut map = self.results.lock().unwrap();
        map.insert(result.node_id.clone(), result);
    }

    /// Retrieve a previously stored result.
    pub fn get_result(&self, node_id: &str) -> Option<NodeResult> {
        let map = self.results.lock().unwrap();
        map.get(node_id).cloned()
    }

    /// Check whether a dependency completed in a degraded state.
    pub fn is_degraded(&self, node_id: &str) -> bool {
        let map = self.results.lock().unwrap();
        map.get(node_id).map(|r| r.degraded).unwrap_or(false)
    }

    /// Trip the circuit breaker — no further nodes will be dispatched.
    pub fn break_circuit(&self) {
        let mut broken = self.circuit_broken.lock().unwrap();
        *broken = true;
    }

    /// Check whether the circuit breaker has been tripped.
    pub fn is_circuit_broken(&self) -> bool {
        *self.circuit_broken.lock().unwrap()
    }
}

// ---------------------------------------------------------------------------
// Node runner trait
// ---------------------------------------------------------------------------

/// Executes individual nodes. Python implementations are wired through PyO3.
pub trait NodeRunner: Send + Sync {
    fn run_node(&self, node: &ExecNode, ctx: &ExecContext) -> NodeResult;
}

// ---------------------------------------------------------------------------
// DAG executor
// ---------------------------------------------------------------------------

/// Topological DAG executor with parallel branch dispatch and circuit breaker.
pub struct DagExecutor {
    /// Circuit breaker trips after this many node failures (default 3).
    max_failures: usize,
    /// Maximum sub-agent nesting depth (default 3).
    max_depth: usize,
}

impl DagExecutor {
    pub fn new(max_failures: usize, max_depth: usize) -> Self {
        Self {
            max_failures,
            max_depth,
        }
    }

    /// Execute a DAG.
    ///
    /// Nodes are topologically sorted. Independent nodes at the same depth
    /// are spawned concurrently via `tokio::spawn`. The circuit breaker
    /// halts execution after `max_failures` node errors.
    pub async fn execute(
        &self,
        nodes: Vec<ExecNode>,
        runner: Arc<dyn NodeRunner>,
    ) -> EngineResult<Vec<NodeResult>> {
        let _max_depth = self.max_depth; // reserved for sub-agent nesting checks

        // Build petgraph DAG -------------------------------------------------
        let mut graph: DiGraph<ExecNode, ()> = DiGraph::new();
        let mut node_idx: HashMap<String, petgraph::graph::NodeIndex> = HashMap::new();

        for node in &nodes {
            let idx = graph.add_node(node.clone());
            node_idx.insert(node.id.clone(), idx);
        }

        for node in &nodes {
            let target = node_idx[&node.id];
            for dep in &node.depends_on {
                let source = node_idx.get(dep).ok_or_else(|| {
                    EngineError::Graph(format!(
                        "dependency '{}' (needed by '{}') not found in DAG",
                        dep, node.id
                    ))
                })?;
                graph.add_edge(*source, target, ());
            }
        }

        // Topological sort ---------------------------------------------------
        let sorted = toposort(&graph, None).map_err(|e| {
            EngineError::Graph(format!("DAG contains a cycle: {:?}", e))
        })?;

        let ordered: Vec<&ExecNode> =
            sorted.iter().map(|idx| graph.node_weight(*idx).unwrap()).collect();

        // Execution context --------------------------------------------------
        let ctx = Arc::new(ExecContext::new("dag-run"));
        let failures = Arc::new(Mutex::new(0usize));
        let max_failures = self.max_failures;

        let mut completed: HashSet<String> = HashSet::new();
        let pending: HashSet<String> = nodes.iter().map(|n| n.id.clone()).collect();
        let mut results: Vec<NodeResult> = Vec::new();

        // Wave-by-wave execution ---------------------------------------------
        while completed.len() < pending.len() {
            if ctx.is_circuit_broken() {
                break;
            }

            // Collect nodes whose dependencies are all satisfied
            let ready: Vec<&ExecNode> = ordered
                .iter()
                .filter(|n| {
                    !completed.contains(&n.id)
                        && n.depends_on.iter().all(|d| completed.contains(d))
                })
                .copied()
                .collect();

            if ready.is_empty() {
                break; // no progress — guard against orphaned nodes
            }

            // Spawn each ready node concurrently in its own task
            let mut handles = Vec::new();

            for node in &ready {
                let node = (*node).clone();
                let runner = Arc::clone(&runner);
                let ctx = Arc::clone(&ctx);
                let failures = Arc::clone(&failures);

                let handle = tokio::spawn(async move {
                    if ctx.is_circuit_broken() {
                        return None; // circuit already broken, skip
                    }

                    let result = runner.run_node(&node, &ctx);
                    let failed = !result.ok;

                    if failed {
                        let mut count = failures.lock().unwrap();
                        *count += 1;
                        if *count >= max_failures {
                            ctx.break_circuit();
                        }
                    }

                    Some(result)
                });

                handles.push(handle);
            }

            // Collect results from this wave
            for handle in handles {
                if let Ok(Some(result)) = handle.await {
                    ctx.store_result(result.clone());
                    completed.insert(result.node_id.clone());
                    results.push(result);
                }
                // If handle returned None (circuit broken mid-wave), skip
            }
        }

        Ok(results)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    /// A mock runner that always succeeds, returning the node id as output.
    struct MockRunner;

    impl NodeRunner for MockRunner {
        fn run_node(&self, node: &ExecNode, _ctx: &ExecContext) -> NodeResult {
            NodeResult {
                node_id: node.id.clone(),
                ok: true,
                output: serde_json::Value::String(node.id.clone()),
                degraded: false,
                error: None,
            }
        }
    }

    struct FailingRunner {
        fail_ids: HashSet<String>,
    }

    impl NodeRunner for FailingRunner {
        fn run_node(&self, node: &ExecNode, _ctx: &ExecContext) -> NodeResult {
            if self.fail_ids.contains(&node.id) {
                NodeResult {
                    node_id: node.id.clone(),
                    ok: false,
                    output: serde_json::Value::Null,
                    degraded: false,
                    error: Some(format!("{} failed", node.id)),
                }
            } else {
                NodeResult {
                    node_id: node.id.clone(),
                    ok: true,
                    output: serde_json::Value::String(node.id.clone()),
                    degraded: false,
                    error: None,
                }
            }
        }
    }

    fn make_nodes() -> Vec<ExecNode> {
        vec![
            ExecNode {
                id: "A".into(),
                kind: "expert".into(),
                name: "Node A".into(),
                depends_on: vec![],
                timeout_secs: 30,
            },
            ExecNode {
                id: "B".into(),
                kind: "skill".into(),
                name: "Node B".into(),
                depends_on: vec!["A".into()],
                timeout_secs: 30,
            },
            ExecNode {
                id: "C".into(),
                kind: "script".into(),
                name: "Node C".into(),
                depends_on: vec!["A".into()],
                timeout_secs: 30,
            },
            ExecNode {
                id: "D".into(),
                kind: "expert".into(),
                name: "Node D".into(),
                depends_on: vec!["B".into(), "C".into()],
                timeout_secs: 30,
            },
        ]
    }

    #[tokio::test]
    async fn test_linear_dag_executes_all() {
        let nodes = make_nodes();
        let executor = DagExecutor::new(3, 3);
        let runner = Arc::new(MockRunner);

        let results = executor.execute(nodes, runner).await.unwrap();
        assert_eq!(results.len(), 4);
        assert!(results.iter().all(|r| r.ok));
    }

    #[tokio::test]
    async fn test_circuit_breaker_trips() {
        let nodes = make_nodes();
        let executor = DagExecutor::new(1, 3); // trip after 1 failure

        let mut fail_ids = HashSet::new();
        fail_ids.insert("A".into());
        let runner = Arc::new(FailingRunner { fail_ids });

        let results = executor.execute(nodes, runner).await.unwrap();
        // A fails, circuit breaks — B, C, D should not run
        let executed_ids: HashSet<&str> = results.iter().map(|r| r.node_id.as_str()).collect();
        assert!(executed_ids.contains("A"));
        assert!(!executed_ids.contains("B"));
        assert!(!executed_ids.contains("C"));
        assert!(!executed_ids.contains("D"));
    }

    #[tokio::test]
    async fn test_cycle_detection() {
        let nodes = vec![
            ExecNode {
                id: "X".into(),
                kind: "expert".into(),
                name: "Node X".into(),
                depends_on: vec!["Y".into()],
                timeout_secs: 30,
            },
            ExecNode {
                id: "Y".into(),
                kind: "expert".into(),
                name: "Node Y".into(),
                depends_on: vec!["X".into()],
                timeout_secs: 30,
            },
        ];

        let executor = DagExecutor::new(3, 3);
        let runner = Arc::new(MockRunner);
        let result = executor.execute(nodes, runner).await;
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("cycle"));
    }

    #[tokio::test]
    async fn test_missing_dependency() {
        let nodes = vec![ExecNode {
            id: "Z".into(),
            kind: "expert".into(),
            name: "Node Z".into(),
            depends_on: vec!["NONEXISTENT".into()],
            timeout_secs: 30,
        }];

        let executor = DagExecutor::new(3, 3);
        let runner = Arc::new(MockRunner);
        let result = executor.execute(nodes, runner).await;
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("not found"));
    }

    #[tokio::test]
    async fn test_degraded_dependency() {
        // A degrades, B depends on A, B should still run and can check is_degraded
        struct DegradedRunner;
        impl NodeRunner for DegradedRunner {
            fn run_node(&self, node: &ExecNode, ctx: &ExecContext) -> NodeResult {
                if node.id == "A" {
                    NodeResult {
                        node_id: "A".into(),
                        ok: true,
                        output: serde_json::Value::String("degraded-output".into()),
                        degraded: true,
                        error: None,
                    }
                } else {
                    let a_degraded = ctx.is_degraded("A");
                    NodeResult {
                        node_id: node.id.clone(),
                        ok: true,
                        output: serde_json::Value::String(format!("a_degraded={}", a_degraded)),
                        degraded: false,
                        error: None,
                    }
                }
            }
        }

        let nodes = vec![
            ExecNode {
                id: "A".into(),
                kind: "expert".into(),
                name: "Node A".into(),
                depends_on: vec![],
                timeout_secs: 30,
            },
            ExecNode {
                id: "B".into(),
                kind: "expert".into(),
                name: "Node B".into(),
                depends_on: vec!["A".into()],
                timeout_secs: 30,
            },
        ];

        let executor = DagExecutor::new(3, 3);
        let runner = Arc::new(DegradedRunner);
        let results = executor.execute(nodes, runner).await.unwrap();
        assert_eq!(results.len(), 2);

        let b_result = results.iter().find(|r| r.node_id == "B").unwrap();
        assert!(b_result.ok);
        assert_eq!(
            b_result.output,
            serde_json::Value::String("a_degraded=true".into())
        );
    }
}
