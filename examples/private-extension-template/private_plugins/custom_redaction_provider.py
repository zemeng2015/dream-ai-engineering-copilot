# SPDX-License-Identifier: Apache-2.0

from dream.extensions import DefaultRedactionProvider


class CustomRedactionProvider:
    provider_name = "privatedemo-redaction"

    def __init__(self) -> None:
        self.default = DefaultRedactionProvider()

    def redact(self, text: str) -> str:
        return self.default.redact(text).replace("PrivateDemoSecret", "[REDACTED]")
