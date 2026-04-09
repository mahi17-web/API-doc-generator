"""
Sample FastAPI backend used as input for the documentation generator.
Run standalone: uvicorn sample_backend.app:app --port 8001 --reload
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


_db: List[Book] = [
    Book(id=1, title="The Pragmatic Programmer", author="David Thomas", price=42.99),
    Book(id=2, title="Clean Code", author="Robert C. Martin", price=37.50),
]
_next_id = 3


@app.get("/books", response_model=List[Book], summary="List all books")
def list_books(in_stock: Optional[bool] = Query(None, description="Filter by stock status")):
    """Return all books, optionally filtered by availability."""
    if in_stock is not None:
        return [b for b in _db if b.in_stock == in_stock]
    return _db


@app.get("/books/{book_id}", response_model=Book, summary="Get a book by ID")
def get_book(book_id: int):
    """Fetch a single book by its numeric ID."""
    for b in _db:
        if b.id == book_id:
            return b
    raise HTTPException(status_code=404, detail="Book not found")


@app.post("/books", response_model=Book, status_code=201, summary="Create a book")
def create_book(payload: BookCreate):
    """Add a new book to the catalog."""
    global _next_id
    book = Book(id=_next_id, **payload.model_dump())
    _next_id += 1
    _db.append(book)
    return book


@app.delete("/books/{book_id}", status_code=204, summary="Delete a book")
def delete_book(book_id: int):
    """Remove a book from the catalog by its ID."""
    global _db
    before = len(_db)
    _db = [b for b in _db if b.id != book_id]
    if len(_db) == before:
        raise HTTPException(status_code=404, detail="Book not found")


@app.get("/health", summary="Health check")
def health():
    """Service health endpoint."""
    return {"status": "ok"}

