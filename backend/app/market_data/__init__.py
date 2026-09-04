"""Market data package.

Adapters that talk to external market-data providers. Only this package is
allowed to import a provider SDK (yfinance). Everything upstream sees the
normalized domain types defined here.
"""
