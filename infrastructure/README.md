# Outline Infrastructure with AWS CDK

This directory contains the AWS CDK infrastructure code for deploying the Outline application on AWS ECS.

## 🏗️ Architecture Overview

The infrastructure is split into logical stacks for better organization and management:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NetworkStack  │    │ DatabaseStack   │    │ApplicationStack │    │   CiCdStack     │
│                 │    │                 │    │                 │    │                 │
│ • VPC          │───▶│ • RDS PostgreSQL│◀───│ • ECS Cluster   │◀───│ • CodePipeline  │
│ • Subnets      │    │ • ElastiCache   │    │ • ECS Service   │    │ • CodeBuild     │
│ • Security     │    │ • Secrets       │    │ • ALB           │    │ • ECR Build     │
│   Groups       │    │ • Subnet Groups │    │ • Auto-scaling  │    │ • ECS Deploy    │
│ • VPC Endpoints│    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 **STACK EXECUTION ORDER - CRITICAL**

**⚠️ IMPORTANT: Stacks MUST be deployed in this exact order due to dependencies:**

### 1. **NetworkStack** (Foundation)
- **Purpose**: VPC, subnets, security groups, and networking components
- **Dependencies**: None
- **Deploy Command**: `cdk deploy outline-network-{ENVIRONMENT}`

### 2. **DatabaseStack** (Data Layer)
- **Purpose**: RDS PostgreSQL, ElastiCache Redis, and Secrets Manager
- **Dependencies**: NetworkStack (requires VPC and security groups)
- **Deploy Command**: `cdk deploy outline-database-{ENVIRONMENT}`

### 3. **ApplicationStack** (Runtime)
- **Purpose**: ECS cluster, services, ALB, and ECR repository
- **Dependencies**: NetworkStack + DatabaseStack (requires VPC, security groups, and secrets)
- **Deploy Command**: `cdk deploy outline-application-{ENVIRONMENT}`

### 4. **CiCdStack** (Automation)
- **Purpose**: CodePipeline, CodeBuild, and deployment automation
- **Dependencies**: ApplicationStack (requires ECS cluster and service)
- **Deploy Command**: `cdk deploy outline-cicd-{ENVIRONMENT}`

## 💰 **Cost Optimization Features**

### **Development Environment** - Estimated: $50-80/month
- **VPC**: 2 AZs, 1 NAT Gateway (minimum required for RDS)
- **Database**: t3.micro, 20GB storage, 7-day backups
- **Redis**: t3.micro, single node
- **ECS**: 512 CPU units, 1GB RAM, single instance
- **Auto-scaling**: 1-3 instances
- **Logs**: 7-day retention

### **Staging Environment** - Estimated: $150-250/month
- **VPC**: 3 AZs, 2 NAT Gateways
- **Database**: t3.small, 50GB storage, 14-day backups
- **Redis**: t3.small, 2 nodes
- **ECS**: 1024 CPU units, 2GB RAM, 2 instances
- **Auto-scaling**: 2-5 instances
- **Logs**: 14-day retention

### **Production Environment** - Estimated: $400-600/month
- **VPC**: 3 AZs, 3 NAT Gateways
- **Database**: t3.medium, 100GB storage, 30-day backups
- **Redis**: t3.small, 3 nodes
- **ECS**: 2048 CPU units, 4GB RAM, 3 instances
- **Auto-scaling**: 3-10 instances
- **Logs**: 30-day retention

## 🏷️ **Comprehensive Resource Tagging**

All AWS resources are automatically tagged with:

```yaml
Project: outline
Environment: {dev|staging|prod}
ManagedBy: CDK
Owner: DevOps
CostCenter: Engineering
Purpose: Outline Knowledge Base
DeploymentDate: {timestamp}
Type: {ResourceType}
Name: {resource-specific-name}
```

