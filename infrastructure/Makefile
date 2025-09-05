# Makefile for Outline Infrastructure CDK Operations

.PHONY: help install bootstrap deploy destroy diff synth list status clean validate

# Default target
help:
	@echo "Outline Infrastructure CDK Operations"
	@echo "===================================="
	@echo ""
	@echo "Available targets:"
	@echo "  install     Install Python dependencies"
	@echo "  bootstrap   Bootstrap CDK (first time only)"
	@echo "  synth       Synthesize CloudFormation templates"
	@echo "  diff        Show differences between deployed and local stacks"
	@echo "  deploy      Deploy all stacks"
	@echo "  destroy     Destroy all stacks"
	@echo "  list        List all stacks"
	@echo "  status      Show deployment status and outputs"
	@echo "  validate    Validate deployment order and dependencies"
	@echo "  clean       Clean up generated files"
	@echo "  help        Show this help message"
	@echo ""
	@echo "Environment variables:"
	@echo "  ENVIRONMENT        Environment name (default: dev)"
	@echo "  CDK_DEFAULT_REGION AWS region (default: us-east-1)"
	@echo "  CDK_DEFAULT_ACCOUNT AWS account ID"
	@echo ""
	@echo "Examples:"
	@echo "  make deploy                    # Deploy dev environment"
	@echo "  ENVIRONMENT=prod make deploy  # Deploy production environment"
	@echo "  make status                   # Show deployment status"
	@echo "  make validate                 # Validate deployment order"

# Set default environment
ENVIRONMENT ?= dev

# Install Python dependencies
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

# Bootstrap CDK (first time only)
bootstrap:
	@echo "Bootstrapping CDK..."
	cdk bootstrap

# Synthesize CloudFormation templates
synth:
	@echo "Synthesizing CloudFormation templates..."
	cdk synth

# Show differences between deployed and local stacks
diff:
	@echo "Showing differences for environment: $(ENVIRONMENT)"
	cdk diff --all

# Deploy all stacks
deploy: install
	@echo "Deploying infrastructure for environment: $(ENVIRONMENT)"
	cdk deploy --all --require-approval never

# Deploy specific stack
deploy-%: install
	@echo "Deploying stack: $*"
	cdk deploy $* --require-approval never

# Destroy all stacks
destroy:
	@echo "Destroying infrastructure for environment: $(ENVIRONMENT)"
	@read -p "Are you sure you want to destroy all stacks? (y/N): " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cdk destroy --all --force; \
	else \
		echo "Infrastructure destruction cancelled"; \
	fi

# Destroy specific stack
destroy-%:
	@echo "Destroying stack: $*"
	@read -p "Are you sure you want to destroy stack $*? (y/N): " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cdk destroy $* --force; \
	else \
		echo "Stack destruction cancelled"; \
	fi

# List all stacks
list:
	@echo "Listing stacks for environment: $(ENVIRONMENT)"
	cdk list

# Show deployment status and outputs
status: list
	@echo ""
	@echo "Stack outputs:"
	@for stack in $$(cdk list); do \
		echo "=== $$stack ==="; \
		cdk output --stack-name $$stack || echo "No outputs"; \
		echo ""; \
	done

# Validate deployment order and dependencies
validate:
	@echo "Validating deployment order for environment: $(ENVIRONMENT)"
	python validate_deployment_order.py --environment $(ENVIRONMENT)

# Show deployment plan only
plan:
	@echo "Showing deployment plan for environment: $(ENVIRONMENT)"
	python validate_deployment_order.py --environment $(ENVIRONMENT) --plan-only

# Clean up generated files
clean:
	@echo "Cleaning up generated files..."
	rm -rf cdk.out/
	rm -rf .cdk.staging/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Development helpers
dev-deploy: install
	@echo "Deploying development environment..."
	ENVIRONMENT=dev cdk deploy --all --require-approval never

staging-deploy: install
	@echo "Deploying staging environment..."
	ENVIRONMENT=staging cdk deploy --all --require-approval never

prod-deploy: install
	@echo "Deploying production environment..."
	ENVIRONMENT=prod cdk deploy --all --require-approval never

# Watch for changes (development)
watch: install
	@echo "Watching for changes..."
	cdk watch --all

# Validate templates
validate-templates: synth
	@echo "Validating CloudFormation templates..."
	@for template in cdk.out/*/template.json; do \
		echo "Validating $$template"; \
		aws cloudformation validate-template --template-body file://$$template; \
	done

# Show stack events
events-%:
	@echo "Showing events for stack: $*"
	aws cloudformation describe-stack-events --stack-name $*

# Show stack resources
resources-%:
	@echo "Showing resources for stack: $*"
	aws cloudformation list-stack-resources --stack-name $*

# Show stack parameters
parameters-%:
	@echo "Showing parameters for stack: $*"
	aws cloudformation describe-stacks --stack-name $* --query 'Stacks[0].Parameters'

# Cost analysis
cost:
	@echo "Showing cost comparison between environments..."
	python -c "from config.environments import get_cost_comparison; import json; print(json.dumps(get_cost_comparison(), indent=2))"
