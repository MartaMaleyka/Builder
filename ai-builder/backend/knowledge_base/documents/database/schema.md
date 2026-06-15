# Database Schema Design

Define tables, relationships, and indexes.

## Conventions
- Primary key: `id` (INTEGER AUTOINCREMENT or UUID)
- Timestamps: `created_at`, `updated_at` with DEFAULT CURRENT_TIMESTAMP
- Foreign keys with ON DELETE CASCADE where appropriate
- Index columns used in WHERE/JOIN

## Example SQLite schema
```sql
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  status TEXT DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_items_status ON items(status);
```

## Related
schema versioned_by migration, schema populated_by seed
