# Security Fix: Separation of RDS Master and Application Credentials

## Overview
This fix addresses a critical security vulnerability where the ECS backend task was granted access to the RDS master credential, violating the principle of least privilege.

## Changes Made

### 1. Database Construct (`cdk/cdk_goat_service/cdk_constructs/db.py`)
- **Renamed** `db_secret` to `db_master_secret` to clearly identify it as the master credential
- **Created** a new `db_app_secret` for application-level database access with limited privileges
- **Exposed** both `db_master_secret` and `db_app_secret` as properties of the DBConstruct class

### 2. Containers Construct (`cdk/cdk_goat_service/cdk_constructs/containers.py`)
- **Removed** the import of the master secret (`db.secret`)
- **Added** `db_app_secret` parameter to the constructor
- **Changed** the `grant_read` call from master secret to application secret (line 98)
- **Updated** all container secret injections to use `db_app_secret` instead of `db_secret` (lines 140-159)

### 3. Stack (`cdk/cdk_goat_service/cdk_goat_stack.py`)
- **Added** `db_app_secret=db_construct.db_app_secret` parameter when instantiating ContainersConstruct

## Security Impact

### Before Fix
- The ECS task role had explicit read access to the RDS master secret
- The master credential (username and password) was injected into the container environment
- Compromise of the backend application would grant attackers full database administrative privileges
- SQL injection vulnerabilities could be exploited to gain master-level database access

### After Fix
- The ECS task role only has access to the application-level secret
- The master credential is isolated and not accessible to the application runtime
- The application uses a separate credential intended for limited-privilege operations
- Reduces the blast radius of application compromise

## Additional Steps Required

**IMPORTANT**: This infrastructure change creates a separate application secret, but additional steps are required to complete the security mitigation:

1. **Create the application database user**: After the RDS instance is created, connect using the master credential and create a limited-privilege user:
   ```sql
   CREATE USER app_user WITH PASSWORD '<password_from_db_app_secret>';
   GRANT CONNECT ON DATABASE defaultdb TO app_user;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;
   ```

2. **Update the application secret**: Ensure the password in `db_app_secret` matches the password set for the `app_user` in the database.

3. **Rotate the master credential**: After confirming the application works with the new user, rotate the master credential to ensure any previous exposure is mitigated.

4. **Implement secret rotation**: Consider implementing AWS Secrets Manager rotation for both secrets.

## Testing

After deployment:
1. Verify the application can connect to the database using the new application secret
2. Verify the ECS task role cannot access the master secret
3. Test that the application has only the necessary database permissions
4. Confirm that attempting to perform administrative operations from the application fails

## Principle of Least Privilege

This fix implements the principle of least privilege by:
- Separating administrative credentials from application credentials
- Limiting the ECS task role to only the secrets it needs
- Reducing the impact of potential application compromise
- Following AWS security best practices for credential management
