import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePlatformContext } from "../context/PlatformContext";
import { PageHeader } from "../components/PageHeader";

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
    <div className="sign-in">
      <PageHeader
        kicker="Access"
        title="Operator session"
        summary="Control-plane routes require a bearer token from SYNAPSE_AUTH_TOKENS. The token is stored only in sessionStorage and is never rendered in full."
      />
      {healthError ? (
        <p className="error-banner">
          API is unreachable ({healthError}). Use demonstration mode rather than inventing live
          telemetry.
        </p>
      ) : (
        <p className="muted">Control plane {health?.status ?? "unchecked"}.</p>
      )}
      <form className="panel form" onSubmit={onSubmit}>
        <label>
          Bearer token
          <input
            type="password"
            autoComplete="off"
            minLength={16}
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="paste viewer or admin token"
          />
        </label>
        <div className="row-actions">
          <button type="submit" className="primary">
            Connect to live API
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => {
              enterDemo();
              navigate("/");
            }}
          >
            Enter demonstration mode
          </button>
        </div>
      </form>
    </div>
  );
}
