"""Custom exceptions for the integrations app.

These exceptions provide clear error messages and guidance for users
when GitHub authentication issues occur.
"""


class GitHubAppDeactivatedError(Exception):
    """Raised when GitHubAppInstallation is no longer active.

    This occurs when:
    - User uninstalls the GitHub App from their organization
    - GitHub suspends the installation
    - Installation is manually deactivated

    The error message should guide the user to reinstall the App.
    """

    pass


class GitHubAuthError(Exception):
    """Raised when no valid authentication is available for a repository.

    This occurs when:
    - TrackedRepository has neither App installation nor OAuth credential
    - Both authentication methods have been revoked

    The error message should guide the user to re-add the repository.
    """

    pass


class TokenRevokedError(Exception):
    """Raised when a GitHub token has been revoked.

    This occurs when:
    - User revokes OAuth access from GitHub settings
    - GitHub App is uninstalled (detected via 401 error)
    - Token is invalidated by GitHub for security reasons

    The error message should guide the user to reconnect.
    """

    pass


class GitHubPermissionError(Exception):
    """Raised when the GitHub App lacks permission to access a resource.

    This occurs when:
    - GitHub App installation doesn't have required permissions
    - Repository has restricted access to certain data (e.g., commits)
    - Organization has SAML/SSO requirements not met

    Common error: "Resource not accessible by integration"

    The error message should guide the user to update GitHub App permissions.
    """

    pass
