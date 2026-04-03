import Terminal from "./game/Terminal";
import Homepage from "./Homepage";
import Game from "./game/Game";
import "./app.css"
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import UserManager from "./components/UserManager";
import ProtectedRoute from "./auth/ProtectedRoute";
import { AuthProvider } from "./auth/AuthContext";
import Login from "./pages/Login/LoginPage";
import Signup from "./pages/Login/SignupPage";
import Sandbox from "./pages/Sandbox/Sandbox"

export default function App() {
    return (
        <AuthProvider>
            <Router>
                <Routes>
                    {/* User pathways */}
                    <Route path="/" element={<Homepage />} />
                    <Route path="/profile" element={<ProtectedRoute></ProtectedRoute>} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/signup" element={<Signup />} />
                    <Route path="/game/:sessionId" element={
                        <ProtectedRoute>
                            <Game />
                        </ProtectedRoute>
                    } />
                    {/* Dev pathways */}
                    <Route path="/terminal" element={<Terminal />} />
                    <Route path="/users" element={<UserManager />} />
                </Routes>
            </Router>
        </AuthProvider>
    )
}