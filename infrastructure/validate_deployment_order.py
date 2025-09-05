#!/usr/bin/env python3
"""
Deployment Order Validation Script

This script validates that the CDK stacks are deployed in the correct order
and checks for any dependency issues.
"""

import json
import subprocess
import sys
from typing import Dict, List, Tuple


class DeploymentValidator:
    """Validates CDK deployment order and dependencies"""
    
    def __init__(self):
        self.stacks = {
            "outline-network": {
                "order": 1,
                "dependencies": [],
                "description": "Network infrastructure (VPC, subnets, security groups)"
            },
            "outline-database": {
                "order": 2,
                "dependencies": ["outline-network"],
                "description": "Database infrastructure (RDS, Redis, Secrets)"
            },
            "outline-application": {
                "order": 3,
                "dependencies": ["outline-network", "outline-database"],
                "description": "Application infrastructure (ECS, ALB, ECR)"
            },
            "outline-cicd": {
                "order": 4,
                "dependencies": ["outline-application"],
                "description": "CI/CD infrastructure (CodePipeline, CodeBuild)"
            }
        }
    
    def get_stack_status(self, environment: str = "dev") -> Dict[str, str]:
        """Get the current status of all stacks"""
        try:
            result = subprocess.run(
                ["cdk", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            
            deployed_stacks = {}
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    stack_name = line.strip()
                    deployed_stacks[stack_name] = "DEPLOYED"
            
            return deployed_stacks
        except subprocess.CalledProcessError:
            print("❌ Error: Could not get stack list. Make sure you're in the infrastructure directory.")
            return {}
        except FileNotFoundError:
            print("❌ Error: CDK CLI not found. Please install AWS CDK CLI first.")
            return {}
    
    def validate_deployment_order(self, environment: str = "dev") -> Tuple[bool, List[str]]:
        """Validate that stacks are deployed in the correct order"""
        deployed_stacks = self.get_stack_status(environment)
        
        if not deployed_stacks:
            return False, ["No stacks found"]
        
        errors = []
        warnings = []
        
        # Check if all required stacks are deployed
        for stack_name, stack_info in self.stacks.items():
            full_stack_name = f"{stack_name}-{environment}"
            
            if full_stack_name not in deployed_stacks:
                if stack_info["order"] == 1:
                    errors.append(f"❌ Missing foundation stack: {full_stack_name}")
                else:
                    warnings.append(f"⚠️  Missing stack: {full_stack_name}")
                continue
            
            # Check dependencies
            for dep in stack_info["dependencies"]:
                dep_stack_name = f"{dep}-{environment}"
                if dep_stack_name not in deployed_stacks:
                    errors.append(f"❌ Stack {full_stack_name} depends on {dep_stack_name} which is not deployed")
        
        # Check deployment order
        deployed_order = []
        for stack_name, stack_info in self.stacks.items():
            full_stack_name = f"{stack_name}-{environment}"
            if full_stack_name in deployed_stacks:
                deployed_order.append((stack_info["order"], full_stack_name))
        
        deployed_order.sort()
        
        # Verify order
        for i, (expected_order, stack_name) in enumerate(deployed_order):
            actual_order = i + 1
            if expected_order != actual_order:
                errors.append(f"❌ Stack {stack_name} deployed in wrong order (expected: {expected_order}, actual: {actual_order})")
        
        return len(errors) == 0, errors + warnings
    
    def show_deployment_plan(self, environment: str = "dev") -> None:
        """Show the recommended deployment plan"""
        print(f"\n🚀 DEPLOYMENT PLAN FOR {environment.upper()} ENVIRONMENT")
        print("=" * 60)
        
        for stack_name, stack_info in self.stacks.items():
            full_stack_name = f"{stack_name}-{environment}"
            deps = ", ".join([f"{dep}-{environment}" for dep in stack_info["dependencies"]]) if stack_info["dependencies"] else "None"
            
            print(f"\n{stack_info['order']}. {full_stack_name}")
            print(f"   Description: {stack_info['description']}")
            print(f"   Dependencies: {deps}")
            print(f"   Command: cdk deploy {full_stack_name}")
        
        print(f"\n💡 RECOMMENDED: Use 'cdk deploy --all' to deploy all stacks in order automatically")
    
    def show_cost_estimate(self, environment: str = "dev") -> None:
        """Show cost estimates for the environment"""
        try:
            from config.environments import get_environment_config
            
            config = get_environment_config(environment)
            print(f"\n💰 COST ESTIMATE FOR {environment.upper()} ENVIRONMENT")
            print("=" * 50)
            print(f"Estimated Monthly Cost: {config.estimated_monthly_cost}")
            print(f"Cost Optimization: {config.cost_optimization_notes}")
            
        except ImportError:
            print(f"\n💰 COST ESTIMATE FOR {environment.upper()} ENVIRONMENT")
            print("=" * 50)
            print("Cost information not available. Check config/environments.py")
    
    def run_validation(self, environment: str = "dev") -> bool:
        """Run complete validation"""
        print(f"🔍 VALIDATING DEPLOYMENT ORDER FOR {environment.upper()} ENVIRONMENT")
        print("=" * 70)
        
        # Show deployment plan
        self.show_deployment_plan(environment)
        
        # Show cost estimate
        self.show_cost_estimate(environment)
        
        # Validate current deployment
        print(f"\n🔍 VALIDATING CURRENT DEPLOYMENT")
        print("=" * 40)
        
        is_valid, messages = self.validate_deployment_order(environment)
        
        if messages:
            for message in messages:
                print(message)
        else:
            print("✅ No validation issues found")
        
        if is_valid:
            print("\n✅ DEPLOYMENT ORDER VALIDATION PASSED")
            return True
        else:
            print("\n❌ DEPLOYMENT ORDER VALIDATION FAILED")
            print("\n💡 To fix deployment order issues:")
            print("1. Destroy stacks in reverse order: cdk destroy --all")
            print("2. Deploy all stacks in correct order: cdk deploy --all")
            return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate CDK deployment order")
    parser.add_argument(
        "--environment", "-e",
        default="dev",
        choices=["dev", "staging", "prod"],
        help="Environment to validate (default: dev)"
    )
    parser.add_argument(
        "--plan-only", "-p",
        action="store_true",
        help="Show only deployment plan without validation"
    )
    
    args = parser.parse_args()
    
    validator = DeploymentValidator()
    
    if args.plan_only:
        validator.show_deployment_plan(args.environment)
        validator.show_cost_estimate(args.environment)
    else:
        success = validator.run_validation(args.environment)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
