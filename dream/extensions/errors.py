# SPDX-License-Identifier: Apache-2.0

from dream.core.errors import DreamError


class ExtensionError(DreamError):
    """Base exception for DREAM extension loading and contract failures."""


class ExtensionLoadError(ExtensionError):
    """Raised when a configured plugin class cannot be imported or loaded."""
