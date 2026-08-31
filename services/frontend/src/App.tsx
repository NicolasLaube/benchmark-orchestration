import './App.css'
import { Routes, Route } from "react-router-dom"
import { UploadPage } from "../src/pages/UploadPage"
import { RunPage } from "../src/pages/RunPage"
import { ReportPage } from './pages/ReportPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<UploadPage />} />
      <Route path="/runs/:runId" element={<RunPage />} />
      <Route
        path="/runs/:runId/report"
        element={<ReportPage />}
      />
    </Routes>
  )
}

export default App
