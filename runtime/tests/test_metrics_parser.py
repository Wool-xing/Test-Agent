"""TDD: Metrics parser — extract test results from junit XML and JMeter JTL."""

from __future__ import annotations

import pytest

JUNIT_XML_PASSING = """<?xml version="1.0"?>
<testsuite name="smoke" tests="10" failures="0" errors="0" skipped="0">
  <testcase classname="test_auth" name="test_login" time="0.5"/>
  <testcase classname="test_auth" name="test_logout" time="0.3"/>
  <testcase classname="test_auth" name="test_register" time="1.2"/>
</testsuite>"""

JUNIT_XML_FAILING = """<?xml version="1.0"?>
<testsuite name="smoke" tests="10" failures="3" errors="1" skipped="1">
  <testcase classname="test_auth" name="test_login" time="0.5"/>
  <testcase classname="test_auth" name="test_fail1" time="0.3">
    <failure message="assert 200 == 404"/>
  </testcase>
</testsuite>"""

JUNIT_XML_EMPTY = """<?xml version="1.0"?>
<testsuite name="smoke" tests="0" failures="0" errors="0" skipped="0">
</testsuite>"""

JMETER_JTL_SAMPLE = """timeStamp,elapsed,label,responseCode,responseMessage,success,bytes,grpThreads,allThreads,Latency
1680000000000,120,Login,200,OK,true,1024,1,1,100
1680000001000,350,Search,200,OK,true,2048,3,3,300
1680000002000,80,Logout,200,OK,true,512,1,1,60
1680000003000,2500,HeavyQuery,500,Error,false,0,5,5,2400
"""


class TestJunitParser:
    def test_parse_passing(self):
        from runtime.orchestrator.metrics.parser import parse_junit
        m = parse_junit(JUNIT_XML_PASSING)
        assert m["total"] == 10
        assert m["passed"] == 10
        assert m["failed"] == 0
        assert m["rate"] == 1.0

    def test_parse_failing(self):
        from runtime.orchestrator.metrics.parser import parse_junit
        m = parse_junit(JUNIT_XML_FAILING)
        assert m["total"] == 10
        assert m["failed"] == 4  # 3 failures + 1 error
        assert m["skipped"] == 1
        assert m["rate"] == 0.5  # 5 passed / 10 total

    def test_parse_empty(self):
        from runtime.orchestrator.metrics.parser import parse_junit
        m = parse_junit(JUNIT_XML_EMPTY)
        assert m["total"] == 0
        assert m["passed"] == 0

    def test_parse_invalid_xml(self):
        from runtime.orchestrator.metrics.parser import parse_junit
        m = parse_junit("not xml at all")
        assert m == {}


class TestJmeterParser:
    def test_parse_jtl(self):
        from runtime.orchestrator.metrics.parser import parse_jmeter_jtl
        m = parse_jmeter_jtl(JMETER_JTL_SAMPLE)
        assert m["samples"] == 4
        assert m["failures"] == 1
        assert 100 <= m["avg_ms"] <= 800  # (120+350+80+2500)/4 = 762.5
        assert m["p95_ms"] >= 2000  # HeavyQuery is 2500
        assert 0 <= m["rate"] <= 1.0

    def test_parse_jtl_percentile(self):
        from runtime.orchestrator.metrics.parser import parse_jmeter_jtl
        m = parse_jmeter_jtl(JMETER_JTL_SAMPLE)
        # p95 should be >= 2500 (the slowest request)
        assert m["p95_ms"] >= 2000

    def test_parse_empty_jtl(self):
        from runtime.orchestrator.metrics.parser import parse_jmeter_jtl
        m = parse_jmeter_jtl("timeStamp,elapsed,label\n")
        assert m["samples"] == 0


class TestMetricsExtractor:
    def test_extract_from_outcome_junit(self):
        from runtime.orchestrator.metrics.parser import extract_metrics
        m = extract_metrics({"stdout": JUNIT_XML_PASSING, "kind": "junit"})
        assert m["total"] == 10
        assert m["rate"] == 1.0

    def test_extract_from_outcome_auto_detect_junit(self):
        from runtime.orchestrator.metrics.parser import extract_metrics
        m = extract_metrics({"stdout": JUNIT_XML_PASSING})
        assert m["total"] == 10  # auto-detected as junit

    def test_extract_from_outcome_auto_detect_jmeter(self):
        from runtime.orchestrator.metrics.parser import extract_metrics
        m = extract_metrics({"stdout": JMETER_JTL_SAMPLE})
        assert m["samples"] == 4  # auto-detected as jmeter

    def test_extract_empty_outcome(self):
        from runtime.orchestrator.metrics.parser import extract_metrics
        m = extract_metrics({"stdout": ""})
        assert m == {}

    def test_extract_none_stdout(self):
        from runtime.orchestrator.metrics.parser import extract_metrics
        m = extract_metrics({})
        assert m == {}
