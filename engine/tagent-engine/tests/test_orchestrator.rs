//! Integration tests for the DAG orchestrator.
//!
//! These tests exercise the public API of `DagExecutor` with various
//! DAG topologies and runner behaviours.

use std::collections::HashSet;
use std::sync::Arc;

use tagent_engine::orchestrator::{
    DagExecutor, ExecContext, ExecNode, NodeResult, NodeRunner,
};

// ---------------------------------------------------------------------------
// Helper runners
// ---------------------------------------------------------------------------

/// Runner that records which nodes were executed and in which wave.
struct RecordingRunner {
    /// Mutex-protected ordered list of (node_id, wave_number).
    record: std::sync::Mutex<Vec<(String, usize)>>,
}

impl RecordingRunner {
    fn new() -> Self {
        Self {
            record: std::sync::Mutex::new(Vec::new()),
        }
    }

    fn executed_ids(&self) -> Vec<String> {
        self.record.lock().unwrap().iter().map(|(id, _)| id.clone()).collect()
    }
}

impl NodeRunner for RecordingRunner {
    fn run_node(&self, node: &ExecNode, _ctx: &ExecContext) -> NodeResult {
        let mut rec = self.record.lock().unwrap();
        rec.push((node.id.clone(), rec.len()));
        NodeResult {
            node_id: node.id.clone(),
            ok: true,
            output: serde_json::Value::String(node.id.clone()),
            degraded: false,
            error: None,
        }
    }
}

/// Runner that fails specific node ids.
struct SelectiveFailingRunner {
    fail_ids: HashSet<String>,
}

impl NodeRunner for SelectiveFailingRunner {
    fn run_node(&self, node: &ExecNode, _ctx: &ExecContext) -> NodeResult {
        let ok = !self.fail_ids.contains(&node.id);
        NodeResult {
            node_id: node.id.clone(),
            ok,
            output: if ok {
                serde_json::Value::String(node.id.clone())
            } else {
                serde_json::Value::Null
            },
            degraded: false,
            error: if ok {
                None
            } else {
                Some(format!("{} failed intentionally", node.id))
            },
        }
    }
}

// ---------------------------------------------------------------------------
// Test DAG builders
// ---------------------------------------------------------------------------

fn diamond_dag() -> Vec<ExecNode> {
    vec![
        ExecNode {
            id: "start".into(),
            kind: "expert".into(),
            name: "Start".into(),
            depends_on: vec![],
            timeout_secs: 10,
        },
        ExecNode {
            id: "left".into(),
            kind: "skill".into(),
            name: "Left Branch".into(),
            depends_on: vec!["start".into()],
            timeout_secs: 10,
        },
        ExecNode {
            id: "right".into(),
            kind: "skill".into(),
            name: "Right Branch".into(),
            depends_on: vec!["start".into()],
            timeout_secs: 10,
        },
        ExecNode {
            id: "end".into(),
            kind: "expert".into(),
            name: "End".into(),
            depends_on: vec!["left".into(), "right".into()],
            timeout_secs: 10,
        },
    ]
}

