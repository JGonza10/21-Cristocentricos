import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import { aplicarTema, temaGuardado } from './tema.js'
import './styles/tokens.css'
import './styles/app.css'

aplicarTema(temaGuardado())
createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)
