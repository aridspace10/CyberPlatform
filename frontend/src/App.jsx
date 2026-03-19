import Terminal from "./game/Terminal";
import Homepage from "./Homepage";
import Game from "./game/Game";
import "./app.css"
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import UserManager from "./components/UserManager";
import ProtectedRoute from "./auth/ProtectedRoute";
import { AuthProvider } from "./auth/AuthContext";
import Login from "./pages/Login/LoginPage";

export default function App() {
    return (
        <AuthProvider>
            <Router>
                <Routes>
                    {/* User pathways */}
                    <Route path="/" element={<Homepage />} />
                    <Route path="/profile" element={<ProtectedRoute></ProtectedRoute>} />
                    <Route path="/login" element={<Login />} />
                    {/* Dev pathways */}
                    <Route path="/terminal" element={<Terminal />} />
                    <Route path="/game" element={<Game />} />
                    <Route path="/users" element={<UserManager />} />
                </Routes>
            </Router>
        </AuthProvider>
    )
}