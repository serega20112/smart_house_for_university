"""Domain model of the smart home.

The model speaks about accounts, devices, climate, scenarios, boards and the
personal projection of a home. It depends on nothing: no framework, no database,
no transport, no language pipeline, and not even on the clock. Every value it
refuses to hold is declared in :mod:`smart_home.domain.exceptions`, every fact it
records is declared in :mod:`smart_home.domain.events`, and every aggregate carries a
typed identifier from :mod:`smart_home.domain.identifiers`.
"""
