# Authentication with JWT Middleware

Protect routes with JWT verification middleware.

## Auth flow
1. POST /auth/login → validate credentials → return JWT
2. Client sends `Authorization: Bearer <token>` on protected routes
3. Middleware verifies token → attaches user to req → next()

## Middleware example
```js
function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1]
  if (!token) return res.status(401).json({ error: 'Unauthorized' })
  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET)
    next()
  } catch {
    res.status(401).json({ error: 'Invalid token' })
  }
}
```

## Dependency chain
auth uses jwt, auth implements middleware, routes protected_by auth
