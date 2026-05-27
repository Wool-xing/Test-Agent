"""Adapter layer: wrap utils/*.py 49 scripts as Prefect tasks without modifying them.

Each adapter shells out via subprocess to isolate import paths and side effects.
"""
