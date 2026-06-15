# Service Layer Pattern

Business logic between controller and repository.

## Responsibilities
- Validate business rules
- Orchestrate multiple repositories
- Throw domain errors (not HTTP errors)

## Example
```js
class ItemService {
  constructor(itemRepo) { this.repo = itemRepo }

  async listItems() {
    return this.repo.findAll()
  }

  async createItem(data) {
    if (!data.name?.trim()) throw new Error('Name is required')
    return this.repo.create({ name: data.name.trim(), status: 'active' })
  }
}
```

## Flow
controller → service → repository → database
