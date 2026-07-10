# SPDX-License-Identifier: Apache-2.0

from dream.connectors.lineage import ArtifactLineageRegistry
from dream.connectors.models import (
    ArtifactLineageRecord,
    ArtifactPurgeReport,
    ConnectorLifecycleResult,
    ConnectorSourceSnapshot,
    ConnectorSourceState,
)
from dream.connectors.repository import ConnectorLifecycleRepository

__all__ = [
    "ArtifactLineageRecord",
    "ArtifactLineageRegistry",
    "ArtifactPurgeReport",
    "ConnectorLifecycleRepository",
    "ConnectorLifecycleResult",
    "ConnectorLifecycleService",
    "ConnectorSourceSnapshot",
    "ConnectorSourceState",
]


def __getattr__(name: str):
    if name == "ConnectorLifecycleService":
        from dream.connectors.service import ConnectorLifecycleService

        return ConnectorLifecycleService
    raise AttributeError(name)
