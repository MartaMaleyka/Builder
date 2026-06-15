# Sidebar Navigation Pattern

React sidebar with React Router integration.

## Structure
- Fixed left sidebar (`w-64`) with app title and nav links
- One `NavLink` per entity with emoji icon
- Active state: left border accent + background tint
- Main content area: `flex-1` with padding

## Example
```jsx
<aside className="w-64 border-r border-border bg-surface">
  <nav className="p-4 space-y-1">
    {entities.map(e => (
      <NavLink key={e.slug} to={`/${e.slug}`}
        className={({isActive}) =>
          `flex items-center gap-2 px-3 py-2 rounded-lg transition-colors
           ${isActive ? 'bg-accent/10 border-l-2 border-accent' : 'hover:bg-bg'}`
        }>
        <span>{e.icon}</span> {e.name}
      </NavLink>
    ))}
  </nav>
</aside>
```

## Related concepts
sidebar requires routing, layout contains sidebar
