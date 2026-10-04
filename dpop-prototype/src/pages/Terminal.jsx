import { useEffect, useState } from 'react';
import { api, sceneUrl, toDataUrl } from '../api.js';
import { Pipeline, VisionView } from '../components/Pipeline.jsx';

const SCENE_LABELS = {
  clean_wheat: 'Clean wheat',
  clean_paddy: 'Clean paddy',
  wheat_with_stones: 'Wheat + stones/dirt',
  sand_fake: 'Sand (fake grain)',
};

export default function Terminal({ onDone }) {
  const [state, setState] = useState(null);
  const [card, setCard] = useState('CARD-7F3A-1001');
  const [finger, setFinger] = useState('enrolled');
  const [crop, setCrop] = useState('wheat');
  const [weight, setWeight] = useState(50);
  const [scene, setScene] = useState('clean_wheat');
  const [upload, setUpload] = useState(null); // { url, file }
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [shownImage, setShownImage] = useState(null);

  useEffect(() => {
    api.state().then(setState).catch((e) => setError(e.message));
  }, []);

  const imageSrc = upload ? upload.url : sceneUrl(scene);

  async function run() {
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const image_b64 = await toDataUrl(upload ? upload.file : sceneUrl(scene));
      const r = await api.procure({
        card_id: card,
        finger,
        declared_crop: crop,
        true_weight_kg: Number(weight),
        image_b64,
      });
      setShownImage(imageSrc);
      setResult(r);
      onDone?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function onFile(e) {
    const file = e.target.files?.[0];
    if (file) setUpload({ file, url: URL.createObjectURL(file) });
  }

  if (error && !state)
    return (
      <div className="card bad-box">
        <strong>Can't reach the backend.</strong> Start it with{' '}
        <code>uvicorn main:app --port 8000</code> inside <code>backend/</code>.
        <div className="detail">{error}</div>
      </div>
    );
  if (!state) return <p className="muted">Connecting to the DPOP node…</p>;

  return (
    <div className="grid two">
      <section className="card">
        <h2>Ingestion terminal</h2>
        <p className="muted">Everything the farmer does at the procurement centre: tap, thumb, load the sack.</p>

        <label>Farmer smart card</label>
        <select value={card} onChange={(e) => setCard(e.target.value)}>
          {Object.entries(state.farmers).map(([id, f]) => (
            <option key={id} value={id}>
              {f.name} · {f.village}
            </option>
          ))}
        </select>

        <label>Thumbprint on the reader</label>
        <div className="seg">
          <button className={finger === 'enrolled' ? 'on' : ''} onClick={() => setFinger('enrolled')}>
            Card owner
          </button>
          <button className={finger === 'stranger' ? 'on' : ''} onClick={() => setFinger('stranger')}>
            Middleman (proxy)
          </button>
        </div>

        <label>Crop declared at the gate</label>
        <div className="seg">
          {['wheat', 'paddy'].map((c) => (
            <button key={c} className={crop === c ? 'on' : ''} onClick={() => setCrop(c)}>
              {c}
            </button>
          ))}
        </div>

        <label>
          Load cell reading <b>{weight} kg</b>
        </label>
        <input type="range" min="5" max="120" value={weight} onChange={(e) => setWeight(e.target.value)} />

        <label>What the camera sees</label>
        <div className="seg wrap">
          {Object.keys(SCENE_LABELS).map((s) => (
            <button
              key={s}
              className={!upload && scene === s ? 'on' : ''}
              onClick={() => {
                setUpload(null);
                setScene(s);
              }}
            >
              {SCENE_LABELS[s]}
            </button>
          ))}
        </div>
        <label className="file">
          or upload your own photo
          <input type="file" accept="image/*" onChange={onFile} />
        </label>

        <button className="primary" disabled={busy} onClick={run}>
          {busy ? 'Processing…' : 'Tap card & weigh'}
        </button>
        {error && <p className="err">{error}</p>}
      </section>

      <section className="card">
        <h2>Edge vision node</h2>
        <VisionView src={result ? shownImage : imageSrc} vision={result?.vision} />
        {result?.vision && (
          <p className="muted small">
            Engine: {result.vision.engine} · crop: <b>{result.vision.crop}</b> · foreign matter:{' '}
            <b>{(result.vision.foreign_fraction * 100).toFixed(1)}%</b>
          </p>
        )}
        <h2>Consensus pipeline</h2>
        <Pipeline result={result} />
      </section>
    </div>
  );
}
