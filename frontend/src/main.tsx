import { createRoot } from "react-dom/client";
import AuthGate from "./AuthGate";
import "./styles.css";
import "./chat.css";
import "./privacy.css";
createRoot(document.getElementById("root")!).render(<AuthGate />);