**Resource-specific tags include:**
- **VPC Resources**: Type, Name
- **Security Groups**: Type, Name
- **Database Resources**: Type, Name, Engine, Purpose
- **ECS Resources**: Type, Name
- **IAM Roles**: Type, Name
- **Log Groups**: Type, Name
- **CodeBuild/CodePipeline**: Type, Name

## 📋 Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.8 or higher
- AWS CDK CLI installed globally: `npm install -g aws-cdk`
- Docker (for building and testing locally)

## 🚀 Installation

1. **Install Python dependencies:**
   ```bash
   cd infrastructure
   pip install -r requirements.txt
   ```

2. **Bootstrap CDK (first time only):**
   ```bash
   cdk bootstrap
   ```

## ⚙️ Configuration

### Environment Variables

Set the following environment variables:

```bash
export ENVIRONMENT=dev          # dev, staging, prod
export CDK_DEFAULT_REGION=us-east-2
export CDK_DEFAULT_ACCOUNT=your-aws-account-id
export DEPLOYMENT_DATE=$(date +%Y-%m-%d)  # Optional: for tracking

# Optional: Custom Domain Configuration
export DOMAIN_NAME=your-domain.com        # Your custom domain
export CERTIFICATE_ARN=arn:aws:acm:...    # Existing ACM certificate ARN (optional)
```

### Required Secrets

The infrastructure automatically creates and manages the following secrets in AWS Secrets Manager:

1. **Database Secret** (`outline-{environment}-database-secret`):
   - Contains: `url`, `username`, `password`, `host`, `port`, `dbname`
   - Used by: ECS tasks for database connection

2. **Redis Secret** (`outline-{environment}-redis-secret`):
   - Contains: `url`, `host`, `port`, `password`
   - Used by: ECS tasks for Redis connection

**Note**: These secrets are automatically generated with secure random passwords. The database and Redis instances are configured to use these credentials.

### Stack Configuration

Each stack can be configured independently. Key configuration options:

- **NetworkStack**: VPC CIDR, number of AZs, NAT gateway configuration
- **DatabaseStack**: Instance types, storage sizes, backup retention
- **ApplicationStack**: ECS task CPU/memory, desired count, auto-scaling thresholds, custom domain/SSL
- **CiCdStack**: Build timeout, deployment strategy

### Custom Domain and SSL Configuration

The ApplicationStack supports custom domains with SSL certificates:

#### Option 1: Using Existing ACM Certificate
```python
# In app.py, pass the certificate ARN
ApplicationStack(
    scope, "outline-application-dev",
    environment="dev",
    project_name="outline",
    vpc=vpc,
    alb_security_group=alb_sg,
    ecs_security_group=ecs_sg,
    database_secret=db_secret,
    redis_secret=redis_secret,
    domain_name="your-domain.com",
    certificate_arn="arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
)
```

#### Option 2: Creating New ACM Certificate
```python
# In app.py, pass only the domain name
ApplicationStack(
    scope, "outline-application-dev",
    environment="dev",
    project_name="outline",
    vpc=vpc,
    alb_security_group=alb_sg,
    ecs_security_group=ecs_sg,
    database_secret=db_secret,
    redis_secret=redis_secret,
    domain_name="your-domain.com"
    # certificate_arn not provided - will create new certificate
)
```

**Important Notes for Custom Domains:**
- ACM certificates must be in the same region as the ALB
- For new certificates, you must complete DNS validation by adding CNAME records to your external DNS provider
- After deployment, create an A/ALIAS or CNAME record in your DNS pointing to the ALB DNS name
- HTTP traffic will automatically redirect to HTTPS when SSL is configured

## 🚀 Deployment

### **⚠️ CRITICAL: Deploy in Order**

**Option 1: Deploy All Stacks (Recommended)**
```bash
# Deploy all stacks in dependency order automatically
cdk deploy --all
```

