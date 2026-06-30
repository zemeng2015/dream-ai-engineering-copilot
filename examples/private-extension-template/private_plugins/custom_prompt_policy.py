# SPDX-License-Identifier: Apache-2.0


class CustomPromptPolicy:
    provider_name = "privatedemo-prompt-policy"

    def apply(self, prompt: str) -> str:
        return f"{prompt}\n\nPolicy: use TeamTemplate knowledge only and cite retrieved sources."
