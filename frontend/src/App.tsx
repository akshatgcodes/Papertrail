import { Route, Routes } from "react-router-dom";
import RequireOwner from "./components/RequireOwner";
import Ask from "./pages/Ask";
import DocumentPage from "./pages/DocumentPage";
import History from "./pages/History";
import Library from "./pages/Library";
import QueryPage from "./pages/QueryPage";

export default function App() {
  return (
    <Routes>
      <Route element={<RequireOwner />}>
        <Route path="/" element={<Ask />} />
        <Route path="/library" element={<Library />} />
        <Route path="/d/:id" element={<DocumentPage />} />
        <Route path="/history" element={<History />} />
        <Route path="/q/:id" element={<QueryPage />} />
      </Route>
    </Routes>
  );
}
