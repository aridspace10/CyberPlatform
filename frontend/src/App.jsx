import Terminal from "./game/Terminal";
import Homepage from "./Homepage";
import Game from "./game/Game";
import "./app.css"
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import UserManager from "./components/UserManager";

export default function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<Homepage />} />
                <Route path="/terminal" element={<Terminal />} />
                <Route path="/game" element={<Game />} />
                <Route path="/users" element={<UserManager />} />
            </Routes>
        </Router>
    )
}