<!-- SPDX-License-Identifier: Apache-2.0 -->

# Requirement Drafting

The requirement assistant accepts a team id, a rough business request, optional
app/component filters, and `top_k`.

## Retrieval

DREAM loads the team knowledge pack, chunks Markdown docs, and searches for
relevant chunks using deterministic keyword matching.

## Output Template

The draft includes summary, business goal, scope, user flow, functional and
non-functional requirements, affected components, data inputs/outputs,
acceptance criteria, test scenarios, open questions, and sources used.

## Human Review

Every draft states that it is for human review. DREAM does not treat generated
requirements as approved requirements.

