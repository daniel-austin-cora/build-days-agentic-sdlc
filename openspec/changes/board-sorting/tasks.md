# Implementation tasks

## Parent work item

Before implementation begins, the team creates or uses the instructor-seeded
parent feature issue. It must link the approved specification pull request and
`openspec/changes/board-sorting/`. Do not treat this specification PR as
approved until a human has reviewed and merged it.

## Task 1: Implement API and storage sorting

**Outcome:** The feedback-list API accepts the documented sort query and both
storage adapters return deterministic results for the supported modes.

**Owned paths:**

- `src/shared/contracts.ts`
- `src/server/app.ts`
- `src/server/storage.ts`
- `tests/api.test.ts`
- `tests/storage.test.ts`

**Prohibited paths:**

- `src/client/**`
- `infra/**`
- `.github/workflows/**`
- Unrelated OpenSpec changes or feature briefs

**Dependencies:** Approved and merged `board-sorting` specification PR.

**Focused validation:**

- `npm test -- tests/api.test.ts tests/storage.test.ts`
- `npm run typecheck`

**Completion receipt:** Post to the parent issue the task owner/session, branch,
commit, changed paths, focused commands and actual results, pull-request link,
and any remaining blockers. The pull request must link the parent issue and
approved specification PR.

## Task 2: Implement the accessible board sorting experience

**Outcome:** The React board lets a user switch modes, accurately handles
selection and failures, and refreshes results in the active order after
successful feedback creation or voting.

**Owned paths:**

- `src/client/App.tsx`
- `src/client/api.ts`
- `tests/App.test.tsx`

**Prohibited paths:**

- `src/shared/**`
- `src/server/**`
- `infra/**`
- `.github/workflows/**`
- Unrelated OpenSpec changes or feature briefs

**Dependencies:** Task 1's shared/API contract and focused tests are reviewed
and integrated before client integration begins.

**Focused validation:**

- `npm test -- tests/App.test.tsx`
- `npm run typecheck`

**Completion receipt:** Post to the parent issue the task owner/session, branch,
commit, changed paths, focused commands and actual results, pull-request link,
and any remaining blockers. The pull request must link the parent issue,
approved specification PR, and Task 1 dependency.

## Task 3: Verify integrated behavior and evidence

**Outcome:** Every approved scenario has independent validation and the final
implementation evidence is understandable without the agent transcript.

**Owned paths:** No application source ownership. Any test correction must be
assigned to Task 1 or Task 2 rather than creating overlapping ownership.

**Prohibited paths:**

- `src/**`
- `infra/**`
- `.github/workflows/**`
- `openspec/changes/board-sorting/specs/**` unless a human approves a
  specification correction

**Dependencies:** Tasks 1 and 2 are complete and their pull requests are
integrated.

**Focused validation:**

- `openspec validate --all`
- `npm run check`
- `git --no-pager diff --check`
- Confirm every scenario in
  `specs/feedback-sorting/spec.md` maps to focused test evidence.

**Completion receipt:** Add the verified pull-request links, integrated commit,
checks and actual results, deployment/demo evidence when available, and
remaining limitations to the parent issue.

## Dependency order and parallel ownership

```text
Approved and merged specification PR
                  |
                  v
        Task 1: API and storage
                  |
                  v
        Task 2: client experience
                  |
                  v
        Task 3: integration evidence
```

Task 1 and Task 2 have separate primary paths, but Task 2 depends on Task 1's
reviewed API contract. Keep them sequential unless the shared contract has
already been stabilized in an integrated commit. Task 3 does not own application
files.
