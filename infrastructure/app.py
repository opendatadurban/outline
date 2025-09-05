#!/usr/bin/env python3
"""
Outline Infrastructure CDK App

This CDK app deploys the complete Outline infrastructure on AWS ECS.
The infrastructure is split into logical stacks for better organization and management.

STACK EXECUTION ORDER:
1. NetworkStack (Foundation - VPC, subnets, security groups)
2. DatabaseStack (Data layer - RDS, Redis, Secrets)
3. ApplicationStack (Runtime - ECS, ALB, ECR)
4. CiCdStack (Automation - CodePipeline, CodeBuild)

Each stack depends on the previous one(s) and cannot be deployed independently.
"""

import os
import aws_cdk as cdk
from aws_cdk import Environment, Tags
from stacks.network_stack import NetworkStack
from stacks.database_stack import DatabaseStack
from stacks.application_stack import ApplicationStack
from stacks.cicd_stack import CiCdStack

app = cdk.App()

# Configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
PROJECT_NAME = 'outline'
REGION = os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
ACCOUNT = os.getenv('CDK_DEFAULT_ACCOUNT')

# Environment configuration
env = Environment(account=ACCOUNT, region=REGION)

# Common tags for all resources
common_tags = {
    'Project': PROJECT_NAME,
    'Environment': ENVIRONMENT,
    'ManagedBy': 'CDK',
    'Owner': 'DevOps',
    'CostCenter': 'Engineering',
    'Purpose': 'Outline Knowledge Base',
    'DeploymentDate': os.getenv('DEPLOYMENT_DATE', 'Unknown')
}

# STACK 1: Network Stack (Foundation)
network_stack = NetworkStack(
    app, f"{PROJECT_NAME}-network-{ENVIRONMENT}",
    env=env,
    environment=ENVIRONMENT,
    project_name=PROJECT_NAME,
    description="Network infrastructure for Outline application"
)

# STACK 2: Database Stack (depends on Network)
database_stack = DatabaseStack(
    app, f"{PROJECT_NAME}-database-{ENVIRONMENT}",
    env=env,
    environment=ENVIRONMENT,
    project_name=PROJECT_NAME,
    vpc=network_stack.vpc,
    database_security_group=network_stack.database_security_group,
    redis_security_group=network_stack.redis_security_group,
    description="Database infrastructure for Outline application"
)
database_stack.add_dependency(network_stack)

# STACK 3: Application Stack (depends on Network and Database)
# SSL Certificate Configuration
DOMAIN_NAME = "wiki.opencitieslab.org"

application_stack = ApplicationStack(
    app, f"{PROJECT_NAME}-application-{ENVIRONMENT}",
    env=env,
    environment=ENVIRONMENT,
    project_name=PROJECT_NAME,
    vpc=network_stack.vpc,
    alb_security_group=network_stack.alb_security_group,
    ecs_security_group=network_stack.ecs_security_group,
    database_secret=database_stack.database_secret,
    redis_secret=database_stack.redis_secret,
    database_host=database_stack.database_instance.instance_endpoint.hostname,
    database_port=str(database_stack.database_instance.instance_endpoint.port),
    redis_host=database_stack.redis_cluster.attr_redis_endpoint_address,
    redis_port=database_stack.redis_cluster.attr_redis_endpoint_port,
    domain_name=DOMAIN_NAME,  # Enable SSL with custom domain
    description="Application infrastructure for Outline on ECS"
)
application_stack.add_dependency(network_stack)
application_stack.add_dependency(database_stack)


# STACK 4: CI/CD Stack (depends on Application)
cicd_stack = CiCdStack(
    app, f"{PROJECT_NAME}-cicd-{ENVIRONMENT}",
    env=env,
    environment=ENVIRONMENT,
    project_name=PROJECT_NAME,
    ecs_cluster=application_stack.ecs_cluster,
    ecs_service=application_stack.ecs_service,
    description="CI/CD pipeline for Outline application"
)
cicd_stack.add_dependency(application_stack)

# ECS resources are passed directly to CiCdStack constructor

# Apply common tags to all stacks
for stack in [network_stack, database_stack, application_stack, cicd_stack]:
    for key, value in common_tags.items():
        Tags.of(stack).add(key, value)

app.synth()
