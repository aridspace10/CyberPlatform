import "./GameDataPanel.css";

const EMPTY_GAME_DATA = {
    sessionName: "Session",
    gameType: "",
    questions: [],
    progress: { completed: 0, total: 0 },
};

export default function GameDataPanel({ gameData = EMPTY_GAME_DATA }) {
    const data = gameData || EMPTY_GAME_DATA;
    const questions = data.questions || [];
    const completed = data.progress?.completed || 0;
    const total = data.progress?.total || 0;
    const percentage = total > 0 ? Math.min(100, (completed / total) * 100) : 0;

    return (
        <aside className="game-data-panel" aria-label="Game data">
            <header className="game-data-header">
                <span className="game-data-eyebrow">Session</span>
                <h1>{data.sessionName || "Session"}</h1>
                {data.gameType && <span className="game-type">{data.gameType}</span>}
            </header>

            <section className="game-data-section">
                <div className="game-data-section-heading">
                    <h2>Progress</h2>
                    <span>{completed} / {total}</span>
                </div>
                <div
                    className="progress-track"
                    role="progressbar"
                    aria-label="Question progress"
                    aria-valuemin="0"
                    aria-valuemax={total}
                    aria-valuenow={completed}
                >
                    <div className="progress-value" style={{ width: `${percentage}%` }} />
                </div>
            </section>

            <section className="game-data-section questions-section">
                <div className="game-data-section-heading">
                    <h2>Questions</h2>
                    <span>{questions.length}</span>
                </div>
                {questions.length > 0 ? (
                    <ol className="question-list">
                        {questions.map((question, index) => (
                            <li
                                key={question.id ?? index}
                                className={`question-item ${question.status || "pending"}`}
                            >
                                <span className="question-number">
                                    {String(index + 1).padStart(2, "0")}
                                </span>
                                <span>{question.prompt}</span>
                            </li>
                        ))}
                    </ol>
                ) : (
                    <p className="empty-questions">
                        Questions will appear here when the minigame starts.
                    </p>
                )}
            </section>

            <section className="game-data-section leaderboard-placeholder">
                <h2>Leaderboard</h2>
                <p>Available in a future update.</p>
            </section>
        </aside>
    );
}
