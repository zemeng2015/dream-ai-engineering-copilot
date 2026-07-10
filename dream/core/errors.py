# SPDX-License-Identifier: Apache-2.0


class DreamError(Exception):
    """Base exception for DREAM."""


class NotFoundError(DreamError):
    """Raised when a requested project resource is missing."""


class PathTraversalError(DreamError):
    """Raised when a file path escapes the DREAM project root."""


class AccessDeniedError(DreamError):
    """Raised when identity, role, or source ACL policy denies an operation."""


class DlpBlockedError(DreamError):
    """Raised when versioned DLP policy blocks content from crossing a boundary."""


class ProviderConfigurationError(DreamError):
    """Raised when an optional provider is not configured."""


class SecurityEvidenceUnavailableError(ProviderConfigurationError):
    """Raised when a required private security decision cannot be persisted."""


class ProviderRequestError(DreamError):
    """Raised when an optional provider request fails."""
