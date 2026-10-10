import { useState } from 'react';

export default function ServicePlan() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function loadPlan() {
    if (loading) return;
    setResult(null);
    setError('');
    setLoading(true);
    try {
      const response = await fetch('/api/cameras/CAM-03/plan', {
        method: 'POST',
        signal: AbortSignal.timeout(360000),
      });
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error(`Keine JSON-Antwort erhalten (HTTP ${response.status}). Prüfe die Python-API auf Port 8000.`);
      }
      if (!response.ok) {
        const detail = typeof data?.detail === 'string' ? data.detail : 'Planerstellung fehlgeschlagen.';
        throw new Error(`HTTP ${response.status}: ${detail}`);
      }
      if (!Array.isArray(data?.plan?.steps) || data.plan.steps.length < 3 || data.plan.steps.length > 5
          || !data.plan.steps.every((step) => step?.status === 'pending'
            && ['activity', 'purpose', 'source', 'section'].every((key) => typeof step[key] === 'string'))
          || data.status?.camera_id !== 'CAM-03' || data.status.simulated !== true
          || typeof data.status.sensor !== 'string' || !Number.isFinite(data.status.temperature_c)
          || typeof data.status.measured_at !== 'string'
          || typeof data.temperature_check?.within_range !== 'boolean'
          || typeof data.temperature_check.reference !== 'string') {
        throw new Error('Die API hat ein unerwartetes Planformat geliefert.');
      }
      setResult(data);
    } catch (error) {
      if (error.name === 'TimeoutError' || error.name === 'AbortError') {
        setError('Die Wartezeit von sechs Minuten ist abgelaufen. Prüfe die Server-Terminals; die Verarbeitung kann dort noch laufen.');
      } else if (error instanceof TypeError) {
        setError('Verbindung fehlgeschlagen. Prüfe, ob Vite und die Python-API laufen.');
      } else {
        setError(error.message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-labelledby="service-plan-heading">
      <h2 id="service-plan-heading">Prüfplan für CAM-03</h2>
      <p>Fiktives Szenario: unscharfes Bild; keine Sichtprüfung durchgeführt.</p>
      <button type="button" onClick={loadPlan} disabled={loading}>
        {loading ? 'Prüfplan wird erstellt …' : 'Optik-Prüfplan erstellen'}
      </button>
      {loading && <p role="status">Status und Dokumente werden abgerufen; der Plan wird erstellt und geprüft. Bitte warte.</p>}
      {error && <p role="alert">{error}</p>}
      {result && (
        <>
          <h3>Datenbasis dieses Plans</h3>
          <p>Simulation: {result.status.camera_id}, Sensor {result.status.sensor}, {result.status.temperature_c} °C.
            Messzeitpunkt: {result.status.measured_at}. Kein aktueller Live-Nachweis.</p>
          <p>Python-Temperaturprüfung: {result.temperature_check.within_range ? 'innerhalb' : 'außerhalb'} des zulässigen Bereichs.
            Quelle: {result.temperature_check.reference}. Dies bestätigt keine Bildqualität.</p>
          <h3>Noch durchzuführende Schritte</h3>
          <ol>
            {result.plan.steps.map((step, index) => (
              <li key={index}>
                <p><strong>Noch durchzuführen:</strong> {step.activity}</p>
                <p>Zweck: {step.purpose}</p>
                <p>Quelle: {step.source} | {step.section}</p>
              </li>
            ))}
          </ol>
          <p>Planformat und Quellenpaare geprüft. Prüfe weiterhin, ob jede Tätigkeit inhaltlich durch ihre Quelle belegt ist.</p>
        </>
      )}
    </section>
  );
}
