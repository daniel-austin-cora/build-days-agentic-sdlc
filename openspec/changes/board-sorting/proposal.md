# Proposal: Board sorting

## Why

Workshop participants can currently browse feedback only in newest-first order.
They need a way to find recently submitted ideas or quickly see which ideas
have received the most votes. Sorting makes the existing feedback board more
useful during team discussion without expanding it into a general-purpose
filtering or ranking product.

## What Changes

- Add two supported feedback-list sort modes: `newest` and `most-votes`.
- Keep `newest` as the default when no sort mode is requested.
- Allow the React board to select and display the active sort mode.
- Validate the sort query at the API boundary and return a clear client error
  for unsupported or repeated values.
- If the UI receives a sort-validation error for a non-default mode, announce
  the issue and retry once with `newest`; never retry that fallback more than
  once.
- Define stable tie-breakers so identical data always produces the same order.
- Preserve the selected mode as in-memory page state only; a full refresh starts
  in `newest`.
- Refetch the active sort after a successful submission or vote, and keep the
  active ordering correct.
- Ensure rapid sort changes cannot let an older response overwrite the latest
  selection.
- Announce successful sort and mutation-driven order changes accessibly
  without moving keyboard focus.

## Capabilities

### New Capabilities

- `feedback-sorting`: A participant can select supported sort modes for the
  feedback board and receives deterministic ordering across API requests,
  submissions, votes, and page reloads.

### Modified Capabilities

None.

## Non-Goals

- Adding arbitrary sort fields, filtering, pagination, drag-and-drop ordering,
  or personalized preferences.
- Persisting the selected mode across page reloads or across devices.
- Changing feedback creation, voting eligibility, vote persistence, or the
  existing feedback data shape.
- Adding Azure resources, AVM modules, OIDC permissions, workflow changes, or
  infrastructure configuration.
- Requiring database-side sorting or adding a new persistence technology.

## Impact

- **Application:** Adds a sort query to the existing feedback-list API and an
  accessible sort control to the React board.
- **Shared contract and storage:** Defines supported sort values and applies
  deterministic ordering to results from the existing in-memory and Azure
  Table Storage adapters.
- **Tests:** Adds fixed-data tests for both orders, tie-breakers, invalid query
  shapes and one-time UI fallback, vote/submission refresh behavior, overlapping
  requests, refresh defaults, accessible order announcements, and retry/failure
  behavior; preserves existing loading, empty, and retry states.
- **Infrastructure and identity:** No impact. The feature uses the existing
  application and storage path.
- **Documentation:** Update only feature-specific guidance if implementation
  reveals a user-facing behavior not covered by this change.
