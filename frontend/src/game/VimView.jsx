import { useSession } from "../components/SessionContext";

export default function VimView({ onClose }) {
    const { vimData } = useSession();
    

    return (
        <div className="vim">
            {vimData?.map((line, i) => (
                <p key={i}>{line}</p>
            ))}
        </div>
    );
}