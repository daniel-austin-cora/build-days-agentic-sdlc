# Design: Board sorting

## Context

The feedback board is a React client backed by an Express API, shared
TypeScript contracts, and a storage interface with in-memory and Azure Table
Storage implementations. The existing list endpoint returns items newest-first.
The workshop feature brief requires two modes, deterministic ties, invalid
query handling, and correct ordering after voting and refreshing.

Root `DESIGN.md` establishes the existing UI/API/shared-contract/storage
boundaries. This change does not introduce a new architectural boundary or
change the Azure deployment model.

## Decisions

### Use an API query as the sorting contract

The client requests `/api/feedback?sort=newest` or
`/api/feedback?sort=most-votes`. An omitted query means `newest` for
compatibility with existing callers. The API accepts exactly one value from
the supported set. Empty, unsupported, or repeated values receive HTTP 400
with the repository's structured API error shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Check the sort value and try again.",
    "fieldErrors": {
      "sort": ["Choose newest or most-voted sorting."]
    }
  }
}
```

The precise wording may follow existing validation-message conventions, but
the status, code, field key, and non-empty actionable message are part of the
contract. The UI exposes only the supported values and initializes to
`newest`. If the UI receives a `VALIDATION_ERROR` for a requested non-default
sort, it announces the problem and retries once with `newest`. It selects
`newest` only after the fallback request succeeds. A validation error for
`newest`, including the fallback attempt, is reported without another retry.
Fallback applies only when the response identifies `VALIDATION_ERROR` on the
`sort` field. Network errors, storage failures, and validation errors for
other fields are not sort-validation errors and must not trigger fallback. A
fallback request is subordinate to the selection that caused it: if the user
chooses another mode before it completes, the fallback response is stale and
must not override that newer choice.

**Alternative considered:** Sorting only in the browser. Rejected because it
would leave the API contract and independently testable server behavior
undefined.

### Keep ordering deterministic in the server storage boundary

Both storage adapters return results in the requested mode. The Azure adapter
already materializes feedback records before sorting, so ordering in the
application does not require a schema change, index, or infrastructure update.
The shared comparator must use the same rules for both adapters.

- `newest`: creation instants descending; ties by feedback ID ascending.
- `most-votes`: vote count descending; ties by creation instants descending;
  remaining ties by feedback ID ascending.

Creation timestamps are compared as instants, not by display-formatted date or
locale-dependent text. Feedback IDs are compared using ordinal lexicographic
ordering; IDs are opaque identifiers and are not parsed as dates or numbers.

**Alternative considered:** Rely on map/insertion order or Azure Table
enumeration order. Rejected because neither is a product contract and equal
sort values could produce unstable results.

### Keep sort selection in page state

The active mode is held in React state and is not written to local storage or
the URL. A full page reload starts in `newest`. Changing the control requests
the chosen mode. While a new request is pending, the board exposes a busy state
and tracks the requested mode separately from the active mode. On success, it
replaces the displayed list and commits the requested mode as active. On an
ordinary network or storage failure, it retains the last successful list and
active selection, restores the control to that selection, announces an
actionable error, and offers retry of the failed mode. The failed requested
mode must not be presented as active.

If requests overlap, only the most recently requested mode may update the
displayed list or active selection. Older responses are ignored (or cancelled
where supported). This prevents a slower earlier request from undoing the
user's latest selection.

This preserves the last known-good content and avoids implying that the API
returned the requested ordering when it did not.

### Reconcile local mutations with the active mode

After successful creation or voting, the client refetches the feedback list
using the active sort query and replaces the displayed list only when that
request succeeds. This keeps the API's ordering authoritative and avoids
maintaining a second comparator in the browser. A newly created item is placed
according to the active mode, a successful vote can move an item in
`most-votes`, and newest ordering remains based on creation time. A duplicate
vote is reflected using the server's unchanged count in the refreshed result.

If the mutation succeeds but the follow-up list request fails, the client
retains the last successfully displayed list and announces both that the
mutation succeeded and that the board could not refresh. It offers a retry of
the active list request and does not claim that the displayed order or count is
current.

### Preserve accessible status and control behavior

The selector must have a visible or programmatic label, native keyboard
operation, and an exposed selected value. The board retains its existing
loading, empty, and retryable error patterns. Sorting and voting updates that
change the displayed order are announced through an appropriate polite live
status without moving keyboard focus unexpectedly. A sort failure is announced
and retryable. Only successful list responses are announced as completed sort
changes.

## Failure Handling

- Malformed sort query: return a structured HTTP 400 validation error before
  reading storage. For a non-default sort validation error, the UI announces
  it and retries once with `newest`; a validation error on that fallback is
  shown without another retry.
- Network or storage/list failure: return/use the existing safe error
  behavior; the client retains its last successful view and active selection
  and announces a retryable error.
- Vote or creation failure: preserve existing error behavior and do not claim
  the mutation succeeded or refresh based on an uncommitted mutation.
- Mutation succeeds but list refresh fails: retain the last successful list,
  report the mutation success and refresh failure distinctly, and allow a
  retry of the active list.
- Overlapping list requests: ignore responses older than the most recent
  selection.
- Duplicate vote: use the authoritative refreshed list and unchanged count.

## Infrastructure and Security

No AVM, Bicep, GitHub Actions, Azure OIDC, managed identity, or permission
changes are needed. The feature uses existing API rate limits and storage
authorization. The sort query is limited to two enumerated values and is not
used to construct storage query text or dynamic field names.

## Validation

| Scenario group | Independent validation |
|---|---|
| Default and both deterministic orders | Fixed-data storage and API tests with different timestamps/counts and equal-value ties |
| Unsupported, empty, and repeated query | API tests assert HTTP 400 and structured `VALIDATION_ERROR` with `fieldErrors.sort` |
| Invalid non-default sort fallback | UI test verifies one announced fallback request to `newest`; another test verifies a rejected `newest` fallback does not loop |
| Sort choice accessibility and successful switch | UI test selects by accessible role/name, checks selected value, request query, rendered order, polite announcement, and unchanged focus |
| Vote-driven reorder announcement | UI test verifies a successful vote that changes an item's position is politely announced without unexpected focus movement |
| Latest overlapping sort request wins | Deferred-response UI test resolves requests out of order and verifies only the latest selection is committed |
| Create and vote while sorted | UI tests verify the active sort query is refetched after a successful mutation and that the returned order/count replaces the list |
| Refresh default | UI remount/reload test verifies initial `newest` and default API behavior |
| Failure and retry | UI test verifies ordinary failures restore the active selection, preserve the last successful list, announce the failure, and retry the failed mode |
| Mutation refresh failure | UI test verifies success and refresh failure are both reported, the last successful list remains, and retry is available |
| Existing board states | Existing empty, loading, create, vote, and retry tests remain passing |

Focused validation uses the checked-in Vitest selectors for the changed API,
storage, and UI test files. The complete repository check is
`npm run check`; OpenSpec artifacts are checked with `openspec validate --all`.

## Rollback

The change can be rolled back by removing the sort control/query support and
restoring the existing newest-first list behavior. No data migration or Azure
resource rollback is required.

## Durable Architecture Impact

None. Sorting is a feature-level behavior within the existing API and storage
boundaries; root `DESIGN.md` does not need an update.
