"""
Outline Application Construct

This construct encapsulates common patterns and configurations
for the Outline application, making it reusable across different stacks.
"""

from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_logs as logs,
    aws_ecr as ecr,
    Duration,
    RemovalPolicy
)
from constructs import Construct


class OutlineApplicationConstruct(Construct):
    """
    A construct that encapsulates the Outline application configuration.
    
    This construct provides a standardized way to deploy the Outline application
    with consistent configuration across different environments.
    """

    def __init__(self, scope: Construct, construct_id: str,
                 environment: str, project_name: str,
                 vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.environment = environment
        self.project_name = project_name
        self.vpc = vpc
        
        # Create the application components
        self._create_application_components()

    def _create_application_components(self):
        """Create all application-related components"""
        
        # Create ECR repository
        self.ecr_repository = self._create_ecr_repository()
        
        # Create log group
        self.log_group = self._create_log_group()
        
        # Create IAM roles
        self.task_role = self._create_task_role()
        self.execution_role = self._create_execution_role()
        
        # Create task definition
        self.task_definition = self._create_task_definition()

    def _create_ecr_repository(self) -> ecr.Repository:
        """Create ECR repository for Outline application"""
        
        return ecr.Repository(
            self, f"{self.project_name}-ecr-repo",
            repository_name=f"{self.project_name}-{self.environment}",
            description="ECR repository for Outline application",
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.DESTROY if self.environment == 'dev' else RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    max_image_count=10,
                    rule_priority=1,
                    description="Keep only 10 images"
                )
            ]
        )

    def _create_log_group(self) -> logs.LogGroup:
        """Create CloudWatch log group for application logs"""
        
        return logs.LogGroup(
            self, f"{self.project_name}-log-group",
            log_group_name=f"/ecs/{self.project_name}-{self.environment}",
            retention=logs.RetentionDays.ONE_WEEK if self.environment == 'dev' else logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY if self.environment == 'dev' else RemovalPolicy.RETAIN
        )

    def _create_task_role(self) -> iam.Role:
        """Create IAM role for ECS tasks"""
        
        role = iam.Role(
            self, f"{self.project_name}-task-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )
        
        # Add custom permissions for Outline
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket"
                ],
                resources=["*"]
            )
        )
        
        return role

    def _create_execution_role(self) -> iam.Role:
        """Create IAM role for ECS task execution"""
        
        return iam.Role(
            self, f"{self.project_name}-execution-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )

    def _create_task_definition(self) -> ecs.FargateTaskDefinition:
        """Create ECS task definition for Outline application"""
        
        task_def = ecs.FargateTaskDefinition(
            self, f"{self.project_name}-task-def",
            task_role=self.task_role,
            execution_role=self.execution_role,
            memory_limit_mib=1024 if self.environment == 'dev' else 2048,
            cpu=512 if self.environment == 'dev' else 1024,
            family=f"{self.project_name}-{self.environment}-task"
        )
        
        # Add container to task definition
        self.container = task_def.add_container(
            f"{self.project_name}-container",
            image=ecs.ContainerImage.from_ecr_repository(
                self.ecr_repository,
                tag="v0.87.0"
            ),
            container_name=f"{self.project_name}-app",
            port_mappings=[ecs.PortMapping(container_port=3000, protocol=ecs.Protocol.TCP)],
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="ecs",
                log_group=self.log_group
            ),
            environment={
                "NODE_ENV": "production",
                "PORT": "3000",
                "ENVIRONMENT": self.environment
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "wget -qO- http://localhost:3000/_health | grep -q 'OK' || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60)
            )
        )
        
        return task_def

    def add_database_secret(self, secret_arn: str):
        """Add database secret to the container"""
        
        self.container.add_secret(
            "DATABASE_URL",
            ecs.Secret.from_secrets_manager(
                secret_arn,
                field="url"
            )
        )

    def add_redis_secret(self, secret_arn: str):
        """Add Redis secret to the container"""
        
        self.container.add_secret(
            "REDIS_URL",
            ecs.Secret.from_secrets_manager(
                secret_arn,
                field="url"
            )
        )

    def get_container_definition(self) -> ecs.ContainerDefinition:
        """Get the container definition for use in other constructs"""
        
        return self.container
