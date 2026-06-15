# React Router Setup

Configure client-side routing for SPA navigation.

## Setup
```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/items" element={<ItemsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
```

## Rules
- Use `NavLink` for sidebar links (active state built-in)
- Wrap layout around routes, not inside each page
- Lazy-load pages with `React.lazy` for large apps
