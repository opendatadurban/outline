"""
Environment Configuration for Outline Infrastructure

This module contains configuration settings for different environments
(development, staging, production) to ensure consistent deployment
across different stages.

COST OPTIMIZATION FEATURES:
- Development: Minimal resources, single AZ, reduced backups
- Staging: Moderate resources, multi-AZ, moderate backups  
- Production: Full resources, multi-AZ, extended backups
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class EnvironmentConfig:
    """Configuration for a specific environment"""
    
    name: str
    description: str
    
    # VPC Configuration
    vpc_cidr: str
    max_azs: int
    nat_gateways: int
    
    # Database Configuration
    database_instance_class: str
    database_allocated_storage: int
    database_max_storage: int
    database_backup_retention_days: int
    database_deletion_protection: bool
    
    # Redis Configuration
    redis_node_type: str
    redis_num_nodes: int
    
    # ECS Configuration
    ecs_cpu: int
    ecs_memory_mib: int
    ecs_desired_count: int
    ecs_min_capacity: int
    ecs_max_capacity: int
    
    # Auto-scaling Configuration
    cpu_target_utilization: float
    memory_target_utilization: float
    
    # Backup and Retention
    backup_retention: bool
    log_retention_days: int
    
    # Security
    enable_https: bool
    enable_waf: bool
    
    # Cost Optimization
    estimated_monthly_cost: str
    cost_optimization_notes: str


# Environment configurations with cost-optimized settings
ENVIRONMENTS: Dict[str, EnvironmentConfig] = {
    "dev": EnvironmentConfig(
        name="dev",
        description="Development Environment - Cost Optimized",
        
        # VPC Configuration (Cost optimized)
        vpc_cidr="10.0.0.0/16",
        max_azs=2,  # Reduced from 3 to save costs
        nat_gateways=1,  # Single NAT gateway to save costs
        
        # Database Configuration (Cost optimized)
        database_instance_class="db.t3.micro",  # Smallest instance type
        database_allocated_storage=20,  # Minimal storage
        database_max_storage=100,  # Limited auto-scaling
        database_backup_retention_days=7,  # Minimal backup retention
        database_deletion_protection=False,  # Allow easy cleanup
        
        # Redis Configuration (Cost optimized)
        redis_node_type="cache.t3.micro",  # Smallest instance type
        redis_num_nodes=1,  # Single node for dev
        
        # ECS Configuration (Cost optimized)
        ecs_cpu=512,  # Minimal CPU units
        ecs_memory_mib=1024,  # Minimal memory
        ecs_desired_count=1,  # Single instance
        ecs_min_capacity=1,  # Minimal scaling
        ecs_max_capacity=3,  # Limited scaling
        
        # Auto-scaling Configuration
        cpu_target_utilization=70.0,
        memory_target_utilization=80.0,
        
        # Backup and Retention (Cost optimized)
        backup_retention=False,  # No automated backups
        log_retention_days=7,  # Minimal log retention
        
        # Security (Cost optimized)
        enable_https=False,  # HTTP only for dev
        enable_waf=False,  # No WAF for dev
        
        # Cost Optimization
        estimated_monthly_cost="$50-80",
        cost_optimization_notes="Minimal resources, single AZ, reduced backups and logging"
    ),
    
    "staging": EnvironmentConfig(
        name="staging",
        description="Staging Environment - Balanced",
        
        # VPC Configuration (Balanced)
        vpc_cidr="10.1.0.0/16",
        max_azs=3,  # Full availability
        nat_gateways=2,  # Balanced availability
        
        # Database Configuration (Balanced)
        database_instance_class="db.t3.small",  # Moderate instance type
        database_allocated_storage=50,  # Moderate storage
        database_max_storage=500,  # Reasonable auto-scaling
        database_backup_retention_days=14,  # Moderate backup retention
        database_deletion_protection=True,  # Protect staging data
        
        # Redis Configuration (Balanced)
        redis_node_type="cache.t3.small",  # Moderate instance type
        redis_num_nodes=2,  # Multi-node for availability
        
        # ECS Configuration (Balanced)
        ecs_cpu=1024,  # Moderate CPU units
        ecs_memory_mib=2048,  # Moderate memory
        ecs_desired_count=2,  # Multiple instances
        ecs_min_capacity=2,  # Moderate scaling
        ecs_max_capacity=5,  # Reasonable scaling
        
        # Auto-scaling Configuration
        cpu_target_utilization=70.0,
        memory_target_utilization=80.0,
        
        # Backup and Retention (Balanced)
        backup_retention=True,  # Automated backups
        log_retention_days=14,  # Moderate log retention
        
        # Security (Balanced)
        enable_https=True,  # HTTPS enabled
        enable_waf=False,  # No WAF for staging
        
        # Cost Optimization
        estimated_monthly_cost="$150-250",
        cost_optimization_notes="Balanced resources, multi-AZ, moderate backups and logging"
    ),
    
    "prod": EnvironmentConfig(
        name="prod",
        description="Production Environment - High Availability",
        
        # VPC Configuration (High availability)
        vpc_cidr="10.2.0.0/16",
        max_azs=3,  # Full availability
        nat_gateways=3,  # Maximum availability
        
        # Database Configuration (High availability)
        database_instance_class="db.t3.medium",  # Larger instance type
        database_allocated_storage=100,  # Larger storage
        database_max_storage=1000,  # Extensive auto-scaling
        database_backup_retention_days=30,  # Extended backup retention
        database_deletion_protection=True,  # Protect production data
        
        # Redis Configuration (High availability)
        redis_node_type="cache.t3.small",  # Moderate instance type
        redis_num_nodes=3,  # Multi-node for maximum availability
        
        # ECS Configuration (High availability)
        ecs_cpu=2048,  # Larger CPU units
        ecs_memory_mib=4096,  # Larger memory
        ecs_desired_count=3,  # Multiple instances
        ecs_min_capacity=3,  # Higher scaling
        ecs_max_capacity=10,  # Extensive scaling
        
        # Auto-scaling Configuration (Conservative for production)
        cpu_target_utilization=65.0,  # More conservative
        memory_target_utilization=75.0,  # More conservative
        
        # Backup and Retention (High availability)
        backup_retention=True,  # Automated backups
        log_retention_days=30,  # Extended log retention
        
        # Security (High availability)
        enable_https=True,  # HTTPS required
        enable_waf=True,  # WAF enabled for production
        
        # Cost Optimization
        estimated_monthly_cost="$400-600",
        cost_optimization_notes="High availability resources, multi-AZ, extensive backups and logging"
    )
}


def get_environment_config(environment: str) -> EnvironmentConfig:
    """
    Get configuration for a specific environment
    
    Args:
        environment: Environment name (dev, staging, prod)
        
    Returns:
        EnvironmentConfig object
        
    Raises:
        ValueError: If environment is not supported
    """
    if environment not in ENVIRONMENTS:
        raise ValueError(f"Unsupported environment: {environment}. "
                       f"Supported environments: {list(ENVIRONMENTS.keys())}")
    
    return ENVIRONMENTS[environment]


def list_environments() -> list:
    """List all supported environments"""
    return list(ENVIRONMENTS.keys())


def get_environment_summary(environment: str) -> Dict[str, Any]:
    """
    Get a summary of environment configuration
    
    Args:
        environment: Environment name
        
    Returns:
        Dictionary with environment summary
    """
    config = get_environment_config(environment)
    
    return {
        "name": config.name,
        "description": config.description,
        "estimated_monthly_cost": config.estimated_monthly_cost,
        "cost_optimization_notes": config.cost_optimization_notes,
        "vpc": {
            "cidr": config.vpc_cidr,
            "max_azs": config.max_azs,
            "nat_gateways": config.nat_gateways
        },
        "database": {
            "instance_class": config.database_instance_class,
            "storage_gb": config.database_allocated_storage,
            "backup_retention_days": config.database_backup_retention_days
        },
        "redis": {
            "node_type": config.redis_node_type,
            "num_nodes": config.redis_num_nodes
        },
        "ecs": {
            "cpu": config.ecs_cpu,
            "memory_mib": config.ecs_memory_mib,
            "desired_count": config.ecs_desired_count,
            "auto_scaling": f"{config.ecs_min_capacity}-{config.ecs_max_capacity}"
        },
        "security": {
            "https": config.enable_https,
            "waf": config.enable_waf
        }
    }


def get_cost_comparison() -> Dict[str, Any]:
    """
    Get cost comparison between environments
    
    Returns:
        Dictionary with cost comparison
    """
    comparison = {}
    
    for env_name in ENVIRONMENTS:
        config = ENVIRONMENTS[env_name]
        comparison[env_name] = {
            "estimated_monthly_cost": config.estimated_monthly_cost,
            "cost_optimization_notes": config.cost_optimization_notes,
            "key_features": [
                f"{config.max_azs} AZs",
                f"{config.nat_gateways} NAT Gateway(s)",
                f"{config.database_instance_class} Database",
                f"{config.redis_node_type} Redis ({config.redis_num_nodes} nodes)",
                f"{config.ecs_cpu} CPU / {config.ecs_memory_mib}MB RAM ECS",
                f"Auto-scaling: {config.ecs_min_capacity}-{config.ecs_max_capacity}",
                f"{config.database_backup_retention_days} day backup retention",
                f"{config.log_retention_days} day log retention"
            ]
        }
    
    return comparison
