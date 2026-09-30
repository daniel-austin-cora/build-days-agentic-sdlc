## ADDED Requirements

### Requirement: Feedback list sorting

The application SHALL let a workshop user view feedback in either newest-first
or most-voted-first order. The default mode SHALL be newest-first. Every mode
SHALL produce deterministic ordering for equal primary sort values.

#### Scenario: Default mode shows newest feedback first

- **WHEN** a user opens the feedback board without choosing a sort mode
- **THEN** the board requests and displays feedback in newest-first order

#### Scenario: Newest mode breaks timestamp ties deterministically

- **WHEN** two or more feedback items have the same creation instant in
  `newest` mode
- **THEN** those items appear in ascending lexicographic ID order

#### Scenario: Most-voted mode orders feedback by vote count

- **WHEN** a user selects `Most votes`
- **THEN** the API returns feedback in descending vote-count order

#### Scenario: Most-voted mode breaks ties deterministically

- **WHEN** two or more feedback items have the same vote count in `most-votes`
  mode
- **THEN** items with newer creation instants appear first, and items still
  tied appear in ascending lexicographic ID order

#### Scenario: Sort control exposes the selected mode accessibly

- **WHEN** the feedback board is available
- **THEN** the sort control has an accessible name, exposes the selected
  supported mode, and can be operated by keyboard

#### Scenario: Sort changes are announced without moving focus

- **WHEN** a successful sort changes the displayed order
- **THEN** the board politely announces the active sort mode to assistive
  technology without moving keyboard focus from the sort control

#### Scenario: Vote-driven order changes are announced

- **WHEN** a successful vote refresh changes an item's position in the list
- **THEN** the board politely announces that the list was updated without
  moving keyboard focus unexpectedly

### Requirement: Sort query validation

The feedback-list API SHALL accept a single optional `sort` query parameter
whose supported values are `newest` and `most-votes`. An omitted parameter
SHALL mean `newest`. An empty, unsupported, or repeated `sort` parameter SHALL
be rejected with HTTP 400 and a structured validation error identifying the
`sort` field. The user interface SHALL offer only supported values and SHALL
start with `newest`; it SHALL NOT disguise API validation errors as successful
fallback responses. If the UI receives a sort validation error for a
non-default mode, it SHALL announce the error and retry once using `newest`.
It SHALL NOT retry again if that fallback request also fails validation.

#### Scenario: API defaults an omitted sort query

- **WHEN** a client requests the feedback list without a `sort` query
- **THEN** the API returns a successful response ordered as `newest`

#### Scenario: API rejects an unsupported sort query

- **WHEN** a client requests the feedback list with an empty or unsupported
  `sort` value
- **THEN** the API returns HTTP 400 with error code `VALIDATION_ERROR` and a
  `fieldErrors.sort` message

#### Scenario: API rejects repeated sort query parameters

- **WHEN** a client requests the feedback list with more than one `sort`
  parameter
- **THEN** the API returns HTTP 400 with error code `VALIDATION_ERROR` and a
  `fieldErrors.sort` message

#### Scenario: UI recovers from an invalid non-default sort

- **WHEN** a request for `most-votes` receives a `VALIDATION_ERROR` for the
  sort field
- **THEN** the UI announces the issue, requests `newest` at most once, and
  selects `newest` only after that fallback request succeeds

#### Scenario: UI does not loop when the default sort is rejected

- **WHEN** a request for `newest`, including a fallback request, receives a
  sort `VALIDATION_ERROR`
- **THEN** the UI reports the error and does not issue another fallback
  request

### Requirement: Sorting remains correct after board changes

The board SHALL preserve its active sort mode while the page remains open.
After a successful feedback submission or vote, the board SHALL refresh and
display the current items in the active mode's order. A full page reload SHALL
start in `newest` mode. If loading a newly selected mode fails for a reason
other than sort validation, the board SHALL retain the last successfully
displayed list and active selection, announce an actionable error, and allow
the user to retry the failed mode without treating the failed request as a
successful sort. When requests overlap, only the response for the latest
selection SHALL be allowed to change the displayed list or active mode.

#### Scenario: New feedback is inserted according to the selected mode

- **WHEN** a user submits valid feedback while either sort mode is selected
- **THEN** the new item appears in the position required by the selected
  ordering

#### Scenario: A successful vote immediately updates most-voted order

- **WHEN** a vote succeeds while `most-votes` is selected
- **THEN** the updated vote count is displayed and the list is reordered to
  match the selected mode

#### Scenario: A successful vote preserves newest order

- **WHEN** a vote succeeds while `newest` is selected
- **THEN** the updated vote count is displayed and the list remains ordered by
  newest creation instant, then ascending ID

#### Scenario: A successful submission refreshes the active ordering

- **WHEN** a user submits valid feedback while a sort mode is active
- **THEN** the board refreshes that mode and displays the new item in the
  position required by the active ordering

#### Scenario: Refresh restores the default mode

- **WHEN** a user reloads the page after selecting `most-votes`
- **THEN** the board starts in `newest` mode and requests the default ordering

#### Scenario: Sort request failure preserves usable board state

- **WHEN** loading feedback for a newly selected mode fails
- **THEN** the board keeps the last successfully displayed list and active
  mode, announces an actionable error to assistive technology, restores the
  control to the active mode, and provides a way to retry the failed mode

#### Scenario: Latest sort selection wins

- **WHEN** a user selects another mode before the previous sort request
  completes
- **THEN** only the response for the latest selection changes the displayed
  list or active mode

#### Scenario: Mutation refresh failure is reported honestly

- **WHEN** feedback creation or voting succeeds but refreshing the active sort
  fails
- **THEN** the board does not claim the refreshed order is current, keeps the
  last successfully displayed list, announces that the change succeeded but
  the board could not refresh, and offers a retry
