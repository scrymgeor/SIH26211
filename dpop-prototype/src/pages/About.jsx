const REAL = [
  ['ECDSA (P-256) device signatures', 'Scale and vision node each sign their payload; the backend verifies. Edit one byte and it fails.'],
  ['3-of-3 consensus engine', 'Identity, weight and vision must all agree before escrow releases funds.'],
  ['Hash-chained ledger', 'Every intake (accepted or blocked) is appended; any past edit breaks the chain.'],
  ['Escrow formula', 'Payout = weight × MSP rate, calculated by code, with no human in the loop.'],
  ['Fail-secure halts', 'Unplugged scale or covered camera stops the line. There is no manual override path.'],
];

const SIMULATED = [
  ['ESP32 + HX711 scale, PN532 NFC', 'The slider stands in for the load cell; the card selector for the NFC tap.'],
  ['Match-on-Card', 'Modelled as a boolean from the “card”. Real MoC runs inside the secure element.'],
  ['YOLOv8 grain model', 'A colour heuristic stands in until a model is fine-tuned on grain images. Set up ultralytics and DPOP_YOLO_WEIGHTS to plug the real one in.'],
  ['Hyperledger / Polygon + IPFS', 'The in-memory hash chain mimics the ledger, and the “CID” is derived from the image hash.'],
];

export default function About() {
  return (
    <div className="grid two">
      <section className="card">
        <h2>What’s real in this prototype</h2>
        <ul className="plain">
          {REAL.map(([t, d]) => (
            <li key={t}>
              <strong>{t}</strong>
              <span>{d}</span>
            </li>
          ))}
        </ul>
      </section>
      <section className="card">
        <h2>What’s simulated until the hardware arrives</h2>
        <ul className="plain">
          {SIMULATED.map(([t, d]) => (
            <li key={t}>
              <strong>{t}</strong>
              <span>{d}</span>
            </li>
          ))}
        </ul>
      </section>
      
    </div>
  );
}
