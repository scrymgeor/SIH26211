import { Fragment, useEffect, useState, useCallback } from 'react';
import { api, inr } from '../api.js';

export default function Dashboard({ refreshKey }) {
  const [state, setState] = useState(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(null);

  const load = useCallback(() => {
    api.state().then(setState).catch((e) => setError(e.message));
  }, []);

  useEffect(load, [load, refreshKey]);

  if (error) return <div className="card bad-box">{error}</div>;
  if (!state) return <p className="muted">Loading ledger…</p>;

  const { totals, chain, ledger } = state;
  const rows = [...ledger].reverse();

  async function tamper(h) {
    await api.tamper(h);
    load();
  }
  async function reset() {
    await api.reset();
    load();
  }

  return (
    <div>
      <div className="stats">
        <div className="stat">
          <span>Disbursed</span>
          <b>{inr(totals.disbursed_inr)}</b>
        </div>
        <div className="stat">
          <span>Grain procured</span>
          <b>{totals.kg_procured} kg</b>
        </div>
        <div className="stat">
          <span>Accepted</span>
          <b>{totals.accepted}</b>
        </div>
        <div className="stat">
          <span>Blocked</span>
          <b>{totals.rejected}</b>
        </div>
        <div className={'stat ' + (chain.valid ? 'okbg' : 'badbg')}>
          <span>Ledger integrity</span>
          <b>{chain.valid ? 'Valid' : `Broken at #${chain.broken_at}`}</b>
        </div>
      </div>

      <section className="card">
        <div className="row-between">
          <h2>Audit ledger</h2>
          <button className="ghost" onClick={reset}>
            Reset demo
          </button>
        </div>
        <p className="muted small">
          Each block stores the hash of the previous one. Try “Tamper” on a procurement block, which silently cuts the
          recorded weight by 10%, and watch integrity break.
        </p>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Type</th>
              <th>Detail</th>
              <th>Hash</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((b) => (
              <Fragment key={b.height}>
                <tr className={b.kind} onClick={() => setOpen(open === b.height ? null : b.height)}>
                  <td>{b.height}</td>
                  <td>
                    <span className={'tag ' + b.kind}>{b.kind}</span>
                  </td>
                  <td>
                    {b.kind === 'procurement' &&
                      `${b.data.farmer} · ${b.data.weight_kg} kg ${b.data.crop} · ${inr(b.data.payout_inr)}`}
                    {b.kind === 'rejected' && (b.data.reasons?.[0] || 'Rejected')}
                    {b.kind === 'genesis' && b.data.note}
                  </td>
                  <td>
                    <code>{b.hash.slice(0, 14)}…</code>
                  </td>
                  <td>
                    {b.kind !== 'genesis' && (
                      <button
                        className="ghost small"
                        onClick={(e) => {
                          e.stopPropagation();
                          tamper(b.height);
                        }}
                      >
                        Tamper
                      </button>
                    )}
                  </td>
                </tr>
                {open === b.height && (
                  <tr className="expand">
                    <td colSpan="5">
                      <pre>{JSON.stringify(b, null, 2)}</pre>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
