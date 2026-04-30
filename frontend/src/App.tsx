import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/ui/Layout";
import BuilderPage from "./pages/BuilderPage";
import SavedBuildsPage from "./pages/SavedBuildsPage";
import RosterPage from "./pages/RosterPage";
import ShrinePage from "./pages/ShrinePage";
import EvaluationPage from "./pages/EvaluationPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/builder" replace />} />
          <Route path="/builder" element={<BuilderPage />} />
          <Route path="/saved" element={<SavedBuildsPage />} />
          <Route path="/roster" element={<RosterPage />} />
          <Route path="/shrine" element={<ShrinePage />} />
          <Route path="/evaluation" element={<EvaluationPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
