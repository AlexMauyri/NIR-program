import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import MetricsPage from "./pages/MetricsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="metrics" element={<MetricsPage />} />
      </Route>
    </Routes>
  );
}
