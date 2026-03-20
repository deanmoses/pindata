.PHONY: export validate push clean agent-docs

export:
	uv run python3 scripts/export_catalog_json.py

validate:
	uv run python3 scripts/validate_catalog.py

push: export
	uv run python3 scripts/push_to_r2.py --skip-export

clean:
	rm -rf export/

agent-docs:
	python3 scripts/build_agent_docs.py
