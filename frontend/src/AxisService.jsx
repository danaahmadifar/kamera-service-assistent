import { useState } from 'react';

const scenarios = [
  { id: 'no_video', label: 'Geräteabruf erfolgreich, Videobild benutzergemeldet fehlend' },
  { id: 'unreachable', label: 'Geräteabruf ohne rechtzeitige Antwort (Timeout)' },
  { id: 'access_denied', label: 'Geräteabruf abgewiesen' },
];

const outcomes = {
  success: 'Geräteinformationen erfolgreich abgerufen (Simulation)',
  timeout: 'Keine rechtzeitige Antwort auf den Geräteabruf (Simulation)',
  access_denied: 'Geräteabruf abgewiesen (Simulation)',
};

export default function AxisService() {
  const [scenario, setScenario] = useState('no_video');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;
    setResult(null);
    setError('');
    setLoading(true);
    try {
      const response = await fetch('/api/axis/service', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario }),
        signal: AbortSignal.timeout(360000),
      });
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error(`Keine JSON-Antwort erhalten (HTTP ${response.status}). Prüfe die API und den Webserver.`);
      }
      if (!response.ok) {
        const detail = typeof data?.detail === 'string' ? data.detail : 'Servicevorschlag konnte nicht erstellt werden.';
        throw new Error(`HTTP ${response.status}: ${detail}`);
      }
      const serviceCase = data?.case;
      if (serviceCase?.simulated !== true || serviceCase.scenario_id !== scenario
          || !Object.hasOwn(outcomes, serviceCase.device_info?.outcome)
          || !['not_checked', 'reported_missing'].includes(serviceCase.video?.observation)
          || serviceCase.video.transport !== null
          || typeof data.answer !== 'string' || !data.answer.trim()
          || data.finish_reason !== 'stop'
          || typeof data.notice !== 'string' || !data.notice.trim()
          || !Array.isArray(data.sources) || !data.sources.length
          || !data.sources.every((source) => typeof source?.source === 'string'
            && source.source.trim() && typeof source.section === 'string' && source.section.trim())) {
        throw new Error('Unerwartetes Format des simulierten Axis-Servicefalls.');
      }
      if (serviceCase.device_info.outcome === 'success') {
        const properties = serviceCase.device_info.response?.data?.propertyList;
        if (!properties || !['Brand', 'ProdNbr', 'Version'].every(
          (field) => typeof properties[field] === 'string' && properties[field].trim()
        )) {
          throw new Error('Die simulierten Geräteinformationen sind unvollständig.');
        }
      }
      setResult(data);
    } catch (error) {
      if (error.name === 'TimeoutError' || error.name === 'AbortError') {
        setError('Die Wartezeit von sechs Minuten ist abgelaufen. Die Verarbeitung kann auf dem Server weiterlaufen. Prüfe die Server-Logs.');
      } else if (error instanceof TypeError) {
        setError('Verbindung fehlgeschlagen. Prüfe den Webserver und die API.');
      } else {
        setError(error.message);
      }
    } finally {
      setLoading(false);
    }
  }

  const properties = result?.case.device_info.response?.data?.propertyList;

  return (
    <section aria-labelledby="axis-service-heading">
      <h2 id="axis-service-heading">Axis-Service: Kein Videobild</h2>
      <p>Proof of Concept für AXIS M2035-LE. Geräteantworten und Benutzerangaben sind simuliert;
        die Hinweise beruhen auf Zusammenfassungen offizieller Axis-Unterlagen. Keine reale Kamera angebunden.</p>
      <form onSubmit={handleSubmit}>
        <label htmlFor="axis-scenario">Simulierten Servicefall auswählen</label>
        <select id="axis-scenario" value={scenario} disabled={loading}
          onChange={(event) => {
            setScenario(event.target.value);
            setResult(null);
            setError('');
          }}>
          {scenarios.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
        <button type="submit" disabled={loading}>
          {loading ? 'Servicevorschlag wird erstellt …' : 'Axis-Servicevorschlag erstellen'}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {loading && <p role="status">Der simulierte Fall und die Quellen werden an das Modell übergeben. Bitte warte.</p>}
      {result && (
        <>
          <h3>Simulierte Datenbasis dieses Vorschlags</h3>
          <dl>
            <dt>Geräteabruf</dt><dd>{outcomes[result.case.device_info.outcome]}</dd>
            <dt>Videobeobachtung</dt>
            <dd>{result.case.video.observation === 'reported_missing'
              ? 'Benutzerangabe: kein Videobild (Simulation); kein geprüfter Stream-Befund'
              : 'Videostream nicht geprüft'}</dd>
            <dt>Übertragungsmodus</dt><dd>Unbekannt</dd>
            {properties && <>
              <dt>Modellkennung</dt><dd>{properties.Brand} {properties.ProdNbr}</dd>
              <dt>Gerätesoftware</dt><dd>{properties.Version} (simulierter Platzhalter)</dd>
            </>}
          </dl>
          <h3>Servicevorschlag – manuell zu prüfen</h3>
          <p className="answer">{result.answer}</p>
          <h3>Mitgesendete Dokumentabschnitte</h3>
          <ul>{result.sources.map((source) => (
            <li key={`${source.source}|${source.section}`}>{source.source} | {source.section}</li>
          ))}</ul>
          <p>{result.notice}</p>
        </>
      )}
    </section>
  );
}
