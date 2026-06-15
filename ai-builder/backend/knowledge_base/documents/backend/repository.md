# Repository Pattern

Database access layer — only SQL/queries, no business logic.

## Responsibilities
- CRUD operations for one entity
- Parameterized queries (prevent SQL injection)
- Return plain objects or DTOs

## Node.js + SQLite example
```js
class ItemRepository {
  constructor(db) { this.db = db }

  findAll() {
    return this.db.prepare('SELECT * FROM items ORDER BY created_at DESC').all()
  }

  findById(id) {
    return this.db.prepare('SELECT * FROM items WHERE id = ?').get(id)
  }

  create(data) {
    const stmt = this.db.prepare(
      'INSERT INTO items (name, status) VALUES (?, ?) RETURNING *'
    )
    return stmt.get(data.name, data.status)
  }
}
```

## Rules
- No HTTP logic here
- Called only by Service layer
