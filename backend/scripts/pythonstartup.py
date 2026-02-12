"""
Python REPL startup for the backend project.
Auto-loaded via PYTHONSTARTUP in the mise `python` task.
"""

try:
    import pandas as pd

    pd.set_option("display.max_columns", None)
except ImportError:
    pass

try:
    from sqlalchemy import create_engine

    db = create_engine("postgresql://super@localhost:5432/super")
except (ImportError, Exception):
    pass
