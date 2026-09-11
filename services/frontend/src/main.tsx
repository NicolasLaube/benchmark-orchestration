import { StrictMode } from 'react'
import ReactDOM from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import './index.css'
import App from './App.tsx'
import keycloak from "./auth/keycloak"


keycloak.init({
  onLoad: "login-required",
  pkceMethod: "S256",
  checkLoginIframe: false,

}).then((authenticated) => {

  if (!authenticated) {
    return;
  }


  ReactDOM.createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </StrictMode>,
  )
}).catch((error) => {
  console.error("Keycloak init error:", error);

});


