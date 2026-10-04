import { useState } from 'react';
import { api, sceneUrl, toDataUrl } from '../api.js';
import { Pipeline } from '../components/Pipeline.jsx';

// The four corruption loopholes from the slides, plus the hardware fail-secure cases.
const ATTACKS = [
  {
    id: 'proxy',
    title: 'Identity hijacking',
    story: 'A middleman presents a farmer’s card with his own thumb to claim the MSP payout.',
    scene: 'clean_wheat',
    body: { finger: 'stranger' },
  },
  {
    id: 'weight',
    title: 'Weight tampering',
    story: 'An official edits the signed 50 kg reading down to 30 kg to pocket the surplus.',
    scene: 'clean_wheat',
    body: { forged_weight_kg: 30 },
  },
  {
    id: 'grading',
    title: 'Subjective grading fraud',
    story: 'Stones and dirt are used as the excuse to downgrade the crop. The camera measures it objectively.',
    scene: 'wheat_with_stones',
    body: {},
  },
  {
    id: 'sand',
    title: 'Scale spoofing',
    story: 'Sand is weighed and declared as wheat to draw MSP funds for non-farm goods.',
    scene: 'sand_fake',
    body: {},
  },
  {
    id: 'unplug',
    title: 'Scale unplugged',
    story: 'Someone cuts the scale to force a manual override. There is none, so the line halts.',
    scene: 'clean_wheat',
    body: { scale_unplugged: true },
  },
  {
    id: 'cover',
    title: 'Camera covered',
    story: 'The lens is blocked so nothing can be verified. Intake halts (fail-secure).',
    scene: 'clean_wheat',
    body: { camera_covered: true },
  },
];

export default function ThreatLab({ onDone }) {
  const [active, setActive] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function launch(a) {
    setActive(a.id);
    setBusy(true);
    setResult(null);
    setError('');
    try {
      const image_b64 = await toDataUrl(sceneUrl(a.scene));
      const r = await api.procure({
        card_id: 'CARD-7F3A-1002',
        declared_crop: 'wheat',
        true_weight_kg: 50,
        image_b64,
        ...a.body,
      });
      setResult(r);
      onDone?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const current = ATTACKS.find((a) => a.id === active);

  return (
    <div className="grid two">
      <section className="card">
        <h2>Threat lab</h2>
        <p className="muted">Fire each known corruption pattern at the pipeline and see which oracle catches it.</p>
        <div className="attacks">
          {ATTACKS.map((a) => (
            <button key={a.id} className={'attack' + (active === a.id ? ' on' : '')} disabled={busy} onClick={() => launch(a)}>
              <strong>{a.title}</strong>
              <span>{a.story}</span>
            </button>
          ))}
        </div>
        {error && <p className="err">{error}</p>}
      </section>
      <section className="card">
        <h2>{current ? current.title : 'Result'}</h2>
        {current && <p className="muted">{current.story}</p>}
        <Pipeline result={result} />
      </section>
    </div>
  );
}
