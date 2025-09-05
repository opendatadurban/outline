"""
Application Stack for Outline Infrastructure

This stack provides the application infrastructure including:
- ECS Cluster with Fargate capacity providers
- ECS Service for the Outline application
- Application Load Balancer
- Task definition with proper configuration
- Auto-scaling policies

COST OPTIMIZATION:
- Uses minimal ECS task resources (512 CPU units, 1GB RAM for dev)
- Single ECS service instance for dev environment
- Reduced auto-scaling limits for dev environment
- Minimal log retention for dev environment
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Tags
)
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_applicationautoscaling as appscaling
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_servicediscovery as servicediscovery
from constructs import Construct
from typing import Optional

class ApplicationStack(Stack):
    """Application infrastructure stack for Outline on ECS"""

    def __init__(self, scope: Construct, construct_id: str, 
                 environment: str, project_name: str, vpc: ec2.Vpc,
                 alb_security_group: ec2.SecurityGroup,
                 ecs_security_group: ec2.SecurityGroup,
                 database_secret: secretsmanager.Secret,
                 redis_secret: secretsmanager.Secret,
                 database_host: str,
                 database_port: str,
                 redis_host: str,
                 redis_port: str,
                 domain_name: Optional[str]  = None,
                 certificate_arn: Optional[str]  = None,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_name = environment
        self.project_name = project_name
        self.vpc = vpc
        self.alb_security_group = alb_security_group
        self.ecs_security_group = ecs_security_group
        self.database_secret = database_secret
        self.redis_secret = redis_secret
        self.database_host = database_host
        self.database_port = database_port
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.domain_name = domain_name
        self.certificate_arn = certificate_arn
        
        # Create ECS Cluster
        self._create_ecs_cluster()

        # Create ECR Repository
        self._create_ecr_repository()

        # Create Task Definition
        self._create_task_definition()
        
        # Create ECS Service
        self._create_ecs_service()
        
        # Create Application Load Balancer
        self._create_load_balancer()
        
        # Create Auto-scaling
        self._create_auto_scaling()
        
        # Create outputs
        self._create_outputs()

    def _create_ecs_cluster(self):
        """Create ECS Cluster with Fargate capacity providers"""
        
        self.ecs_cluster = ecs.Cluster(
            self, f"{self.project_name}-cluster",
            vpc=self.vpc,
            cluster_name=f"{self.project_name}-{self.env_name}-cluster",
            container_insights=True,
            # default_cloud_map_namespace=ecs.CloudMapNamespaceOptions(
            #     name=f"{self.project_name}-{self.env_name}",
            #     type=servicediscovery.NamespaceType.DNS_PRIVATE
            # )
        )
        
        # Add tags to cluster
        Tags.of(self.ecs_cluster).add("Name", f"{self.project_name}-{self.env_name}-cluster")
        Tags.of(self.ecs_cluster).add("Type", "ECSCluster")

    def _create_ecr_repository(self):
        """Reference existing ECR repository by name (do not create)."""

        # Import an existing repository named <project>-<env> (e.g. outline-dev)
        self.ecr_repository = ecr.Repository.from_repository_name(
            self, f"{self.project_name}-repository",
            repository_name=f"{self.project_name}-{self.env_name}"
        )

        # Add tags to repository
        Tags.of(self.ecr_repository).add("Name", f"{self.project_name}-{self.env_name}-ecr-repo")
        Tags.of(self.ecr_repository).add("Type", "ECRRepository")

    def _create_task_definition(self):
        """Create ECS Task Definition for Outline application"""
        
        # Create log group
        self.log_group = logs.LogGroup(
            self, f"{self.project_name}-logs",
            log_group_name=f"/ecs/{self.project_name}-{self.env_name}",
            retention=logs.RetentionDays.ONE_WEEK if self.env_name == 'dev' else logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY if self.env_name == 'dev' else RemovalPolicy.RETAIN
        )
        
        # Add tags to log group
        Tags.of(self.log_group).add("Name", f"{self.project_name}-{self.env_name}-logs")
        Tags.of(self.log_group).add("Type", "LogGroup")
        
        # Create task role
        self.task_role = iam.Role(
            self, f"{self.project_name}-task-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )
        
        # Add custom permissions for Outline
        self.task_role.add_to_policy(
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
        
        # Add tags to task role
        Tags.of(self.task_role).add("Name", f"{self.project_name}-{self.env_name}-task-role")
        Tags.of(self.task_role).add("Type", "IAMRole")
        
        # Create execution role
        self.execution_role = iam.Role(
            self, f"{self.project_name}-execution-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )
        
        # Add tags to execution role
        Tags.of(self.execution_role).add("Name", f"{self.project_name}-{self.env_name}-execution-role")
        Tags.of(self.execution_role).add("Type", "IAMRole")
        
        # Cost optimization: Use minimal resources for dev environment
        cpu_units = 512 if self.env_name == 'dev' else 1024
        memory_mib = 1024 if self.env_name == 'dev' else 2048
        
        # Create task definition
        self.task_definition = ecs.FargateTaskDefinition(
            self, f"{self.project_name}-task-def",
            task_role=self.task_role,
            execution_role=self.execution_role,
            memory_limit_mib=memory_mib,
            cpu=cpu_units,
            family=f"{self.project_name}-{self.env_name}-task"
        )
        
        # Add tags to task definition
        Tags.of(self.task_definition).add("Name", f"{self.project_name}-{self.env_name}-task-def")
        Tags.of(self.task_definition).add("Type", "TaskDefinition")
        
        # Create application secrets for Outline-specific configuration
        self.app_secret = secretsmanager.Secret(
            self, f"{self.project_name}-app-secret",
            secret_name=f"{self.project_name}-{self.env_name}-app-credentials",
            description="Application secrets for Outline (SECRET_KEY, UTILS_SECRET, etc.)",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"secret_key": "", "utils_secret": ""}',
                generate_string_key="secret_key",
                exclude_characters="\"@/\\",
                password_length=32
            ),
            removal_policy=RemovalPolicy.DESTROY if self.env_name == 'dev' else RemovalPolicy.RETAIN
        )
        
        # Create a separate secret for utils_secret to generate it like secret_key
        self.utils_secret = secretsmanager.Secret(
            self, f"{self.project_name}-utils-secret",
            secret_name=f"{self.project_name}-{self.env_name}-utils-credentials",
            description="Utils secret for Outline application",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"utils_secret": ""}',
                generate_string_key="utils_secret",
                exclude_characters="\"@/\\",
                password_length=32
            ),
            removal_policy=RemovalPolicy.DESTROY if self.env_name == 'dev' else RemovalPolicy.RETAIN
        )
        
        # Add tags to app secret
        Tags.of(self.app_secret).add("Name", f"{self.project_name}-{self.env_name}-app-secret")
        Tags.of(self.app_secret).add("Type", "Secret")
        Tags.of(self.app_secret).add("Purpose", "ApplicationCredentials")
        
        # Add tags to utils secret
        Tags.of(self.utils_secret).add("Name", f"{self.project_name}-{self.env_name}-utils-secret")
        Tags.of(self.utils_secret).add("Type", "Secret")
        Tags.of(self.utils_secret).add("Purpose", "UtilsCredentials")

        # Add container to task definition
        self.container = self.task_definition.add_container(
            f"{self.project_name}-container",
            # Build image from local Dockerfile via CDK assets to avoid manual ECR pushes
            image=ecs.ContainerImage.from_ecr_repository(
                self.ecr_repository,
                tag="latest"
            ),
            container_name=f"{self.project_name}-app",
            port_mappings=[ecs.PortMapping(
                container_port=3000, 
                protocol=ecs.Protocol.TCP,
                name=f"{self.project_name}-app"
            )],
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="ecs",
                log_group=self.log_group
            ),
            environment={
                "NODE_ENV": "production",
                "PORT": "3000",
                "ENVIRONMENT": self.env_name,
                "ENABLE_UPDATES": "true",
                "DEFAULT_LANGUAGE": "en_US",
                "FILE_STORAGE_UPLOAD_MAX_SIZE": "26214400",  # 25MB
                "AWS_REGION": self.region,
                "AWS_S3_ACL": "private",
                "AWS_S3_FORCE_PATH_STYLE": "false",
                "SMTP_SECURE": "true",
                "PGSSLMODE": "require",
                # Construct REDIS_URL from known endpoint
                "REDIS_URL": f"redis://{self.redis_host}:{self.redis_port}"
            },
            secrets={
                "SECRET_KEY": ecs.Secret.from_secrets_manager(
                    self.app_secret,
                    field="secret_key"
                ),
                "UTILS_SECRET": ecs.Secret.from_secrets_manager(
                    self.utils_secret,
                    field="utils_secret"
                ),
                "DATABASE_URL": ecs.Secret.from_secrets_manager(
                    self.database_secret,
                    field="DATABASE_URL"
                )
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "wget -qO- http://localhost:3000/_health | grep -q 'OK' || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60)
            )
        )

    def _create_ecs_service(self):
        """Create ECS Service for Outline application"""
        
        # Cost optimization: Use minimal instances for dev environment
        desired_count = 1 if self.env_name == 'dev' else 2
        
        # Create service
        self.ecs_service = ecs.FargateService(
            self, f"{self.project_name}-service",
            cluster=self.ecs_cluster,
            task_definition=self.task_definition,
            service_name=f"{self.project_name}-{self.env_name}-service",
            desired_count=desired_count,
            min_healthy_percent=50,
            max_healthy_percent=200,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[self.ecs_security_group],
            assign_public_ip=False,
            service_connect_configuration=ecs.ServiceConnectProps(
                namespace=f"{self.project_name}-{self.env_name}",
                services=[
                    ecs.ServiceConnectService(
                        port_mapping_name=f"{self.project_name}-app",
                        port=3000,
                        discovery_name=f"{self.project_name}-app"
                    )
                ]
            )
        )
        
        # Add tags to service
        Tags.of(self.ecs_service).add("Name", f"{self.project_name}-{self.env_name}-service")
        Tags.of(self.ecs_service).add("Type", "ECSService")

    def _create_load_balancer(self):
        """Create Application Load Balancer"""
        
        certificate = None
        if self.domain_name:
            if self.certificate_arn:
                certificate = acm.Certificate.from_certificate_arn(
                    self, f"{self.project_name}-imported-cert", self.certificate_arn
                )
            else:
                certificate = acm.Certificate(
                    self, f"{self.project_name}-certificate",
                    domain_name=self.domain_name,
                    validation=acm.CertificateValidation.from_dns()
                )
                # Note: For external DNS, create the ACM validation CNAMEs manually.

        # Create ALB
        self.load_balancer = elbv2.ApplicationLoadBalancer(
            self, f"{self.project_name}-alb",
            vpc=self.vpc,
            internet_facing=True,
            load_balancer_name=f"{self.project_name}-{self.env_name}-alb",
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            security_group=self.alb_security_group
        )
        
        # Add tags to load balancer
        Tags.of(self.load_balancer).add("Name", f"{self.project_name}-{self.env_name}-alb")
        Tags.of(self.load_balancer).add("Type", "LoadBalancer")
        
        # Create target group
        self.target_group = elbv2.ApplicationTargetGroup(
            self, f"{self.project_name}-target-group",
            vpc=self.vpc,
            port=3000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/_health",
                port="3000",
                protocol=elbv2.Protocol.HTTP,
                healthy_http_codes="200",
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
                timeout=Duration.seconds(5),
                interval=Duration.seconds(30)
            ),
            deregistration_delay=Duration.seconds(30)
        )
        
        # Add tags to target group
        Tags.of(self.target_group).add("Name", f"{self.project_name}-{self.env_name}-target-group")
        Tags.of(self.target_group).add("Type", "TargetGroup")
        
        # Attach ECS service to the target group
        self.ecs_service.attach_to_application_target_group(self.target_group)

        # ECS service will automatically register with the target group
        # when the load balancer is attached to the service
        
        # Create HTTP listener
        if certificate is not None:
            # Redirect HTTP to HTTPS when SSL is configured
            self.listener = self.load_balancer.add_listener(
                f"{self.project_name}-listener",
                port=80,
                protocol=elbv2.ApplicationProtocol.HTTP,
                default_action=elbv2.ListenerAction.redirect(
                    protocol="HTTPS", port="443", permanent=True
                )
            )
        else:
            # No SSL configured, forward HTTP to target group
            self.listener = self.load_balancer.add_listener(
                f"{self.project_name}-listener",
                port=80,
                protocol=elbv2.ApplicationProtocol.HTTP,
                default_action=elbv2.ListenerAction.forward([self.target_group])
            )
        
        # Add tags to HTTP listener
        Tags.of(self.listener).add("Name", f"{self.project_name}-{self.env_name}-listener")
        Tags.of(self.listener).add("Type", "Listener")
        
        # Add HTTPS listener (port 443) when certificate present
        if certificate is not None:
            self.https_listener = self.load_balancer.add_listener(
                f"{self.project_name}-https-listener",
                port=443,
                protocol=elbv2.ApplicationProtocol.HTTPS,
                certificates=[elbv2.ListenerCertificate.from_acm_certificate(certificate)],
                default_action=elbv2.ListenerAction.forward([self.target_group])
            )
            # Add tags to HTTPS listener
            Tags.of(self.https_listener).add("Name", f"{self.project_name}-{self.env_name}-https-listener")
            Tags.of(self.https_listener).add("Type", "Listener")

        # Ensure the application URL is configured after the load balancer exists
        url_value = (
            f"https://{self.domain_name}" if self.domain_name else f"http://{self.load_balancer.load_balancer_dns_name}"
        )
        self.container.add_environment("URL", url_value)

    def _create_auto_scaling(self):
        """Create auto-scaling policies for the ECS service"""
        
        # Cost optimization: Use minimal scaling limits for dev environment
        min_capacity = 1 if self.env_name == 'dev' else 2
        max_capacity = 3 if self.env_name == 'dev' else 5
        
        # Create scalable target
        self.scalable_target = appscaling.ScalableTarget(
            self, f"{self.project_name}-scalable-target",
            service_namespace=appscaling.ServiceNamespace.ECS,
            scalable_dimension="ecs:service:DesiredCount",
            resource_id=f"service/{self.ecs_cluster.cluster_name}/{self.ecs_service.service_name}",
            min_capacity=min_capacity,
            max_capacity=max_capacity
        )
        
        # Add tags to scalable target
        Tags.of(self.scalable_target).add("Name", f"{self.project_name}-{self.env_name}-scalable-target")
        Tags.of(self.scalable_target).add("Type", "ScalableTarget")
        
        # Create CPU-based scaling policy
        self.cpu_scaling = appscaling.TargetTrackingScalingPolicy(
            self, f"{self.project_name}-cpu-scaling",
            scaling_target=self.scalable_target,
            target_value=70.0,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
            predefined_metric=appscaling.PredefinedMetric.ECS_SERVICE_AVERAGE_CPU_UTILIZATION
        )
        
        # Create memory-based scaling policy
        self.memory_scaling = appscaling.TargetTrackingScalingPolicy(
            self, f"{self.project_name}-memory-scaling",
            scaling_target=self.scalable_target,
            target_value=80.0,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
            predefined_metric=appscaling.PredefinedMetric.ECS_SERVICE_AVERAGE_MEMORY_UTILIZATION
        )

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self, "EcsClusterName",
            value=self.ecs_cluster.cluster_name,
            description="ECS Cluster Name",
            export_name=f"{self.project_name}-{self.env_name}-ecs-cluster-name"
        )
        
        CfnOutput(
            self, "EcsServiceName",
            value=self.ecs_service.service_name,
            description="ECS Service Name",
            export_name=f"{self.project_name}-{self.env_name}-ecs-service-name"
        )
        
        CfnOutput(
            self, "LoadBalancerDnsName",
            value=self.load_balancer.load_balancer_dns_name,
            description="Application Load Balancer DNS Name",
            export_name=f"{self.project_name}-{self.env_name}-alb-dns-name"
        )
        
        CfnOutput(
            self, "EcrRepositoryUri",
            value=self.ecr_repository.repository_uri,
            description="ECR Repository URI",
            export_name=f"{self.project_name}-{self.env_name}-ecr-repo-uri"
        )
        
        CfnOutput(
            self, "AppSecretArn",
            value=self.app_secret.secret_arn,
            description="Application secrets ARN (SECRET_KEY)",
            export_name=f"{self.project_name}-{self.env_name}-app-secret-arn"
        )
        
        CfnOutput(
            self, "UtilsSecretArn",
            value=self.utils_secret.secret_arn,
            description="Utils secrets ARN (UTILS_SECRET)",
            export_name=f"{self.project_name}-{self.env_name}-utils-secret-arn"
        )
