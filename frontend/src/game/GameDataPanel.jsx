import { useEffect, useState } from "react";
import "./GameDataPanel.css";

const EMPTY_GAME_DATA = {
    sessionName: "Session",
    gameType: "",
    questions: [],
    progress: { completed: 0, total: 0 },
};

export default function GameDataPanel({ gameData = EMPTY_GAME_DATA }) {
    const data = gameData || EMPTY_GAME_DATA;
    const [now, setNow] = useState(0);
    const [selectedQuestionId, setSelectedQuestionId] = useState(null);
    useEffect(() => {
        if (!data.deadline || data.finished) return;
        const initial = window.setTimeout(() => setNow(Date.now()), 0);
        const timer = window.setInterval(() => setNow(Date.now()), 1000);
        return () => {
            window.clearTimeout(initial);
            window.clearInterval(timer);
        };
    }, [data.deadline, data.finished]);
    const questions = data.questions || [];
    const selectedIndex = questions.findIndex(
        (question, index) => (question.id ?? index) === selectedQuestionId
    );
    const currentIndex = selectedIndex >= 0 ? selectedIndex : 0;
    const currentQuestion = questions[currentIndex];
    const changeQuestion = (offset) => {
        setSelectedQuestionId(previousId => {
            const previousIndex = questions.findIndex(
                (question, index) => (question.id ?? index) === previousId
            );
            const index = previousIndex >= 0 ? previousIndex : 0;
            const nextIndex = (index + offset + questions.length) % questions.length;
            return questions[nextIndex].id ?? nextIndex;
        });
    };
    const completed = data.progress?.completed || 0;
    const total = data.progress?.total || 0;
    const percentage = total > 0 ? Math.min(100, (completed / total) * 100) : 0;
    const remaining = data.deadline ? Math.max(0, Math.ceil(data.deadline - now / 1000)) : 0;

    return (
        <aside className="game-data-panel" aria-label="Game data">
            <header className="game-data-header">
                <span className="game-data-eyebrow">Session</span>
                <h1>{data.sessionName || "Session"}</h1>
                {data.gameType && <span className="game-type">{data.gameType}</span>}
                {data.round > 0 && <p className="round-label">Round {data.round} of {data.rounds}</p>}
                {data.playType === "Versus" && data.deadline && !data.finished && <p className="round-timer">Time left: {now ? `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}` : "..."}</p>}
            </header>

            <div className="game-data-main">
                <section className="game-data-section questions-section">
                    <div className="game-data-section-heading question-heading">
                        <h2>Question</h2>
                        {currentQuestion ? (
                            <nav className="question-navigation" aria-label="Question navigation">
                                <button type="button" aria-label="Previous question" onClick={() => changeQuestion(-1)} disabled={questions.length < 2}>
                                    <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m12 4-6 6 6 6" /></svg>
                                </button>
                                <span>{currentIndex + 1} / {questions.length}</span>
                                <button type="button" aria-label="Next question" onClick={() => changeQuestion(1)} disabled={questions.length < 2}>
                                    <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m8 4 6 6-6 6" /></svg>
                                </button>
                            </nav>
                        ) : <span>0 / 0</span>}
                    </div>
                    {currentQuestion ? (
                        <article
                            key={currentQuestion.id ?? currentIndex}
                            className={`question-item ${currentQuestion.status || "pending"}`}
                            aria-live="polite"
                        >
                            <p className="question-prompt">{currentQuestion.prompt}</p>
                            <span className="question-status">
                                {currentQuestion.status === "completed" ? "Completed" : "To do"}
                            </span>
                        </article>
                    ) : (
                        <p className="empty-questions">
                            Questions will appear here when the minigame starts.
                        </p>
                    )}
                </section>

            </div>

            <section className="game-data-section progress-section">
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
        </aside>
    );
}
