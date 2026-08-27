import './App.css'
import { Routes, Route } from "react-router-dom"
import { UploadPage } from "../src/pages/UploadPage"
import { RunPage } from "../src/pages/RunPage"

function App() {
  return (
    <Routes>
      <Route path="/" element={<UploadPage />} />
      <Route path="/runs/:runId" element={<RunPage />} />
    </Routes>
  )
}

export default App