**Option 2: Deploy Individual Stacks (Manual Order)**
```bash
# 1. Deploy network infrastructure first
cdk deploy outline-network-{ENVIRONMENT}

# 2. Deploy database infrastructure
cdk deploy outline-database-{ENVIRONMENT}

# 3. Deploy application infrastructure
cdk deploy outline-application-{ENVIRONMENT}

# 4. Deploy CI/CD infrastructure
cdk deploy outline-cicd-{ENVIRONMENT}
```

### **Environment-Specific Deployment**

```bash
# Development environment
ENVIRONMENT=dev cdk deploy --all

# Staging environment
ENVIRONMENT=staging cdk deploy --all

# Production environment
ENVIRONMENT=prod cdk deploy --all
```

### **Destroy Infrastructure**

```bash
# Destroy all stacks (in reverse dependency order automatically)
cdk destroy --all

# Destroy individual stacks (in reverse dependency order)
cdk destroy outline-cicd-{ENVIRONMENT}
cdk destroy outline-application-{ENVIRONMENT}
cdk destroy outline-database-{ENVIRONMENT}
cdk destroy outline-network-{ENVIRONMENT}
```

## 📊 Stack Details

### NetworkStack

**Purpose**: Foundation networking infrastructure

**Components**:
- VPC with public, private, and isolated subnets across 2-3 AZs
- Internet Gateway and NAT Gateways (1-3 based on environment)
- Security Groups for ALB, ECS, Database, and Redis
- VPC Endpoints for S3, ECR, and CloudWatch Logs (essential only)

**Cost Optimizations**:
- Reduced AZs for dev environment (2 instead of 3, minimum required for RDS)
- Single NAT Gateway for dev environment
- Minimal VPC endpoints (only essential services)

**Outputs**:
- VPC ID
- Private/Public subnet IDs
- Security Group IDs

### DatabaseStack

**Purpose**: Database and caching infrastructure

**Components**:
- RDS PostgreSQL instance (t3.micro for dev, t3.small+ for staging/prod)
- ElastiCache Redis cluster (single node for dev, multi-node for staging/prod)
- Secrets Manager for database credentials
- Subnet groups and parameter groups

**Cost Optimizations**:
- Smallest instance types for dev environment
- Minimal storage allocation with auto-scaling
- Reduced backup retention for dev environment
- Single-node Redis for dev environment

**Outputs**:
- Database endpoint and port
- Redis endpoint and port
- Secret ARNs

### ApplicationStack

**Purpose**: Application runtime infrastructure

**Components**:
- ECS Cluster with Fargate capacity providers
- ECS Service with task definition
- Application Load Balancer with target groups
- Auto-scaling policies (CPU and memory-based)
- ECR repository for container images

**Cost Optimizations**:
- Minimal ECS task resources for dev environment (512 CPU, 1GB RAM)
- Single ECS service instance for dev environment
- Reduced auto-scaling limits for dev environment
- Minimal log retention for dev environment

**Outputs**:
- ECS cluster and service names
- Load balancer DNS name
- ECR repository URI
- Certificate ARN (if custom domain configured)

### CiCdStack

**Purpose**: Continuous integration and deployment

**Components**:
- CodeBuild project for building Docker images
- CodePipeline for automated deployments
- ECR image building and pushing
- ECS service updates

**Cost Optimizations**:
- Minimal CodeBuild compute resources (SMALL for dev, MEDIUM for staging/prod)
- Reduced log retention for dev environment
- Minimal build timeout for faster feedback

**Outputs**:
- CodeBuild project name
- CodePipeline name and URL

## 🏗️ Local Constructs

### OutlineApplicationConstruct

A reusable construct that encapsulates common Outline application patterns:

- ECR repository configuration
- Task definition with proper container setup
- IAM roles and policies
- Logging configuration

**Usage**:
```python
from constructs.outline_construct import OutlineApplicationConstruct

app_construct = OutlineApplicationConstruct(
    self, "outline-app",
    environment="dev",
    project_name="outline",
    vpc=vpc
)

# Add database secrets
app_construct.add_database_secret(database_secret.secret_arn)
app_construct.add_redis_secret(redis_secret.secret_arn)
```

