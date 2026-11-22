import "./Tabs.css"

export default function RequestTab({requests}) {
    return (
        <div className="request-tab">
            {requests.map((line, i) => (
                <div className="request" key={i}>
                    <p>{String(line)}</p>
                    <button className="accept">  ✓ </button>
                    <button className="decline"> X </button>
                </div>
            ))}
        </div>
    )
}
