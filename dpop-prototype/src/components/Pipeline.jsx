import { useEffect, useState } from 'react';
import { inr } from '../api.js';

/** Bounding boxes over the grain image. Boxes are normalised [x, y, w, h]. */
export function VisionView({ src, vision }) {
  return (
    <div className="vision">
      {src ? <img src={src} alt="grain sack" /> : <div className="vision-empty">No image</div>}
      {vision?.detections?.map((d, i) => (
        <div
          key={i}
          className="bbox"
          style={{
            left: `${d.box[0] * 100}%`,
            top: `${d.box[1] * 100}%`,
            width: `${d.box[2] * 100}%`,
            height: `${d.box[3] * 100}%`,
          }}
        >
          <span>
            {d.label} {(d.conf * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  );
}

/** Reveals pipeline steps one by one, the way the terminal would stream them. */
export function Pipeline({ result }) {
  const [shown, setShown] = useState(0);

  useEffect(() => {
    setShown(0);
    if (!result) return;
    let i = 0;
    const t = setInterval(() => {
      i += 1;
      setShown(i);
      if (i >= result.steps.length) clearInterval(t);
    }, 380);
    return () => clearInterval(t);
  }, [result]);

  if (!result) return <p className="muted">Run an intake to see the pipeline.</p>;

  const done = shown >= result.steps.length;
  return (
    <div>
      <ol className="steps">
        {result.steps.slice(0, shown).map((s, i) => (
          <li key={i} className={s.ok ? 'ok' : 'bad'}>
            <span className="dot">{s.ok ? '✓' : '✕'}</span>
            <div>
              <strong>{s.name}</strong>
              <div className="detail">{s.detail}</div>
              {s.votes && (
                <div className="votes">
                  {Object.entries(s.votes).map(([k, v]) => (
                    <span key={k} className={'vote ' + (v ? 'ok' : 'bad')}>
                      {k}: {v ? 'YES' : 'NO'}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
      {done && (
        <div className={'verdict ' + (result.approved ? 'ok' : 'bad')}>
          {result.approved ? (
            <>
              <div className="big">{inr(result.payout_inr)} released</div>
              <div>
                Paid directly to {result.farmer.name} · block #{result.block.height} ·{' '}
                <code>{result.block.hash.slice(0, 16)}…</code>
              </div>
            </>
          ) : (
            <>
              <div className="big">Intake blocked</div>
              <div>Funds stay locked in escrow. Rejection logged as block #{result.block.height}.</div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
