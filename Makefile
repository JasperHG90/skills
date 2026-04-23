SHELL := /bin/bash

.PHONY: help install pre-commit-setup setup pre-commit

.DEFAULT_GOAL := help

help:
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

venv: ## Set up a virtual environment
	uv venv .venv --clear

install: ## Install python dependencies
	uv pip install prek pytest

pre-commit-setup: ## Install pre-commit hooks
	uv run prek install

setup: venv install pre-commit-setup ## Install python dependencies and pre-commit hooks

pre-commit: ## Run pre-commit
	uv run prek run -a
