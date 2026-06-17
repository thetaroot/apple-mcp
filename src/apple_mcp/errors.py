class AppleMCPError(Exception):
    pass


class AuthError(AppleMCPError):
    pass


class ScopeError(AppleMCPError):
    pass


class ServiceUnavailableError(AppleMCPError):
    pass


class ValidationError(AppleMCPError):
    pass
