.ONESHELL:
.DEFAULT_GOAL := help
SHELL := /bin/bash

ROOT := $(CURDIR)
WEB_DIR := $(ROOT)/apps/web
API_DIR := $(ROOT)/apps/api
EXT_DIR := $(ROOT)/apps/extension

.PHONY: help dev test lint format web-build api-run extension-build

help:
	@printf "Available targets:\\n"
	@printf "  make dev\\n"
	@printf "  make test\\n"
	@printf "  make lint\\n"
	@printf "  make format\\n"

dev:
	@set -euo pipefail; \
	trap 'kill 0' INT TERM EXIT; \
	( cd "$(WEB_DIR)" && npm run dev ) & \
	( cd "$(API_DIR)" && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 ) & \
	( cd "$(EXT_DIR)" && npm run dev ) & \
	wait

test:
	@set -euo pipefail; \
	npm --workspace @careeros/shared test; \
	npm --workspace @careeros/web test; \
	npm --workspace @careeros/extension test; \
	cd "$(API_DIR)" && python3 -m pytest

lint:
	@set -euo pipefail; \
	npm --workspace @careeros/shared run typecheck; \
	npm --workspace @careeros/web run typecheck; \
	npm --workspace @careeros/extension run typecheck; \
	cd "$(API_DIR)" && python3 -m ruff check .

format:
	@set -euo pipefail; \
	FILES=$$(find apps/web apps/extension packages/shared docs infra -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.mjs' -o -name '*.cjs' -o -name '*.json' -o -name '*.md' -o -name '*.yml' -o -name '*.yaml' \) ! -path '*/node_modules/*' ! -path '*/.next/*' ! -path '*/.plasmo/*' ! -path '*/build/*'); \
	npx prettier --write $$FILES README.md package.json; \
	cd "$(API_DIR)" && python3 -m ruff format .

web-build:
	@cd "$(WEB_DIR)" && npm run build

extension-build:
	@cd "$(EXT_DIR)" && npm run build

api-run:
	@cd "$(API_DIR)" && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
