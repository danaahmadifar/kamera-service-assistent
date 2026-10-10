import { useState } from 'react';

export default function CameraStatus() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function loadStatus() {
    if (loading) return;
    setResult(null);
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/cameras/CAM-03/status', {
        method: 'GET',
        signal: AbortSignal.timeout(15000),
      });
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error(`Keine JSON-Antwort erhalten (HTTP ${response.status}). Prüfe die Python-API auf Port 8000.`);
      }
      if (!response.ok) {
        const detail = typeof data?.detail === 'string' ? data.detail : 'Statusabruf fehlgeschlagen.';
        throw new Error(`HTTP ${response.status}: ${detail}`);
      }
      const status = data?.status;
      const check = data?.temperature_check;
      if (status?.camera_id !== 'CAM-03' || status.simulated !== true
          || status.sensor !== 'board_temperature' || !Number.isFinite(status.temperature_c)
          || typeof status.measured_at !== 'string' || !status.measured_at.trim()
          || check?.camera_id !== status.camera_id || check.sensor !== status.sensor
          || check.temperature_c !== status.temperature_c
          || typeof check.within_range !== 'boolean' || typeof check.reference !== 'string'
          || !Number.isFinite(check.minimum_c) || !Number.isFinite(check.maximum_c)) {
        throw new Error('Unerwartetes Format der simulierten Statusdaten oder der Temperaturprüfung.');
      }
      setResult(data);
    } catch (error) {
      if (error.name === 'TimeoutError' || error.name === 'AbortError') {
        setError('Der Statusabruf hat nach 15 Sekunden keine Antwort geliefert. Prüfe die Python-API.');
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
    <section aria-labelledby="camera-status-heading">
      <h2 id="camera-status-heading">Simulierter Kamerastatus</h2>
      <button type="button" onClick={loadStatus} disabled={loading}>
        {loading ? 'Status wird abgerufen …' : 'Simulierten Status von CAM-03 abrufen'}
      </button>
      {error && <p role="alert">{error}</p>}
      {loading && <p role="status">Status wird abgerufen. Bitte warte.</p>}
      {result && (
        <>
          <dl>
            <dt>Kamera</dt><dd>{result.status.camera_id}</dd>
            <dt>Sensor</dt><dd>{result.status.sensor}</dd>
            <dt>Temperatur</dt><dd>{result.status.temperature_c} °C</dd>
            <dt>Messzeitpunkt</dt><dd>{result.status.measured_at}</dd>
            <dt>Python-Bereichsprüfung</dt>
            <dd>{result.temperature_check.within_range ? 'Innerhalb des zulässigen Bereichs' : 'Außerhalb des zulässigen Bereichs'}</dd>
            <dt>Zulässiger Bereich</dt>
            <dd>{result.temperature_check.minimum_c} bis einschließlich {result.temperature_check.maximum_c} °C</dd>
            <dt>Grenzwertquelle</dt><dd>{result.temperature_check.reference}</dd>
          </dl>
          <p>Messdatenquelle: Simulation über camera_tools.get_camera_status. Prüfung: camera_tools.evaluate_temperature.</p>
          <p>Diese Daten belegen keinen aktuellen Live-Zustand. Die interne Temperatur bestätigt keine Bildqualität; eine Bereichsüberschreitung allein beweist keinen Defekt.</p>
        </>
      )}
    </section>
  );
}
