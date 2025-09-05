"""
Network Stack for Outline Infrastructure

This stack provides the foundational networking infrastructure including:
- VPC with public and private subnets across multiple AZs
- Internet Gateway and NAT Gateways for internet access
- Security Groups for different components
- VPC Endpoints for AWS services

COST OPTIMIZATION:
- Uses minimal AZs (2 for dev, 3 for staging/prod)
- Single NAT Gateway for dev environment
- Minimal VPC endpoints (only essential ones)
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Tags
)
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_logs as logs
from constructs import Construct


class NetworkStack(Stack):
    """Network infrastructure stack for Outline application"""

    def __init__(self, scope: Construct, construct_id: str, 
                 environment: str, project_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_name = environment
        self.project_name = project_name
        
        # Create VPC
        self.vpc = self._create_vpc()
        
        # Create Security Groups
        self._create_security_groups()
        
        # Create VPC Endpoints (only essential ones for cost optimization)
        self._create_vpc_endpoints()
        
        # Outputs
        self._create_outputs()

    def _create_vpc(self) -> ec2.Vpc:
        """Create VPC with public and private subnets"""
        
        # Cost optimization: Use fewer AZs for dev environment
        # Note: RDS requires at least 2 AZs, so dev uses 2 AZs minimum
        max_azs = 2 if self.env_name == 'dev' else 3
        nat_gateways = 1 if self.env_name == 'dev' else 2
        
        vpc = ec2.Vpc(
            self, f"{self.project_name}-vpc",
            max_azs=max_azs,
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
            nat_gateways=nat_gateways,  # Cost optimization: fewer NAT gateways
            nat_gateway_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )
        
        # Add tags to VPC
        Tags.of(vpc).add("Name", f"{self.project_name}-{self.env_name}-vpc")
        Tags.of(vpc).add("Type", "VPC")
        
        return vpc

    def _create_security_groups(self):
        """Create security groups for different components"""
        
        # Security Group for Application Load Balancer
        self.alb_security_group = ec2.SecurityGroup(
            self, f"{self.project_name}-alb-sg",
            vpc=self.vpc,
            description="Security group for Application Load Balancer",
            allow_all_outbound=True
        )
        
        # Allow HTTP and HTTPS from internet
        self.alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from internet"
        )
        
        self.alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from internet"
        )
        
        # Security Group for ECS Tasks
        self.ecs_security_group = ec2.SecurityGroup(
            self, f"{self.project_name}-ecs-sg",
            vpc=self.vpc,
            description="Security group for ECS tasks",
            allow_all_outbound=True
        )
        
        # Allow traffic from ALB to ECS tasks
        self.ecs_security_group.add_ingress_rule(
            peer=self.alb_security_group,
            connection=ec2.Port.tcp(3000),
            description="Allow traffic from ALB to ECS tasks"
        )
        
        # Security Group for Database
        self.database_security_group = ec2.SecurityGroup(
            self, f"{self.project_name}-database-sg",
            vpc=self.vpc,
            description="Security group for RDS database",
            allow_all_outbound=False
        )
        
        # Allow PostgreSQL access from ECS tasks
        self.database_security_group.add_ingress_rule(
            peer=self.ecs_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL access from ECS tasks"
        )
        
        # For dev environment, allow PostgreSQL access from internet
        if self.env_name == 'dev':
            self.database_security_group.add_ingress_rule(
                peer=ec2.Peer.any_ipv4(),
                connection=ec2.Port.tcp(5432),
                description="Allow PostgreSQL access from internet (dev only)"
            )
        
        # Security Group for Redis
        self.redis_security_group = ec2.SecurityGroup(
            self, f"{self.project_name}-redis-sg",
            vpc=self.vpc,
            description="Security group for ElastiCache Redis",
            allow_all_outbound=False
        )
        
        # Allow Redis access from ECS tasks
        self.redis_security_group.add_ingress_rule(
            peer=self.ecs_security_group,
            connection=ec2.Port.tcp(6379),
            description="Allow Redis access from ECS tasks"
        )
        
        # Add tags to security groups
        for sg in [self.alb_security_group, self.ecs_security_group, 
                   self.database_security_group, self.redis_security_group]:
            Tags.of(sg).add("Name", f"{self.project_name}-{self.env_name}-{sg.node.id}")
            Tags.of(sg).add("Type", "SecurityGroup")

    def _create_vpc_endpoints(self):
        """Create VPC endpoints for AWS services (cost-optimized)"""
        
        # S3 VPC Endpoint (Gateway) - Essential for ECR and other services
        self.s3_endpoint = ec2.GatewayVpcEndpoint(
            self, f"{self.project_name}-s3-endpoint",
            vpc=self.vpc,
            service=ec2.GatewayVpcEndpointAwsService.S3
        )
        Tags.of(self.s3_endpoint).add("Name", f"{self.project_name}-{self.env_name}-s3-endpoint")
        Tags.of(self.s3_endpoint).add("Type", "VPCEndpoint")
        
        # ECR VPC Endpoint (Interface) - Essential for pulling images
        self.ecr_endpoint = ec2.InterfaceVpcEndpoint(
            self, f"{self.project_name}-ecr-endpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.ECR,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )
        Tags.of(self.ecr_endpoint).add("Name", f"{self.project_name}-{self.env_name}-ecr-endpoint")
        Tags.of(self.ecr_endpoint).add("Type", "VPCEndpoint")
        
        # ECR Docker VPC Endpoint (Interface) - Essential for Docker operations
        self.ecr_docker_endpoint = ec2.InterfaceVpcEndpoint(
            self, f"{self.project_name}-ecr-docker-endpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )
        Tags.of(self.ecr_docker_endpoint).add("Name", f"{self.project_name}-{self.env_name}-ecr-docker-endpoint")
        Tags.of(self.ecr_docker_endpoint).add("Type", "VPCEndpoint")
        
        # CloudWatch Logs VPC Endpoint (Interface) - Essential for logging
        self.cloudwatch_endpoint = ec2.InterfaceVpcEndpoint(
            self, f"{self.project_name}-cloudwatch-endpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )
        Tags.of(self.cloudwatch_endpoint).add("Name", f"{self.project_name}-{self.env_name}-cloudwatch-endpoint")
        Tags.of(self.cloudwatch_endpoint).add("Type", "VPCEndpoint")

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self, "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name=f"{self.project_name}-{self.env_name}-vpc-id"
        )
        
        CfnOutput(
            self, "PrivateSubnets",
            value=",".join([subnet.subnet_id for subnet in self.vpc.private_subnets]),
            description="Private subnet IDs",
            export_name=f"{self.project_name}-{self.env_name}-private-subnets"
        )
        
        CfnOutput(
            self, "PublicSubnets",
            value=",".join([subnet.subnet_id for subnet in self.vpc.public_subnets]),
            description="Public subnet IDs",
            export_name=f"{self.project_name}-{self.env_name}-public-subnets"
        )
        
        CfnOutput(
            self, "EcsSecurityGroupId",
            value=self.ecs_security_group.security_group_id,
            description="ECS Security Group ID",
            export_name=f"{self.project_name}-{self.env_name}-ecs-sg-id"
        )
        
        CfnOutput(
            self, "AlbSecurityGroupId",
            value=self.alb_security_group.security_group_id,
            description="ALB Security Group ID",
            export_name=f"{self.project_name}-{self.env_name}-alb-sg-id"
        )
        
        CfnOutput(
            self, "DatabaseSecurityGroupId",
            value=self.database_security_group.security_group_id,
            description="Database Security Group ID",
            export_name=f"{self.project_name}-{self.env_name}-database-sg-id"
        )
        
        CfnOutput(
            self, "RedisSecurityGroupId",
            value=self.redis_security_group.security_group_id,
            description="Redis Security Group ID",
            export_name=f"{self.project_name}-{self.env_name}-redis-sg-id"
        )
