import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import "./ResultsScreen.css";

const FINISH_REASONS = {
    all_questions_completed: "All questions in the final round were completed.",
    time_expired: "The round timer expired.",
    rounds_exhausted: "The final round ended with some questions incomplete.",
};

function scoreOf(entry) {
    const score = Number(entry.completed);
    return Number.isFinite(score) && score >= 0 ? score : 0;
}

export default function ResultsScreen({ gameData, userId }) {
    const data = gameData || {};
    const headingRef = useRef(null);
    useEffect(() => { headingRef.current?.focus(); }, []);
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
    const finalQuestions = Array.isArray(data.questions) ? data.questions : [];
    const remainingQuestions = finalQuestions.filter((question) => question.status !== "completed");
    const completedQuestions = finalQuestions.length - remainingQuestions.length;
    const finishExplanation = FINISH_REASONS[data.finishReason]
        || "The session ended. Its exact finish reason is unavailable after reconnecting.";

    return (
        <section className="game-results" aria-labelledby="results-title">
            <div className="results-card">
                <p className="results-eyebrow">SESSION COMPLETE</p>
                <h1 id="results-title" ref={headingRef} tabIndex={-1}>Game complete</h1>
                {data.sessionName && <p className="results-session-name">{data.sessionName}</p>}
                <p className="results-reason">{finishExplanation}</p>

                {data.playType === "Versus" ? <>
                    <h2>Final standings</h2>
                    {standings.length >= 2 && standings[0].score === 0 ? (
                        <p className="results-outcome">No winner: no questions were completed.</p>
                    ) : standings.length >= 2 ? (
                        <p className="results-outcome">
                            {leaders.length > 1
                                ? `Tie for first: ${leaders.map((entry) => entry.name || `Player ${entry.playerID}`).join(" and ")}`
                                : `${data.finishReason === "rounds_exhausted" ? "Top score" : "Winner"}: ${leaders[0].name || `Player ${leaders[0].playerID}`}`}
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

                <section className="results-review" aria-labelledby="results-review-title">
                    <h2 id="results-review-title">Final-round questions</h2>
                    {finalQuestions.length ? <>
                        <p>{completedQuestions} completed · {remainingQuestions.length} to practice</p>
                        <ol className="results-question-list">
                            {finalQuestions.map((question, index) => (
                                <li key={question.id ?? index}>
                                    <span>Question {index + 1}</span>
                                    <strong>{question.status === "completed" ? "Completed" : "To practice"}</strong>
                                </li>
                            ))}
                        </ol>
                        <p className="results-note">
                            {remainingQuestions.length
                                ? "In your next session, revisit the numbered questions marked To practice. Try one command at a time and check its output."
                                : "You completed every question in the final round. Try another session with a different command selection."}
                        </p>
                    </> : <p className="results-note">Question details are unavailable for this saved session. Start another session to practice again.</p>}
                </section>

                <div className="results-actions">
                    <Link to="/sessions">Back to sessions</Link>
                    <Link to="/session-create">Start a new session</Link>
                </div>
            </div>
        </section>
    );
}
