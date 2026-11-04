import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePlatformContext } from "../context/PlatformContext";

export function SignIn() {
  const { enterLive, enterDemo, healthError, health } = usePlatformContext();
  const [token, setToken] = useState("");
  const navigate = useNavigate();

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const value = token.trim();
    if (value.length < 16) {
      return;
    }
    enterLive(value);
    navigate("/");
  }

  return (
    <div className="lock">
      <div className="lock-copy">
        <p className="kicker">Synapse-CRS</p>
        <h1>Operator lock</h1>
        <p>Bearer token from SYNAPSE_AUTH_TOKENS. Stored in sessionStorage only. Full token is never rendered.</p>
        {healthError ? (
          <p className="error-banner">API unreachable ({healthError}). Use demonstration mode.</p>
        ) : (
          <p className="dim">Control plane {health?.status ?? "unchecked"}.</p>
        )}
        <form onSubmit={onSubmit}>
          <label>
            Token
            <input
              type="password"
              autoComplete="off"
              minLength={16}
              value={token}
              onChange={(event) => setToken(event.target.value)}
            />
          </label>
          <div className="row-actions">
            <button type="submit" className="primary">
              Connect live
            </button>
            <button
              type="button"
              className="ghost"
              onClick={() => {
                enterDemo();
                navigate("/");
              }}
            >
              Demonstration mode
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
