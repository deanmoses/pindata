.PHONY: export validate push clean agent-docs

# Export catalog markdown to JSON build artifacts in export/.
export:
	uv run python3 scripts/export_catalog_json.py

# Validate catalog records and data patches against their JSON schemas.
# Structural checks only; run this before push.
validate:
	uv run python3 scripts/validate_catalog.py
	uv run python3 scripts/validate_patches.py

# Export, then push catalog JSON and data patches (patches/*.yaml) to
# Cloudflare R2. Requires R2_* credentials in the environment or .env.
push: export
	uv run python3 scripts/push_to_r2.py --skip-export

# Remove the export/ build directory.
clean:
	rm -rf export/

# Regenerate CLAUDE.md and AGENTS.md from docs/AGENTS.src.md.
agent-docs:
	python3 scripts/build_agent_docs.py
