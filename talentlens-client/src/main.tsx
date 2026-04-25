import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const rootEl = document.getElementById('root')!

try {
  createRoot(rootEl).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
} catch (e) {
  rootEl.innerHTML = `<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;font-family:sans-serif;padding:2rem;text-align:center"><h2 style="font-size:1.25rem;font-weight:600;margin-bottom:0.5rem">Failed to load application</h2><p style="color:#666;font-size:0.875rem;max-width:400px">${(e as Error)?.message ?? 'Unknown error'}</p><button onclick="location.reload()" style="margin-top:1rem;padding:0.5rem 1.5rem;border-radius:6px;border:1px solid #ccc;cursor:pointer">Reload</button></div>`
}
