# Outline Infrastructure Deployment Script for PowerShell
# This script deploys the complete Outline infrastructure on AWS

param(
    [Parameter(Position=0)]
    [ValidateSet("deploy", "destroy", "status", "help")]
    [string]$Command = "deploy",
    
    [Parameter()]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"
$White = "White"

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    try {
        $null = Get-Command aws -ErrorAction Stop
    }
    catch {
        Write-Error "AWS CLI is not installed. Please install it first."
        exit 1
    }
    
    # Check if CDK is installed
    try {
        $null = Get-Command cdk -ErrorAction Stop
    }
    catch {
        Write-Error "AWS CDK is not installed. Please install it first: npm install -g aws-cdk"
        exit 1
    }
    
    # Check if Python is available
    try {
        $null = Get-Command python -ErrorAction Stop
    }
    catch {
        try {
            $null = Get-Command python3 -ErrorAction Stop
        }
        catch {
            Write-Error "Python is not installed. Please install it first."
            exit 1
        }
    }
    
    # Check if pip is available
    try {
        $null = Get-Command pip -ErrorAction Stop
    }
    catch {
        try {
            $null = Get-Command pip3 -ErrorAction Stop
        }
        catch {
            Write-Error "pip is not installed. Please install it first."
            exit 1
        }
    }
    
    Write-Success "Prerequisites check passed"
}

# Function to install dependencies
function Install-Dependencies {
    Write-Status "Installing Python dependencies..."
    
    if (Test-Path "requirements.txt") {
        try {
            pip install -r requirements.txt
            Write-Success "Dependencies installed"
        }
        catch {
            Write-Warning "Failed to install dependencies: $_"
        }
    }
    else {
        Write-Warning "requirements.txt not found, skipping dependency installation"
    }
}

# Function to bootstrap CDK
function Initialize-CDK {
    Write-Status "Checking if CDK is bootstrapped..."
    
    try {
        $null = aws cloudformation describe-stacks --stack-name CDKToolkit 2>$null
        Write-Success "CDK already bootstrapped"
    }
    catch {
        Write-Status "CDK not bootstrapped. Bootstrapping now..."
        try {
            cdk bootstrap
            Write-Success "CDK bootstrapped successfully"
        }
        catch {
            Write-Error "Failed to bootstrap CDK: $_"
            exit 1
        }
    }
}

# Function to deploy infrastructure
function Deploy-Infrastructure {
    Write-Status "Deploying infrastructure for environment: $Environment"
    
    # Set environment variable
    $env:ENVIRONMENT = $Environment
    
    # List stacks
    Write-Status "Available stacks:"
    cdk list
    
    # Deploy all stacks
    Write-Status "Deploying all stacks..."
    try {
        cdk deploy --all --require-approval never
        Write-Success "Infrastructure deployment completed"
    }
    catch {
        Write-Error "Infrastructure deployment failed: $_"
        exit 1
    }
}

# Function to show deployment status
function Show-Status {
    Write-Status "Infrastructure deployment status:"
    
    # List stacks and their status
    cdk list
    
    # Show outputs for each stack
    $stacks = cdk list
    foreach ($stack in $stacks) {
        Write-Status "Outputs for $stack:"
        try {
            cdk output --stack-name $stack
        }
        catch {
            Write-Warning "No outputs for $stack"
        }
        Write-Host ""
    }
}

# Function to destroy infrastructure
function Destroy-Infrastructure {
    Write-Warning "This will destroy all infrastructure for environment: $Environment"
    $confirmation = Read-Host "Are you sure you want to continue? (y/N)"
    
    if ($confirmation -eq "y" -or $confirmation -eq "Y") {
        Write-Status "Destroying infrastructure..."
        try {
            cdk destroy --all --force
            Write-Success "Infrastructure destroyed"
        }
        catch {
            Write-Error "Failed to destroy infrastructure: $_"
            exit 1
        }
    }
    else {
        Write-Status "Infrastructure destruction cancelled"
    }
}

# Function to show help
function Show-Help {
    Write-Host "Usage: .\deploy.ps1 [COMMAND] [OPTIONS]" -ForegroundColor $White
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor $White
    Write-Host "  deploy     Deploy the complete infrastructure"
    Write-Host "  destroy    Destroy the complete infrastructure"
    Write-Host "  status     Show deployment status and outputs"
    Write-Host "  help       Show this help message"
    Write-Host ""
    Write-Host "Options:" -ForegroundColor $White
    Write-Host "  -Environment Environment name (dev, staging, prod)"
    Write-Host ""
    Write-Host "Environment variables:" -ForegroundColor $White
    Write-Host "  ENVIRONMENT        Environment name (default: dev)"
    Write-Host "  CDK_DEFAULT_REGION AWS region (default: us-east-1)"
    Write-Host "  CDK_DEFAULT_ACCOUNT AWS account ID"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor $White
    Write-Host "  .\deploy.ps1 deploy                    # Deploy dev environment"
    Write-Host "  .\deploy.ps1 deploy -Environment prod  # Deploy production environment"
    Write-Host "  .\deploy.ps1 status                    # Show deployment status"
}

# Main script logic
function Main {
    switch ($Command) {
        "deploy" {
            Test-Prerequisites
            Install-Dependencies
            Initialize-CDK
            Deploy-Infrastructure
            Show-Status
        }
        "destroy" {
            Test-Prerequisites
            Destroy-Infrastructure
        }
        "status" {
            Test-Prerequisites
            Show-Status
        }
        "help" {
            Show-Help
        }
        default {
            Write-Error "Unknown command: $Command"
            Show-Help
            exit 1
        }
    }
}

# Run main function
Main
