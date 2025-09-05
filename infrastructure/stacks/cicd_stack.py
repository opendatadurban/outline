"""
CI/CD Stack for Outline Infrastructure

This stack provides the CI/CD infrastructure including:
- CodePipeline for automated deployments
- CodeBuild for building and testing
- ECR image building and pushing
- ECS service updates
- GitHub webhook integration

COST OPTIMIZATION:
- Uses minimal CodeBuild compute resources (SMALL for dev, MEDIUM for staging/prod)
- Reduced log retention for dev environment
- Minimal build timeout for faster feedback
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Tags
)
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_logs as logs
from constructs import Construct


class CiCdStack(Stack):
    """CI/CD infrastructure stack for Outline application"""

    def __init__(self, scope: Construct, construct_id: str, 
                 environment: str, project_name: str,
                 ecs_cluster: ecs.Cluster,
                 ecs_service: ecs.FargateService, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_name = environment
        self.project_name = project_name
        self.ecs_cluster = ecs_cluster
        self.ecs_service = ecs_service
        
        # Create CodeBuild project
        self._create_codebuild_project()
        
        # Create CodePipeline
        self._create_codepipeline()
        
        # Create outputs
        self._create_outputs()

    def _create_codebuild_project(self):
        """Create CodeBuild project for building and testing"""
        
        # Create log group for CodeBuild
        self.codebuild_log_group = logs.LogGroup(
            self, f"{self.project_name}-codebuild-logs",
            log_group_name=f"/aws/codebuild/{self.project_name}-{self.env_name}",
            retention=logs.RetentionDays.ONE_WEEK if self.env_name == 'dev' else logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY if self.env_name == 'dev' else RemovalPolicy.RETAIN
        )
        
        # Add tags to log group
        Tags.of(self.codebuild_log_group).add("Name", f"{self.project_name}-{self.env_name}-codebuild-logs")
        Tags.of(self.codebuild_log_group).add("Type", "LogGroup")
        
        # Create service role for CodeBuild
        self.codebuild_service_role = iam.Role(
            self, f"{self.project_name}-codebuild-service-role",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSCodeBuildServiceRole")
            ]
        )
        
        # Add custom permissions for CodeBuild
        self.codebuild_service_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:PutImage",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload",
                    "ecs:DescribeServices",
                    "ecs:DescribeTaskDefinition",
                    "ecs:DescribeTasks",
                    "ecs:ListTasks",
                    "ecs:RegisterTaskDefinition",
                    "ecs:UpdateService",
                    "iam:PassRole"
                ],
                resources=["*"]
            )
        )
        
        # Add tags to service role
        Tags.of(self.codebuild_service_role).add("Name", f"{self.project_name}-{self.env_name}-codebuild-role")
        Tags.of(self.codebuild_service_role).add("Type", "IAMRole")
        
        # Cost optimization: Use smaller compute resources for dev environment
        compute_type = codebuild.ComputeType.SMALL if self.env_name == 'dev' else codebuild.ComputeType.MEDIUM
        
        # Create CodeBuild project
        self.codebuild_project = codebuild.Project(
            self, f"{self.project_name}-codebuild-project",
            project_name=f"{self.project_name}-{self.env_name}-build",
            description=f"CodeBuild project for {self.project_name} {self.env_name}",
            role=self.codebuild_service_role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_4,
                compute_type=compute_type,
                privileged=True  # Required for Docker builds
            ),
            environment_variables={
                "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                    value=self.env_name,
                    type=codebuild.BuildEnvironmentVariableType.PLAINTEXT
                ),
                "PROJECT_NAME": codebuild.BuildEnvironmentVariable(
                    value=self.project_name,
                    type=codebuild.BuildEnvironmentVariableType.PLAINTEXT
                ),
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(
                    value=self.region,
                    type=codebuild.BuildEnvironmentVariableType.PLAINTEXT
                )
            },
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "pre_build": {
                        "commands": [
                            "echo Logging in to Amazon ECR...",
                            "aws --version",
                            "aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com",
                            "REPOSITORY_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$PROJECT_NAME-$ENVIRONMENT",
                            "COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)",
                            "IMAGE_TAG=${COMMIT_HASH:=latest}"
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo Build started on `date`",
                            "echo Building the Docker image...",
                            "docker build -t $PROJECT_NAME-$ENVIRONMENT .",
                            "docker tag $PROJECT_NAME-$ENVIRONMENT:$IMAGE_TAG $REPOSITORY_URI:$IMAGE_TAG",
                            "docker tag $PROJECT_NAME-$ENVIRONMENT:$IMAGE_TAG $REPOSITORY_URI:latest"
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "echo Build completed on `date`",
                            "echo Pushing the Docker image...",
                            "docker push $REPOSITORY_URI:$IMAGE_TAG",
                            "docker push $REPOSITORY_URI:latest",
                            "echo Writing image definitions file...",
                            "printf '[{\"name\":\"%s\",\"imageUri\":\"%s\"}]' $PROJECT_NAME-$ENVIRONMENT $REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json"
                        ]
                    }
                },
                "artifacts": {
                    "files": ["imagedefinitions.json"]
                }
            }),
            cache=codebuild.Cache.local(codebuild.LocalCacheMode.DOCKER_LAYER),
            logging=codebuild.LoggingOptions(
                cloud_watch=codebuild.CloudWatchLoggingOptions(
                    log_group=self.codebuild_log_group,
                    prefix="build-log"
                )
            ),
            timeout=Duration.minutes(30)
        )
        
        # Add tags to CodeBuild project
        Tags.of(self.codebuild_project).add("Name", f"{self.project_name}-{self.env_name}-codebuild-project")
        Tags.of(self.codebuild_project).add("Type", "CodeBuildProject")

    def _create_codepipeline(self):
        """Create CodePipeline for automated deployments"""
        
        # Create artifacts
        self.artifacts_bucket = codepipeline.Artifact("SourceArtifact")
        self.build_artifacts = codepipeline.Artifact("BuildArtifact")
        
        # Reference or create CodeCommit repository as IRepository
        self.repository = codecommit.Repository.from_repository_name(
            self, f"{self.project_name}-codecommit-repo",
            repository_name=f"{self.project_name}-{self.env_name}"
        )

        # Create source action (CodeCommit)
        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name="Source",
            repository=self.repository,
            branch="main",
            output=self.artifacts_bucket
        )
        
        # Create build action
        build_action = codepipeline_actions.CodeBuildAction(
            action_name="Build",
            project=self.codebuild_project,
            input=self.artifacts_bucket,
            outputs=[self.build_artifacts],
            environment_variables={
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(
                    value=self.account,
                    type=codebuild.BuildEnvironmentVariableType.PLAINTEXT
                )
            }
        )
        
        # Create deploy action
        deploy_action = codepipeline_actions.EcsDeployAction(
            action_name="Deploy",
            service=self.ecs_service,
            image_file=self.build_artifacts.at_path("imagedefinitions.json"),
            deployment_timeout=Duration.minutes(60)
        )
        
        # Create the pipeline
        self.pipeline = codepipeline.Pipeline(
            self, f"{self.project_name}-pipeline",
            pipeline_name=f"{self.project_name}-{self.env_name}-pipeline",
            cross_account_keys=False,
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[source_action]
                ),
                codepipeline.StageProps(
                    stage_name="Build",
                    actions=[build_action]
                ),
                codepipeline.StageProps(
                    stage_name="Deploy",
                    actions=[deploy_action]
                )
            ]
        )
        
        # Add tags to pipeline
        Tags.of(self.pipeline).add("Name", f"{self.project_name}-{self.env_name}-pipeline")
        Tags.of(self.pipeline).add("Type", "CodePipeline")
        
        # Grant permissions to pipeline
        self.pipeline.role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "codebuild:BatchGetBuilds",
                    "codebuild:StartBuild"
                ],
                resources=[self.codebuild_project.project_arn]
            )
        )

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self, "CodeBuildProjectName",
            value=self.codebuild_project.project_name,
            description="CodeBuild Project Name",
            export_name=f"{self.project_name}-{self.env_name}-codebuild-project-name"
        )
        
        CfnOutput(
            self, "CodePipelineName",
            value=self.pipeline.pipeline_name,
            description="CodePipeline Name",
            export_name=f"{self.project_name}-{self.env_name}-codepipeline-name"
        )
        
        CfnOutput(
            self, "CodePipelineUrl",
            value=f"https://{self.region}.console.aws.amazon.com/codesuite/codepipeline/pipelines/{self.pipeline.pipeline_name}/view",
            description="CodePipeline Console URL",
            export_name=f"{self.project_name}-{self.env_name}-codepipeline-url"
        )
