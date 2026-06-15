# Data Table with CRUD

List page pattern with loading, empty, and error states.

## Required states
1. **Loading**: `animate-pulse` skeleton rows
2. **Empty**: centered icon + message + "Create first item" CTA
3. **Error**: error message + retry button
4. **Data**: table with sticky header, row actions (edit/delete)

## Fetch pattern
```jsx
const [items, setItems] = useState([])
const [loading, setLoading] = useState(true)
const [error, setError] = useState(null)

useEffect(() => {
  fetch('/api/items')
    .then(r => r.json())
    .then(setItems)
    .catch(e => setError(e.message))
    .finally(() => setLoading(false))
}, [])
```

## Actions
- Header: title + "Nuevo" button opens create modal
- Row: edit (pencil) + delete (trash) with confirmation
