import { Link } from "react-router-dom";
import "./ResultsScreen.css";

function scoreOf(entry) {
    const score = Number(entry.completed);
    return Number.isFinite(score) && score >= 0 ? score : 0;
}

export default function ResultsScreen({ gameData, userId }) {
    const data = gameData || {};
    const standings = (Array.isArray(data.leaderboard) ? data.leaderboard : [])
        .map((entry) => ({ ...entry, score: scoreOf(entry) }))
        .sort((left, right) => right.score - left.score);
    const roundsPlayed = Math.max(0, Number(data.round) || 0);
    const roundsTotal = Math.max(roundsPlayed, Number(data.rounds) || 0);
    const questionsPerRound = Math.max(0, Number(data.progress?.total) || 0);
    const possibleQuestions = roundsTotal && questionsPerRound
        ? roundsTotal * questionsPerRound : null;
    const soloScore = standings.find((entry) => String(entry.playerID) === String(userId))?.score
        ?? Math.max(0, Number(data.progress?.completed) || 0);
    const leaders = standings.filter((entry) => entry.score === standings[0]?.score);

    return (
        <section className="game-results" aria-labelledby="results-title">
            <div className="results-card">
                <p className="results-eyebrow">SESSION COMPLETE</p>
                <h1 id="results-title">Game complete</h1>
                {data.sessionName && <p className="results-session-name">{data.sessionName}</p>}

                {data.playType === "Versus" ? <>
                    <h2>Final standings</h2>
                    {standings.length >= 2 ? (
                        <p className="results-outcome">
                            {leaders.length > 1
                                ? `Tie for first: ${leaders.map((entry) => entry.name || `Player ${entry.playerID}`).join(" and ")}`
                                : `Winner: ${leaders[0].name || `Player ${leaders[0].playerID}`}`}
                        </p>
                    ) : <p className="results-outcome">Final standings are incomplete.</p>}
                    {standings.length ? <ol className="results-standings">
                        {standings.map((entry, index) => (
                            <li key={entry.playerID ?? index}>
                                <span className="results-rank">#{standings.findIndex((other) => other.score === entry.score) + 1}</span>
                                <span className="results-player">{entry.name || `Player ${entry.playerID ?? index + 1}`}</span>
                                <strong>{entry.score} completed</strong>
                            </li>
                        ))}
                    </ol> : <p>No scores are available for this session.</p>}
                    <p className="results-note">Standings count completed questions, including for players who did not finish every round.</p>
                </> : <>
                    <h2>Your results</h2>
                    <div className="results-stats">
                        <div><strong>{soloScore}</strong><span>questions completed{possibleQuestions ? ` of ${possibleQuestions}` : ""}</span></div>
                        <div><strong>{roundsPlayed}{roundsTotal ? ` / ${roundsTotal}` : ""}</strong><span>rounds played</span></div>
                    </div>
                </>}

                <div className="results-actions">
                    <Link to="/sessions">Back to sessions</Link>
                    <Link to="/session-create">Start a new session</Link>
                </div>
            </div>
        </section>
    );
}
