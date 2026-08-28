"""Database CDK construct module."""

import json

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as sme
from constructs import Construct

from cdk.cdk_goat_service.cdk_constructs.constants import (
    CLUSTER_DB_NAME,
    CLUSTER_MASTER_USER_NAME,
)


class DBConstruct(Construct):
    """Database CDK construct class."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.IVpc,
        security_group: ec2.ISecurityGroup,
        *,
        prefix=None,
    ):
        """Construct initialization."""
        super().__init__(scope, id)

        db_master_secret = sme.Secret(
            self,
            "DBMasterSecret",
            generate_secret_string=sme.SecretStringGenerator(
                exclude_punctuation=True,
                include_space=False,
                secret_string_template=json.dumps(
                    {
                        "username": CLUSTER_MASTER_USER_NAME,
                    }
                ),
                generate_string_key="password",
            ),
        )

        db = rds.DatabaseInstance(
            self,
            "DB",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15
            ),
            storage_encrypted=False,
            iam_authentication=False,
            database_name=CLUSTER_DB_NAME,
            credentials=rds.Credentials.from_secret(
                secret=db_master_secret, username="master"
            ),
            backup_retention=cdk.Duration.days(7),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
            ),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            vpc=vpc,
            publicly_accessible=True,
            allow_major_version_upgrade=False,
            auto_minor_version_upgrade=False,
            security_groups=[security_group],
            deletion_protection=False,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # Create a separate application-level secret with limited privileges
        # This secret should be used by the application instead of the master credential
        db_app_secret = sme.Secret(
            self,
            "DBAppSecret",
            generate_secret_string=sme.SecretStringGenerator(
                exclude_punctuation=True,
                include_space=False,
                secret_string_template=json.dumps(
                    {
                        "username": "app_user",
                        "dbname": CLUSTER_DB_NAME,
                        "host": db.instance_endpoint.hostname,
                        "port": db.instance_endpoint.port,
                    }
                ),
                generate_string_key="password",
            ),
        )

        cdk.CfnOutput(self, "DBInstanceEndpoint", value=db.instance_endpoint.hostname)
        cdk.CfnOutput(self, "DBName", value=CLUSTER_DB_NAME)

        self.db_cluster = db
        self.db_master_secret = db_master_secret
        self.db_app_secret = db_app_secret
