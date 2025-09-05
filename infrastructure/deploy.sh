#!/bin/bash

# Outline Infrastructure Deployment Script
# This script deploys the complete Outline infrastructure on AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${ENVIRONMENT:-"dev"}
PROJECT_NAME="outline"
REGION=${CDK_DEFAULT_REGION:-"us-east-1"}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if CDK is installed
    if ! command -v cdk &> /dev/null; then
        print_error "AWS CDK is not installed. Please install it first: npm install -g aws-cdk"
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check if pip is available
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install it first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        print_success "Dependencies installed"
    else
        print_warning "requirements.txt not found, skipping dependency installation"
    fi
}

# Function to bootstrap CDK
bootstrap_cdk() {
    print_status "Checking if CDK is bootstrapped..."
    
    if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
        print_status "CDK not bootstrapped. Bootstrapping now..."
        cdk bootstrap
        print_success "CDK bootstrapped successfully"
    else
        print_success "CDK already bootstrapped"
    fi
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure for environment: $ENVIRONMENT"
    
    # List stacks
    print_status "Available stacks:"
    cdk list
    
    # Deploy all stacks
    print_status "Deploying all stacks..."
    cdk deploy --all --require-approval never
    
    print_success "Infrastructure deployment completed"
}

# Function to show deployment status
show_status() {
    print_status "Infrastructure deployment status:"
    
    # List stacks and their status
    cdk list
    
    # Show outputs for each stack
    for stack in $(cdk list); do
        print_status "Outputs for $stack:"
        cdk output --stack-name $stack || print_warning "No outputs for $stack"
        echo
    done
}

# Function to destroy infrastructure
destroy_infrastructure() {
    print_warning "This will destroy all infrastructure for environment: $ENVIRONMENT"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Destroying infrastructure..."
        cdk destroy --all --force
        print_success "Infrastructure destroyed"
    else
        print_status "Infrastructure destruction cancelled"
    fi
}

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy     Deploy the complete infrastructure"
    echo "  destroy    Destroy the complete infrastructure"
    echo "  status     Show deployment status and outputs"
    echo "  help       Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  ENVIRONMENT        Environment name (default: dev)"
    echo "  CDK_DEFAULT_REGION AWS region (default: us-east-1)"
    echo "  CDK_DEFAULT_ACCOUNT AWS account ID"
    echo ""
    echo "Examples:"
    echo "  $0 deploy                    # Deploy dev environment"
    echo "  ENVIRONMENT=prod $0 deploy   # Deploy production environment"
    echo "  $0 status                    # Show deployment status"
}

# Main script logic
main() {
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            install_dependencies
            bootstrap_cdk
            deploy_infrastructure
            show_status
            ;;
        "destroy")
            check_prerequisites
            destroy_infrastructure
            ;;
        "status")
            check_prerequisites
            show_status
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
