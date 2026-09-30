"""SQLite storage for the dog shop's catalog, carts, sessions, and orders."""

from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    description: str
    price_tokens: int
    emoji: str


PRODUCTS = (
    Product(
        "sniffari-kit",
        "The Sniffari Starter Kit",
        "A field guide, three suspiciously interesting scents, and permission "
        "to inspect every shrub.",
        12,
        "🌿",
    ),
    Product(
        "squeaky-duck",
        "The Extremely Squeaky Duck",
        "Squeaks at a volume legally classified as 'delighted.' The duck has "
        "accepted its fate.",
        8,
        "🦆",
    ),
    Product(
        "zoomie-blanket",
        "Post-Zoomie Recovery Blanket",
        "For collapsing dramatically after a sprint around the living room.",
        15,
        "🛋️",
    ),
    Product(
        "treat-puzzle",
        "Treat Puzzle of Mild Genius",
        "A brain game for scholars who also eat the homework.",
        10,
        "🧩",
    ),
    Product(
        "raincoat",
        "Raincoat for Brave Little Cloud Encounters",
        "Keeps the drizzle off. Does not prevent theatrical puddle negotiations.",
        18,
        "🌧️",
    ),
    Product(
        "tennis-ball",
        "The Ball You Definitely Won't Lose",
        "High bounce, classic fuzz, absolutely not going under the sofa.",
        6,
        "🎾",
    ),
)


class DogStore:
    """Persistence boundary backed by a local SQLite database."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        if str(self.database_path) != ":memory:":
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    price_tokens INTEGER NOT NULL CHECK (price_tokens > 0),
                    emoji TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    csrf_token TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cart_items (
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    product_id TEXT NOT NULL REFERENCES products(id),
                    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 20),
                    PRIMARY KEY (session_id, product_id)
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    dog_name TEXT NOT NULL,
                    items_json TEXT NOT NULL,
                    total_tokens INTEGER NOT NULL CHECK (total_tokens > 0),
                    payment_status TEXT NOT NULL CHECK (payment_status = 'SIMULATED'),
                    created_at TEXT NOT NULL
                );
                """
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO products (id, name, description, price_tokens, emoji)
                VALUES (:id, :name, :description, :price_tokens, :emoji)
                """,
                [asdict(product) for product in PRODUCTS],
            )

    def check_ready(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    def list_products(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, name, description, price_tokens, emoji "
                "FROM products ORDER BY id"
            ).fetchall()
            return [dict(row) for row in rows]

    def create_session(self, session_id: str, csrf_token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions (id, csrf_token) VALUES (?, ?)",
                (session_id, csrf_token),
            )

    def get_session(self, session_id: str) -> dict[str, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, csrf_token FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_cart(self, session_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT products.id, products.name, products.emoji,
                       products.price_tokens, cart_items.quantity,
                       products.price_tokens * cart_items.quantity AS subtotal
                FROM cart_items
                JOIN products ON products.id = cart_items.product_id
                WHERE cart_items.session_id = ?
                ORDER BY products.name
                """,
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def add_to_cart(self, session_id: str, product_id: str, quantity: int) -> None:
        if not 1 <= quantity <= 20:
            raise ValueError("Pick between 1 and 20 of an item.")
        with self._connect() as connection:
            product = connection.execute(
                "SELECT id FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if product is None:
                raise ValueError("That item vanished behind the sofa. Try another?")
            existing = connection.execute(
                "SELECT quantity FROM cart_items WHERE session_id = ? AND product_id = ?",
                (session_id, product_id),
            ).fetchone()
            new_quantity = quantity + (existing["quantity"] if existing else 0)
            if new_quantity > 20:
                raise ValueError("Twenty is the cart limit. Even for tennis balls.")
            connection.execute(
                """
                INSERT INTO cart_items (session_id, product_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id, product_id)
                DO UPDATE SET quantity = excluded.quantity
                """,
                (session_id, product_id, new_quantity),
            )

    def remove_from_cart(self, session_id: str, product_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM cart_items WHERE session_id = ? AND product_id = ?",
                (session_id, product_id),
            )

    def create_order(self, session_id: str, dog_name: str) -> dict[str, object]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT products.id, products.name, products.price_tokens,
                       cart_items.quantity,
                       products.price_tokens * cart_items.quantity AS subtotal
                FROM cart_items
                JOIN products ON products.id = cart_items.product_id
                WHERE cart_items.session_id = ?
                ORDER BY products.name
                """,
                (session_id,),
            ).fetchall()
            if not rows:
                raise ValueError("Your pack is empty. Add a treasure before checkout.")

            items = [dict(row) for row in rows]
            order = {
                "id": secrets.token_hex(6).upper(),
                "dog_name": dog_name,
                "items": items,
                "total_tokens": sum(int(item["subtotal"]) for item in items),
                "payment_status": "SIMULATED",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            connection.execute(
                """
                INSERT INTO orders
                    (id, dog_name, items_json, total_tokens, payment_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    order["id"],
                    dog_name,
                    json.dumps(items),
                    order["total_tokens"],
                    order["payment_status"],
                    order["created_at"],
                ),
            )
            connection.execute(
                "DELETE FROM cart_items WHERE session_id = ?", (session_id,)
            )
            return order

    def get_order(self, order_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, dog_name, items_json, total_tokens, payment_status, created_at
                FROM orders WHERE id = ?
                """,
                (order_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "id": row["id"],
                "dog_name": row["dog_name"],
                "items": json.loads(row["items_json"]),
                "total_tokens": row["total_tokens"],
                "payment_status": row["payment_status"],
                "created_at": row["created_at"],
            }
