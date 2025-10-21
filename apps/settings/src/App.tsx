import { BrowserRouter } from 'react-router-dom'
import { AppRoutes } from './router'


function App() {
  return (
    <BrowserRouter basename={__BASE_PATH__}>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App