# Configuration Archive

This directory contains all configuration files from the ArcticShadowTracker project before archiving on 2025-09-18.

## Contents

- **config/**: Main configuration directory containing:
  - **ArcticShadowTracker.code-workspace**: VSCode workspace configuration
  - **barentswatch_config.example.json**: Barentswatch API configuration template
  - **data_pipeline_config.py**: Data pipeline configuration
  - **pytest.ini**: Testing configuration

- **arcticshadowtracker_env/**: Python environment configuration and dependencies

- **Configuration files**:
  - **.pre-commit-config.yaml**: Pre-commit hooks configuration
  - **.dockerignore**: Docker build ignore patterns

## Purpose

These configuration files represent the development environment setup, API configurations, testing setup, and deployment configurations that were built up over time. They show the complexity that accumulated in the system configuration.

## Usage

These files can be referenced for:
- Understanding the original system's dependencies and setup
- Examples of configuration patterns (both good and overly complex)
- Reference for API configurations and endpoints
- Learning from the environmental setup approach

## Note

The goal of the rebuild is to start with much simpler configuration. Use these files as reference for what might be needed, but aim for minimal, essential configuration only.