## 📈 Monitoring and Logging

### CloudWatch Logs

- Application logs: `/ecs/outline-{environment}`
- CodeBuild logs: `/aws/codebuild/outline-{environment}`

### Metrics

- ECS service metrics (CPU, memory, request count)
- RDS database metrics
- ElastiCache Redis metrics
- Application Load Balancer metrics

### Alarms

The infrastructure includes basic monitoring. Consider adding:

- ECS service health alarms
- Database connection alarms
- Redis memory usage alarms
- ALB 5xx error rate alarms

## 🔒 Security

### Network Security

- All resources deployed in private subnets where possible
- Security groups with minimal required access
- VPC endpoints for AWS services to avoid internet exposure

### IAM Security

- Least privilege principle applied
- Service-specific roles for ECS tasks
- Separate execution and task roles

### Data Security

- RDS encryption at rest enabled
- Secrets Manager for credential management
- No hardcoded credentials in code

## 💡 Cost Optimization Tips

### **Development Environment**
- Use single AZ deployment
- Minimal backup retention
- Reduced log retention
- Smallest instance types
- Single NAT Gateway

### **Staging Environment**
- Use multi-AZ for testing
- Moderate backup retention
- Balanced resource allocation
- Test auto-scaling behavior

### **Production Environment**
- Full multi-AZ deployment
- Extended backup retention
- Reserved instances for predictable workloads
- Enable WAF and enhanced security

## 🚨 Troubleshooting

### Common Issues

1. **Stack Dependency Errors**
   - **Error**: "Cannot create resource X because Y doesn't exist"
   - **Solution**: Ensure stacks are deployed in the correct order

2. **VPC Endpoint Issues**
   - Ensure VPC endpoints are in private subnets
   - Check security group rules

3. **ECS Service Issues**
   - Verify task definition and container health checks
   - Check CloudWatch logs for container errors

4. **Database Connection Issues**
   - Verify security group rules
   - Check Secrets Manager permissions

5. **CI/CD Pipeline Issues**
   - Verify CodeBuild service role permissions
   - Check ECR repository access

6. **Custom Domain/SSL Issues**
   - Ensure ACM certificate is in the same region as ALB
   - Verify DNS validation records are added to external DNS provider
   - Check that DNS A/ALIAS record points to ALB DNS name
   - Confirm certificate is in "Issued" status before deployment

### Debug Commands

```bash
# Check stack status
cdk list

# View stack details
cdk diff outline-application-{ENVIRONMENT}

# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name outline-application-{ENVIRONMENT}

# View ECS service logs
aws logs tail /ecs/outline-{ENVIRONMENT} --follow

# Check cost optimization
python -c "from config.environments import get_cost_comparison; import json; print(json.dumps(get_cost_comparison(), indent=2))"

# Check certificate status (if using custom domain)
aws acm describe-certificate --certificate-arn "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"

# Check ALB DNS name for DNS configuration
aws elbv2 describe-load-balancers --names "outline-{ENVIRONMENT}-alb" --query 'LoadBalancers[0].DNSName'
```

## 🤝 Contributing

When modifying the infrastructure:

1. Test changes locally with `cdk synth`
2. Use `cdk diff` to review changes before deployment
3. Update documentation for any new components
4. Follow the existing naming conventions
5. Add appropriate CloudFormation outputs for new resources
6. **Maintain stack dependency order**
7. **Add comprehensive tagging to all resources**

## 📞 Support

For infrastructure issues:

1. Check CloudWatch logs and metrics
2. Review CloudFormation stack events
3. Verify IAM permissions
4. Check security group configurations
5. Review VPC endpoint configurations
6. **Verify stack deployment order**
7. **Check resource tagging compliance**

## 📚 Additional Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [AWS ECS Best Practices](https://docs.aws.amazon.com/ecs/latest/bestpracticesguide/)
- [AWS Cost Optimization](https://aws.amazon.com/cost-optimization/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
