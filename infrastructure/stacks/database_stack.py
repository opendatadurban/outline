"""
Database Stack for Outline Infrastructure

This stack provides the database infrastructure including:
- RDS PostgreSQL instance for the main database
- ElastiCache Redis cluster for caching and queues
- Parameter groups and subnet groups
- Backup and maintenance configurations

COST OPTIMIZATION:
- Uses smallest instance types (t3.micro for dev, t3.small for staging/prod)
- Minimal storage allocation with auto-scaling
- Reduced backup retention for dev environment
- Single-node Redis for dev environment
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Tags,
    CfnTag
)
from aws_cdk import aws_rds as rds
from aws_cdk import aws_elasticache as elasticache
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class DatabaseStack(Stack):
    """Database infrastructure stack for Outline application"""

    def __init__(self, scope: Construct, construct_id: str, 
                 environment: str, project_name: str, vpc: ec2.Vpc,
                 database_security_group: ec2.SecurityGroup,
                 redis_security_group: ec2.SecurityGroup, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_name = environment
        self.project_name = project_name
        self.vpc = vpc
        self.database_security_group = database_security_group
        self.redis_security_group = redis_security_group
        
        # Create database credentials
        self._create_database_credentials()
        
        # Create Redis credentials
        self._create_redis_credentials()
        
        # Create RDS PostgreSQL instance
        self._create_postgresql_database()
        
        # Create ElastiCache Redis cluster
        self._create_redis_cluster()
        
        # Create outputs
        self._create_outputs()

    def _create_database_credentials(self):
        """Create database credentials in Secrets Manager"""
        
        self.database_secret = secretsmanager.Secret(
            self, f"{self.project_name}-database-secret",
            secret_name=f"{self.project_name}-{self.env_name}-database-credentials",
            description="Database credentials for Outline application",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "outline"}',
                generate_string_key="password",
                exclude_characters="\"@/\\",
                password_length=32
            ),
            removal_policy=RemovalPolicy.DESTROY if self.env_name == 'dev' else RemovalPolicy.RETAIN
        )
        
        # Add tags to secret
        Tags.of(self.database_secret).add("Name", f"{self.project_name}-{self.env_name}-database-secret")
        Tags.of(self.database_secret).add("Type", "Secret")
        Tags.of(self.database_secret).add("Purpose", "DatabaseCredentials")

    def _create_redis_credentials(self):
        """Create Redis connection URL in Secrets Manager"""
        
        self.redis_secret = secretsmanager.Secret(
            self, f"{self.project_name}-redis-secret",
            secret_name=f"{self.project_name}-{self.env_name}-redis-credentials",
            description=f"Redis connection URL for {self.project_name} {self.env_name} environment",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"url": "redis://"}',
                generate_string_key="password",
                exclude_characters='"@/\\'
            ),
            removal_policy=RemovalPolicy.DESTROY if self.env_name == 'dev' else RemovalPolicy.RETAIN
        )
        
        # Add tags to secret
        Tags.of(self.redis_secret).add("Name", f"{self.project_name}-{self.env_name}-redis-secret")
        Tags.of(self.redis_secret).add("Type", "Secret")
        Tags.of(self.redis_secret).add("Purpose", "RedisCredentials")

    def _create_postgresql_database(self):
        """Create RDS PostgreSQL instance"""
        
        # Create subnet group for RDS
        self.database_subnet_group = rds.SubnetGroup(
            self, f"{self.project_name}-database-subnet-group",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC if self.env_name == 'dev' else ec2.SubnetType.PRIVATE_ISOLATED
            ),
            description=f"Subnet group for {self.project_name} database",
            removal_policy=RemovalPolicy.DESTROY if self.env_name == 'dev' else RemovalPolicy.RETAIN
        )
        
        # Add tags to subnet group
        Tags.of(self.database_subnet_group).add("Name", f"{self.project_name}-{self.env_name}-database-subnet-group")
        Tags.of(self.database_subnet_group).add("Type", "SubnetGroup")
        
        # Create parameter group for PostgreSQL
        self.database_parameter_group = rds.ParameterGroup(
            self, f"{self.project_name}-database-parameter-group",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_3
            ),
            parameters={
                "timezone": "UTC",
                "log_statement": "all" if self.env_name == 'dev' else "none",
                "log_min_duration_statement": "1000" if self.env_name == 'dev' else "10000"
            }
        )
        
        # Add tags to parameter group
        Tags.of(self.database_parameter_group).add("Name", f"{self.project_name}-{self.env_name}-database-parameter-group")
        Tags.of(self.database_parameter_group).add("Type", "ParameterGroup")
        
        # Cost optimization: Use smallest instance types
        instance_class = ec2.InstanceClass.T3
        instance_size = ec2.InstanceSize.MICRO if self.env_name == 'dev' else ec2.InstanceSize.SMALL
        
        # Cost optimization: Minimal storage allocation
        storage_gb = 20 if self.env_name == 'dev' else 50
        max_storage_gb = 100 if self.env_name == 'dev' else 500
        
        # Create the PostgreSQL instance
        self.database_instance = rds.DatabaseInstance(
            self, f"{self.project_name}-database",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_3
            ),
            instance_type=ec2.InstanceType.of(instance_class, instance_size),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC if self.env_name == 'dev' else ec2.SubnetType.PRIVATE_ISOLATED
            ),
            subnet_group=self.database_subnet_group,
            parameter_group=self.database_parameter_group,
            credentials=rds.Credentials.from_secret(self.database_secret),
            database_name="outline",
            port=5432,
            allocated_storage=storage_gb,
            max_allocated_storage=max_storage_gb,
            storage_type=rds.StorageType.GP3,
            storage_encrypted=True,
            backup_retention=Duration.days(7) if self.env_name == 'dev' else Duration.days(30),
            delete_automated_backups=True if self.env_name == 'dev' else False,
            deletion_protection=False if self.env_name == 'dev' else True,
            removal_policy=RemovalPolicy.DESTROY if self.env_name == 'dev' else RemovalPolicy.RETAIN,
            auto_minor_version_upgrade=True,
            monitoring_interval=Duration.minutes(1),
            enable_performance_insights=True,
            performance_insight_retention=rds.PerformanceInsightRetention.DEFAULT,
            publicly_accessible=True if self.env_name == 'dev' else False,
            security_groups=[self.database_security_group],
            instance_identifier=f"{self.project_name}-{self.env_name}-database"
        )
        
        # Add tags to database instance
        Tags.of(self.database_instance).add("Name", f"{self.project_name}-{self.env_name}-database")
        Tags.of(self.database_instance).add("Type", "Database")
        Tags.of(self.database_instance).add("Engine", "PostgreSQL")

    def _create_redis_cluster(self):
        """Create ElastiCache Redis cluster"""
        
        # Create subnet group for ElastiCache
        self.redis_subnet_group = elasticache.CfnSubnetGroup(
            self, f"{self.project_name}-redis-subnet-group",
            description=f"Subnet group for {self.project_name} Redis cluster",
            subnet_ids=[subnet.subnet_id for subnet in self.vpc.private_subnets],
            cache_subnet_group_name=f"{self.project_name}-{self.env_name}-redis-subnet-group"
        )
        
        # Add tags to subnet group
        Tags.of(self.redis_subnet_group).add("Name", f"{self.project_name}-{self.env_name}-redis-subnet-group")
        Tags.of(self.redis_subnet_group).add("Type", "SubnetGroup")
        
        # Cost optimization: Use smallest instance types and single node for dev
        node_type = "cache.t3.micro" if self.env_name == 'dev' else "cache.t3.small"
        num_nodes = 1 if self.env_name == 'dev' else 2
        
        # Create the Redis cluster
        self.redis_cluster = elasticache.CfnCacheCluster(
            self, f"{self.project_name}-redis-cluster",
            cache_node_type=node_type,
            engine="redis",
            num_cache_nodes=num_nodes,
            port=6379,
            vpc_security_group_ids=[self.redis_security_group.security_group_id],
            cache_subnet_group_name=self.redis_subnet_group.ref,
            cache_parameter_group_name="default.redis7",
            auto_minor_version_upgrade=True,
            cluster_name=f"{self.project_name}-{self.env_name}-redis",
            tags=[
                CfnTag(key="Name", value= f"{self.project_name}-{self.env_name}-redis"),
                CfnTag(key="Environment", value=self.env_name),
                CfnTag(key="Project", value=self.project_name),
                CfnTag(key="Type", value="CacheCluster"),
                CfnTag(key="Engine", value="Redis")
            ]
        )
        
        # Add dependency on subnet group
        self.redis_cluster.add_dependency(self.redis_subnet_group)

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self, "DatabaseEndpoint",
            value=self.database_instance.instance_endpoint.hostname,
            description="RDS PostgreSQL endpoint",
            export_name=f"{self.project_name}-{self.env_name}-database-endpoint"
        )
        
        CfnOutput(
            self, "DatabasePort",
            value=str(self.database_instance.instance_endpoint.port),
            description="RDS PostgreSQL port",
            export_name=f"{self.project_name}-{self.env_name}-database-port"
        )
        
        CfnOutput(
            self, "DatabaseSecretArn",
            value=self.database_secret.secret_arn,
            description="RDS PostgreSQL secret ARN",
            export_name=f"{self.project_name}-{self.env_name}-database-secret-arn"
        )
        
        CfnOutput(
            self, "RedisSecretArn",
            value=self.redis_secret.secret_arn,
            description="Redis secret ARN",
            export_name=f"{self.project_name}-{self.env_name}-redis-secret-arn"
        )
        
        CfnOutput(
            self, "RedisEndpoint",
            value=self.redis_cluster.attr_redis_endpoint_address,
            description="ElastiCache Redis endpoint",
            export_name=f"{self.project_name}-{self.env_name}-redis-endpoint"
        )
        
        CfnOutput(
            self, "RedisPort",
            value=str(self.redis_cluster.attr_redis_endpoint_port),
            description="ElastiCache Redis port",
            export_name=f"{self.project_name}-{self.env_name}-redis-port"
        )
        
        # Output database credentials for dev environment
        if self.env_name == 'dev':
            CfnOutput(
                self, "DatabaseCredentials",
                value=f"Username: outline, Password: Check AWS Secrets Manager - {self.database_secret.secret_arn}",
                description="Database credentials for dev environment",
                export_name=f"{self.project_name}-{self.env_name}-database-credentials"
            )
