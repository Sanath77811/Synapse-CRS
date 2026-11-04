import { Link } from "react-router-dom";
import { usePlatformContext } from "../context/PlatformContext";
import { formatTime, shortId } from "../lib/format";

export function SystemControl() {
  const { data, health, ready, mode, token } = usePlatformContext();
  return (
    <div className="control">
      <header>
        <p className="kicker">System control</p>
        <h1>Plant overview</h1>
        <Link to="/session">Session</Link>
      </header>
      <div className="control-grid">
        <section>
          <h2>Health</h2>
          <p>mode {mode}</p>
          <p>api {health?.status ?? "down"}</p>
          <p>ready {ready?.status ?? "unknown"}</p>
          <p>session {token ? "token present" : "none"}</p>
        </section>
        <section>
          <h2>Chain</h2>
          {data.chain ? (
            <p>
              valid={String(data.chain.valid)} · n={data.chain.event_count}
              <br />
              <span className="mono wrap">{data.chain.head_hash ?? "—"}</span>
            </p>
          ) : (
            <p className="dim">Not loaded.</p>
          )}
        </section>
      </div>
      <section className="ledger">
        <h2>Audit ledger</h2>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Seq</th>
                <th>Type</th>
                <th>Actor</th>
                <th>Time</th>
                <th>Hash</th>
              </tr>
            </thead>
            <tbody>
              {data.audit.map((row) => (
                <tr key={row.id}>
                  <td>{row.sequence}</td>
                  <td>{row.event_type}</td>
                  <td>{row.actor}</td>
                  <td className="mono">{formatTime(row.timestamp)}</td>
                  <td className="mono">{shortId(row.event_hash)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
