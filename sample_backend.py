"""
sample_backend.py - Working FastAPI example with GET, POST, path params, and query params.
Run with: uvicorn sample_backend:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Bookstore API", version="1.0.0")


class Book(BaseModel):
    id: int
    title: str
    author: str
    price: float
    in_stock: bool = True


class BookCreate(BaseModel):
    title: str
    author: str
    price: float
    in_stock: bool = True


# In-memory database
books_db: List[Book] = [
    Book(id=1, title="The Pragmatic Programmer", author="David Thomas", price=42.99),
    Book(id=2, title="Clean Code", author="Robert C. Martin", price=37.50),
]
_next_id = 3


@app.get("/books", response_model=List[Book], summary="List all books")
def list_books(in_stock: Optional[bool] = Query(None, description="Filter by availability")):
    """Return all books, optionally filtered by stock status."""
    if in_stock is not None:
        return [b for b in books_db if b.in_stock == in_stock]
    return books_db


@app.get("/books/{book_id}", response_model=Book, summary="Get a book by ID")
def get_book(book_id: int):
    """Fetch a single book by its ID."""
    for b in books_db:
        if b.id == book_id:
            return b
    raise HTTPException(status_code=404, detail="Book not found")


@app.post("/books", response_model=Book, status_code=201, summary="Create a new book")
def create_book(payload: BookCreate):
    """Add a new book to the catalog."""
    global _next_id
    new = Book(id=_next_id, **payload.model_dump())
    _next_id += 1
    books_db.append(new)
    return new


@app.delete("/books/{book_id}", status_code=204, summary="Delete a book")
def delete_book(book_id: int):
    """Remove a book by ID."""
    global books_db
    before = len(books_db)
    books_db = [b for b in books_db if b.id != book_id]
    if len(books_db) == before:
        raise HTTPException(status_code=404, detail="Book not found")


@app.get("/health", summary="Health check")
def health():
    """Returns service health."""
    return {"status": "ok"}
