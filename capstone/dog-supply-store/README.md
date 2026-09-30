# Bark & Buy: a dog-run dog-supply shop

Welcome to a store for dogs with human-level intelligence, excellent noses,
and absolutely no interest in your boring human checkout. Browse the shelves,
pack your cart, and place a **pretend** order using imaginary treat tokens.
No real payment is collected and the app never asks for card details.

## Run it locally

Requires Python 3.10 or newer. No administrator rights, Node.js, package
manager, network access, or third-party Python packages are needed.

From this directory in PowerShell:

```powershell
py --version
py -m dog_supply_store
```

Open <http://127.0.0.1:8000>. Stop the server with `Ctrl+C`. The server binds
to the local computer only by default. SQLite data is saved under `data/` and
is ignored by Git. To use a fresh temporary database or a different port:

```powershell
py -m dog_supply_store --port 8001 --database "$env:TEMP\dog-store-demo.sqlite3"
```

Do not change the bind address to expose this demo to the internet. It is a
local capstone, not a production commerce service.

## Try the dog workflow

1. Add a squeaky duck or sniffari kit to your pack.
2. Check the treat-token total and remove anything that fails the sniff test.
3. Enter a delivery-tag name and choose **Pay with pretend treat tokens**.
4. See the simulated order confirmation. No account, shipping address, or
   payment credential is requested.

## Validate without installing anything

Run from this directory:

```powershell
py -m unittest discover -s tests -v
py -m compileall -q dog_supply_store tests
```

The unit tests cover the SQLite storage boundary, product catalog, cart
isolation, quantity validation, and simulated order persistence. The HTTP tests
start a real local server on a temporary database and exercise the product API,
liveness/readiness endpoints, browser forms, CSRF rejection, validation errors,
and output escaping.

GitHub Actions runs these same checks when this capstone changes. It uses
GitHub's hosted runner; it does not install anything on your computer.

## Design and guardrails

- **One primary workflow:** browse supplies, manage one shopping cart, and
  submit a pretend order.
- **Dog-first voice:** sniffaris, squeaks, zoomies, puddle negotiations, and
  strong opinions about tennis balls.
- **Accessible UI:** semantic headings, labeled controls, keyboard-visible
  focus, and announced success and error messages.
- **Explicit storage boundary:** `DogStore` owns parameterized SQLite access;
  each test uses a disposable local database.
- **Local safety:** loopback binding by default, opaque `HttpOnly` session
  cookie, per-session CSRF token, bounded form sizes and quantities, escaped
  customer-controlled text, and no payment data.
- **Operations:** `/health/live` reports that the process responds;
  `/health/ready` checks SQLite; `/api/products` exposes the catalog.
- **No cloud or paid services:** Azure and real payment processing are
  intentionally out of scope.

## Capstone evidence and limitations

The checked-in tests and capstone-specific CI workflow are reproducible
evidence. The CI job has read-only repository permission and runs only when
this capstone or its workflow changes.

This implementation intentionally proceeds without OpenSpec, at the user's
request. It also omits Azure deployment because the app must run locally.
The workshop's licensed/tool-dependent GitHub Agentic Workflow, protected
deployment, and real GitHub issue/PR review loop are not represented as
completed: they require repository and platform setup beyond a local Python
app. The repository's existing PR policy also requires an approved OpenSpec
change for workflow-file changes, so a PR containing this CI workflow will not
pass that policy without the required specification evidence. Do not bypass
or weaken the policy. Before presenting the full workshop evidence chain,
open a parent capstone issue, resolve the specification gate through the
repository owners' chosen process, review this change through a PR and its CI
run, file a real reproducible bug issue if testing or use discovers a defect,
and record which optional platform controls are unavailable. Do not invent a
bug or claim a deployment that did not happen.
