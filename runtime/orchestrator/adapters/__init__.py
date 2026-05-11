"""Adapter layer: wrap 05-代码示例/*.py 49 scripts as Prefect tasks without modifying them.

Each adapter shells out via subprocess to isolate import paths and side effects.
"""
