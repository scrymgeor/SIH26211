async function j(res) {
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  state: () => fetch('/api/state').then(j),
  scenes: () => fetch('/api/scenes').then(j),
  procure: (body) =>
    fetch('/api/procure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(j),
  tamper: (h) => fetch(`/api/ledger/tamper/${h}`, { method: 'POST' }).then(j),
  reset: () => fetch('/api/ledger/reset', { method: 'POST' }).then(j),
};

export const sceneUrl = (name) => `/api/scene/${name}.png`;

// fetch a scene (or read an uploaded File) as a data URL the backend can analyse
export async function toDataUrl(blobOrUrl) {
  const blob = typeof blobOrUrl === 'string' ? await (await fetch(blobOrUrl)).blob() : blobOrUrl;
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(blob);
  });
}

export const inr = (n) => '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 });
