# Controller Pattern

HTTP request handlers — thin layer, delegate to service.

## Responsibilities
- Parse request params/body
- Call service methods
- Map results to HTTP status codes
- Never contain SQL or business rules

## Express example
```js
router.get('/items', async (req, res, next) => {
  try {
    const items = await itemService.listItems()
    res.json(items)
  } catch (err) { next(err) }
})

router.post('/items', async (req, res, next) => {
  try {
    const item = await itemService.createItem(req.body)
    res.status(201).json(item)
  } catch (err) { next(err) }
})
```

## Error mapping
- Validation error → 400
- Not found → 404
- Unexpected → 500 via error_handler middleware
