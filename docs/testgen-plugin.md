<!-- SPDX-License-Identifier: Apache-2.0 -->

# TestGen Plugin

DREAM does not include a production test-generation engine. It exposes a
`TestGenProvider` interface so JTestGen or other tools can be integrated later.

## TestGenProvider

```python
class TestGenProvider(Protocol):
    provider_name: str

    def plan(self, request: TestGenRequest) -> TestGenPlan:
        ...

    def run(self, request: TestGenRequest) -> TestGenResult:
        ...
```

## MockTestGenProvider

The mock provider:

- Does not modify the target repository.
- Does not run Maven or external commands.
- Writes a fake report under `artifacts/`.
- Suggests generated test file names.
- Always requires human review.

## JTestGenAdapter Stub

`JTestGenAdapter` is a safe stub. It shows where a future external JTestGen CLI
integration can build a command, run the external tool only when explicitly
configured, write reports under `artifacts/`, and require human review.

## Future External Engines

An external engine should implement `TestGenProvider`, accept `TestGenRequest`,
write generated artifacts through controlled paths, return a structured
`TestGenResult`, and never bypass human review.

