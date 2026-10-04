import { useState } from 'react';
import Terminal from './pages/Terminal.jsx';
import ThreatLab from './pages/ThreatLab.jsx';
import Dashboard from './pages/Dashboard.jsx';
import About from './pages/About.jsx';

const TABS = [
  ['terminal', 'Intake terminal'],
  ['threats', 'Threat lab'],
  ['dashboard', 'Audit dashboard'],
  ['about', 'About'],
];

export default function App() {
  const [tab, setTab] = useState('terminal');
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = () => setRefreshKey((k) => k + 1);

  return (
    <div className="shell">
      <header>
        <div className="brand">
          <div className="logo">W</div>
          <div>
            <h1>DPOP</h1>
            <span>Decentralized Proof-of-Procurement · Team The W.A.L.L. · SIH 2026 · PS26211</span>
          </div>
        </div>
        <nav>
          {TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? 'on' : ''} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {/* keep pages mounted so results survive tab switches */}
        <div hidden={tab !== 'terminal'}>
          <Terminal onDone={bump} />
        </div>
        <div hidden={tab !== 'threats'}>
          <ThreatLab onDone={bump} />
        </div>
        <div hidden={tab !== 'dashboard'}>
          <Dashboard refreshKey={refreshKey} />
        </div>
        <div hidden={tab !== 'about'}>
          <About />
        </div>
      </main>
    </div>
  );
}
