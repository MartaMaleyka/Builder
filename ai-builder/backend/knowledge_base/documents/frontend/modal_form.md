# Modal Form Pattern

Create/edit modal with form validation.

## Structure
- Overlay: `fixed inset-0 bg-black/50 z-50`
- Panel: centered card with title, form fields, Cancel + Save buttons
- Close on ESC and overlay click

## Form fields
- Use controlled inputs with `useState`
- Show inline validation errors below each field
- Disable Save while submitting

## Example trigger
```jsx
<button onClick={() => setShowModal(true)} className="bg-accent text-white px-4 py-2 rounded-lg">
  Nuevo Item
</button>
```
