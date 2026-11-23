import Terminal from "./game/Terminal";
import Homepage from "./Homepage";
import Game from "./game/Game";
import "./app.css"
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from "./auth/ProtectedRoute";
import { AuthProvider } from "./auth/AuthContext";
import Login from "./pages/Login/LoginPage";
import Signup from "./pages/Login/SignupPage";
import SessionCreation from "./pages/Session/SessionCreation";
import SessionsPage from "./pages/Session/SessionsPage";
import Profile from "./pages/Profile/Profile";
import ContactPage from "./pages/Contact/ContactPage";

export default function App() {
    return (
        <AuthProvider>
            <Router>
                <Routes>
                    {/* User pathways */}
                    <Route path="/" element={<Homepage />} />
                    <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
                    <Route path="/sessions" element={<SessionsPage />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/signup" element={<Signup />} />
                    <Route path="/contact" element={<ContactPage />} />
                    <Route path="/game/:sessionId" element={
                        <ProtectedRoute>
                            <Game />
                        </ProtectedRoute>
                    } />
                    <Route path="/session-create" element={
                        <ProtectedRoute>
                            <SessionCreation />
                        </ProtectedRoute>
                    } />
                    {/* Dev pathways */}
                    <Route path="/terminal" element={<Terminal />} />
                    <Route path="/users" element={<Navigate to="/profile" replace />} />
                </Routes>
            </Router>
        </AuthProvider>
    )
}