fn linear_dag(count: usize) -> Vec<ExecNode> {
    let mut nodes = Vec::new();
    for i in 0..count {
        let id = format!("N{}", i);
        let depends_on = if i == 0 {
            vec![]
        } else {
            vec![format!("N{}", i - 1)]
        };
        nodes.push(ExecNode {
            id,
            kind: "script".into(),
            name: format!("Node {}", i),
            depends_on,
            timeout_secs: 5,
        });
    }
    nodes
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_diamond_dag_all_nodes_execute() {
    let runner = Arc::new(RecordingRunner::new());
    let executor = DagExecutor::new(3, 3);

    let results = executor.execute(diamond_dag(), runner.clone()).await.unwrap();

    assert_eq!(results.len(), 4);
    let ids: HashSet<&str> = results.iter().map(|r| r.node_id.as_str()).collect();
    assert!(ids.contains("start"));
    assert!(ids.contains("left"));
    assert!(ids.contains("right"));
    assert!(ids.contains("end"));
}

#[tokio::test]
async fn test_diamond_dag_topological_order_respected() {
    // In a diamond DAG: start -> left,right -> end
    // start must execute before left/right, and left/right must execute before end.
    // The recording runner logs execution order, so "start" must come first and
    // "end" must come last.
    let runner = Arc::new(RecordingRunner::new());
    let executor = DagExecutor::new(3, 3);

    let results = executor.execute(diamond_dag(), runner.clone()).await.unwrap();
    let ordered: Vec<&str> = results.iter().map(|r| r.node_id.as_str()).collect();

    let start_pos = ordered.iter().position(|&id| id == "start").unwrap();
    let left_pos = ordered.iter().position(|&id| id == "left").unwrap();
    let right_pos = ordered.iter().position(|&id| id == "right").unwrap();
    let end_pos = ordered.iter().position(|&id| id == "end").unwrap();

    assert!(start_pos < left_pos);
    assert!(start_pos < right_pos);
    assert!(left_pos < end_pos);
    assert!(right_pos < end_pos);
}

#[tokio::test]
async fn test_circuit_breaker_stops_after_max_failures() {
    let mut fail_ids = HashSet::new();
    fail_ids.insert("N0".into());
    fail_ids.insert("N1".into());
    fail_ids.insert("N2".into());

    let runner = Arc::new(SelectiveFailingRunner { fail_ids });
    let executor = DagExecutor::new(2, 3); // trip after 2 failures

    let results = executor.execute(linear_dag(10), runner).await.unwrap();

    // N0 fails (1), N1 fails (2) -> circuit breaker trips
    // N2..N9 should NOT execute
    let executed: HashSet<&str> = results.iter().map(|r| r.node_id.as_str()).collect();
    assert!(executed.contains("N0"));
    assert!(executed.contains("N1"));
    // After 2 failures, circuit breaks
    assert!(results.len() <= 2);
}

#[tokio::test]
async fn test_empty_dag() {
    let runner = Arc::new(RecordingRunner::new());
    let executor = DagExecutor::new(3, 3);

    let results = executor.execute(vec![], runner).await.unwrap();
    assert!(results.is_empty());
}

#[tokio::test]
async fn test_single_node_dag() {
    let runner = Arc::new(RecordingRunner::new());
    let executor = DagExecutor::new(3, 3);

    let nodes = vec![ExecNode {
        id: "only".into(),
        kind: "expert".into(),
        name: "Only Node".into(),
        depends_on: vec![],
        timeout_secs: 10,
    }];

    let results = executor.execute(nodes, runner).await.unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].node_id, "only");
    assert!(results[0].ok);
}

#[tokio::test]
async fn test_exec_context_degraded_check() {
    struct DegradedCheckRunner;
    impl NodeRunner for DegradedCheckRunner {
        fn run_node(&self, node: &ExecNode, ctx: &ExecContext) -> NodeResult {
            match node.id.as_str() {
                "producer" => NodeResult {
                    node_id: "producer".into(),
                    ok: true,
                    output: serde_json::Value::String("partial".into()),
                    degraded: true,
                    error: None,
                },
                "consumer" => {
                    let was_degraded = ctx.is_degraded("producer");
                    NodeResult {
                        node_id: "consumer".into(),
                        ok: !was_degraded, // consumer fails if dep was degraded
                        output: serde_json::Value::Bool(was_degraded),
                        degraded: false,
                        error: if was_degraded {
                            Some("upstream degraded".into())
                        } else {
                            None
                        },
                    }
                }
                _ => unreachable!(),
            }
        }
    }

    let nodes = vec![
        ExecNode {
            id: "producer".into(),
            kind: "expert".into(),
            name: "Producer".into(),
            depends_on: vec![],
            timeout_secs: 10,
        },
        ExecNode {
            id: "consumer".into(),
            kind: "expert".into(),
            name: "Consumer".into(),
            depends_on: vec!["producer".into()],
            timeout_secs: 10,
        },
    ];

    let runner = Arc::new(DegradedCheckRunner);
    let executor = DagExecutor::new(3, 3);

    let results = executor.execute(nodes, runner).await.unwrap();
    assert_eq!(results.len(), 2);

    let consumer = results.iter().find(|r| r.node_id == "consumer").unwrap();
    assert!(!consumer.ok, "consumer should have failed due to degraded upstream");
    assert_eq!(consumer.output, serde_json::Value::Bool(true));
}
