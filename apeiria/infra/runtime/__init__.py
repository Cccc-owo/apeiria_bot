"""Runtime bootstrap and environment integration.

Keep this package import-light. Modules under `infra.runtime` are imported
directly to avoid reintroducing cycles during the migration from legacy
runtime entrypoints.
"""
