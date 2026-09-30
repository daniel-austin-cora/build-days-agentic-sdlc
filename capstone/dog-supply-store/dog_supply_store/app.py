"""A dependency-free HTTP storefront for dogs with excellent taste."""

from __future__ import annotations

import argparse
import hmac
import json
import secrets
import sqlite3
from html import escape
from http import HTTPStatus
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from dog_supply_store.storage import DogStore

MAX_FORM_BYTES = 8_192


def _layout(title: str, content: str) -> str:
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} | Bark &amp; Buy</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; color: #29251f;
      background: #fff9ed; }}
    body {{ max-width: 58rem; margin: 0 auto; padding: 1rem; line-height: 1.55; }}
    header, .card, .notice {{ background: white; border: 2px solid #e7d8b9;
      border-radius: 1rem; padding: 1rem; margin: 1rem 0; }}
    header {{ background: #f3c96b; }}
    nav a {{ margin-right: 1rem; }}
    .products {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
      gap: 0.75rem; }}
    .product {{ border: 1px solid #e7d8b9; border-radius: 0.75rem; padding: 1rem; }}
    button {{ background: #315b3b; color: white; border: 0; border-radius: 0.5rem;
      padding: 0.65rem 0.9rem; font: inherit; cursor: pointer; }}
    button:focus-visible, a:focus-visible, input:focus-visible {{ outline: 3px solid #934d19;
      outline-offset: 3px; }}
    input {{ font: inherit; padding: 0.45rem; }}
    .price {{ font-weight: 700; }}
    .notice {{ border-color: #315b3b; }}
    .error {{ border-color: #a52828; }}
    footer {{ margin: 2rem 0; font-size: 0.92rem; }}
  </style>
</head>
<body>
  <header>
    <p><strong>BARK &amp; BUY</strong> — independent shopping for independent sniffers</p>
    <nav aria-label="Main navigation"><a href="/">Sniff the shelves</a>
      <a href="/#pack">Your pack</a></nav>
  </header>
  <main>{content}</main>
  <footer><p>All prices are imaginary treat tokens. Payment is pretend.
    No card details, real money, or squirrels are collected.</p></footer>
</body>
</html>"""


def _hidden_csrf(token: str) -> str:
    return f'<input type="hidden" name="csrf_token" value="{escape(token, quote=True)}">'


def _render_store(
    store: DogStore, session_id: str, csrf_token: str, message: str = "", error: bool = False
) -> str:
    products = store.list_products()
    cart = store.get_cart(session_id)
    total = sum(int(item["subtotal"]) for item in cart)
    notice = ""
    if message:
        role = "alert" if error else "status"
        class_name = "notice error" if error else "notice"
        notice = f'<p class="{class_name}" role="{role}">{escape(message)}</p>'

    product_cards = []
    for product in products:
        product_cards.append(
            f"""<article class="product">
  <h3>{escape(str(product["emoji"]))} {escape(str(product["name"]))}</h3>
  <p>{escape(str(product["description"]))}</p>
  <p class="price">{int(product["price_tokens"])} imaginary treat tokens</p>
  <form method="post" action="/cart/add">
    {_hidden_csrf(csrf_token)}
    <input type="hidden" name="product_id" value="{escape(str(product["id"]), quote=True)}">
    <label>Quantity <input type="number" name="quantity" value="1" min="1" max="20"></label>
    <button type="submit">Add to my pack</button>
  </form>
</article>"""
        )

    if cart:
        cart_lines = []
        for item in cart:
            cart_lines.append(
                f"""<li>{escape(str(item["emoji"]))} {escape(str(item["name"]))}
  × {int(item["quantity"])} — {int(item["subtotal"])} treat tokens
  <form method="post" action="/cart/remove">
    {_hidden_csrf(csrf_token)}
    <input type="hidden" name="product_id" value="{escape(str(item["id"]), quote=True)}">
    <button type="submit" aria-label="Remove {escape(str(item["name"]), quote=True)}">
      Remove from pack
    </button>
  </form>
</li>"""
            )
        cart_content = f"""<ul>{"".join(cart_lines)}</ul>
<p><strong>Pack total: {total} imaginary treat tokens</strong></p>
<form method="post" action="/checkout">
  {_hidden_csrf(csrf_token)}
  <label for="dog-name">Name for the delivery tag</label>
  <input id="dog-name" name="dog_name" maxlength="40" required autocomplete="off">
  <button type="submit">Pay with pretend treat tokens</button>
</form>"""
    else:
        cart_content = (
            "<p>Your pack is empty. This is a crisis best solved with treats.</p>"
        )

    content = f"""<h1>Excellent taste. Questionable impulse control.</h1>
<p>Welcome, discerning dog. Shop for sniffing, squeaking, zooming, and
  looking mysteriously busy.</p>
{notice}
<section aria-labelledby="shelves-heading">
  <h2 id="shelves-heading">The shelves</h2>
  <div class="products">{"".join(product_cards)}</div>
</section>
<section id="pack" class="card" aria-labelledby="pack-heading">
  <h2 id="pack-heading">Your pack ({len(cart)} item types)</h2>
  {cart_content}
</section>"""
    return _layout("The shelves", content)


def _render_order(order: dict[str, object]) -> str:
    items = order["items"]
    assert isinstance(items, list)
    item_lines = "".join(
        f"<li>{escape(str(item['name']))} × {int(item['quantity'])}</li>"
        for item in items
    )
    content = f"""<h1>Checkout complete (in our imaginations)</h1>
<p class="notice" role="status">Order {escape(str(order["id"]))} is confirmed for
  {escape(str(order["dog_name"]))}. The treat-token transaction was simulated;
  no money or payment details were involved.</p>
<h2>Delivery sniff-list</h2><ul>{item_lines}</ul>
<p>Total: {int(order["total_tokens"])} imaginary treat tokens</p>
<p><a href="/">Back to the shelves</a></p>"""
    return _layout("Order confirmed", content)


class DogStoreHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], database_path: str | Path):
        self.store = DogStore(database_path)
        super().__init__(address, DogStoreRequestHandler)


class DogStoreRequestHandler(BaseHTTPRequestHandler):
    server: DogStoreHTTPServer

    def _respond(
        self,
        body: str | bytes,
        status: HTTPStatus = HTTPStatus.OK,
        content_type: str = "text/html; charset=utf-8",
        cookie: str = "",
    ) -> None:
        encoded = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        self.send_header("Referrer-Policy", "no-referrer")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(encoded)

    def _html_error(self, status: HTTPStatus, message: str) -> None:
        body = _layout(
            "Something went sideways",
            f'<h1>Ruh-roh</h1><p class="notice error" role="alert">{escape(message)}</p>'
            '<p><a href="/">Back to the shelves</a></p>',
        )
        self._respond(body, status)

    def _session_cookie(self) -> tuple[dict[str, str] | None, str]:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except CookieError:
            return None, ""
        morsel = cookie.get("dog_store_session")
        if morsel is None:
            return None, ""
        session = self.server.store.get_session(morsel.value)
        return session, morsel.value if session else ""

    def _new_session(self) -> tuple[dict[str, str], str]:
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        self.server.store.create_session(session_id, csrf_token)
        return {"id": session_id, "csrf_token": csrf_token}, (
            f"dog_store_session={session_id}; Path=/; HttpOnly; SameSite=Lax"
        )

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health/live":
            self._respond('{"status":"alive"}', content_type="application/json")
            return
        if path == "/health/ready":
            try:
                self.server.store.check_ready()
            except sqlite3.Error:
                self._respond(
                    '{"status":"unavailable"}',
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "application/json",
                )
                return
            self._respond('{"status":"ready"}', content_type="application/json")
            return
        if path == "/api/products":
            products = self.server.store.list_products()
            self._respond(
                json.dumps(products, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
            )
            return
        if path != "/":
            self._html_error(HTTPStatus.NOT_FOUND, "That trail does not exist.")
            return

        session, _ = self._session_cookie()
        set_cookie = ""
        if session is None:
            session, set_cookie = self._new_session()
        page = _render_store(
            self.server.store, session["id"], session["csrf_token"]
        )
        self._respond(page, cookie=set_cookie)

    def _read_form(self) -> dict[str, list[str]]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("The form size was not a number.") from exc
        if length < 0 or length > MAX_FORM_BYTES:
            self._respond(
                "Form is too large.",
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "text/plain; charset=utf-8",
            )
            return {}
        data = self.rfile.read(length).decode("utf-8", errors="replace")
        return parse_qs(data, keep_blank_values=True)

    def _post_error(
        self,
        session: dict[str, str],
        status: HTTPStatus,
        message: str,
    ) -> None:
        page = _render_store(
            self.server.store,
            session["id"],
            session["csrf_token"],
            message,
            error=True,
        )
        self._respond(page, status)

    def do_POST(self) -> None:
        session, _ = self._session_cookie()
        if session is None:
            self._html_error(
                HTTPStatus.FORBIDDEN, "Your shopping session expired. Please start again."
            )
            return
        try:
            form = self._read_form()
        except ValueError as exc:
            self._post_error(session, HTTPStatus.BAD_REQUEST, str(exc))
            return
        if not form and self.headers.get("Content-Length", "0") != "0":
            return
        supplied_token = form.get("csrf_token", [""])[0]
        if not hmac.compare_digest(supplied_token, session["csrf_token"]):
            self._post_error(
                session, HTTPStatus.FORBIDDEN, "That form needs a fresh sniff of approval."
            )
            return

        path = urlsplit(self.path).path
        try:
            if path == "/cart/add":
                quantity_text = form.get("quantity", ["1"])[0]
                try:
                    quantity = int(quantity_text)
                except ValueError as exc:
                    raise ValueError("Quantity must be a whole number.") from exc
                self.server.store.add_to_cart(
                    session["id"], form.get("product_id", [""])[0], quantity
                )
            elif path == "/cart/remove":
                self.server.store.remove_from_cart(
                    session["id"], form.get("product_id", [""])[0]
                )
            elif path == "/checkout":
                dog_name = form.get("dog_name", [""])[0].strip()
                if (
                    not dog_name
                    or len(dog_name) > 40
                    or any(ord(character) < 32 for character in dog_name)
                ):
                    raise ValueError("Please enter a dog name up to 40 characters long.")
                order = self.server.store.create_order(session["id"], dog_name)
                self._respond(_render_order(order))
                return
            else:
                self._html_error(HTTPStatus.NOT_FOUND, "That trail does not exist.")
                return
        except ValueError as exc:
            self._post_error(session, HTTPStatus.BAD_REQUEST, str(exc))
            return

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/#pack")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        super().log_message(format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Bark & Buy dog shop.")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: local only)")
    parser.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "dog-store.sqlite3",
        help="SQLite database path",
    )
    args = parser.parse_args()
    server = DogStoreHTTPServer((args.host, args.port), args.database)
    print(f"Bark & Buy is sniffable at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nThe shop is closed. Good dog.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
