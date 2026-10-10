import { useState } from 'react';
import CameraStatus from './CameraStatus.jsx';
import ServicePlan from './ServicePlan.jsx';
import AxisService from './AxisService.jsx';

export default function App() {
  const [question, setQuestion] = useState('');
  const [submittedQuestion, setSubmittedQuestion] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;
    const trimmedQuestion = question.trim();
    setResult(null);

    if (!trimmedQuestion) {
      setError('Bitte gib eine Frage ein.');
      setSubmittedQuestion('');
      return;
    }

    setError('');
    setSubmittedQuestion(trimmedQuestion);
    setLoading(true);

    try {
      const response = await fetch('/api/documents/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmedQuestion }),
        signal: AbortSignal.timeout(360000),
      });

      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error(`Keine JSON-Antwort erhalten (HTTP ${response.status}). Prüfe, ob die Python-API auf Port 8000 läuft.`);
      }

      if (!response.ok) {
        const detail = typeof data?.detail === 'string' ? data.detail : 'Die Anfrage konnte nicht verarbeitet werden.';
        throw new Error(`HTTP ${response.status}: ${detail}`);
      }

      if (typeof data?.answer !== 'string' || !data.answer.trim()
          || typeof data.finish_reason !== 'string'
          || !Array.isArray(data.sources)
          || !data.sources.every((source) => typeof source?.source === 'string'
            && typeof source.section === 'string')) {
        throw new Error('Die API hat ein unerwartetes Antwortformat geliefert.');
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
    <main>
      <h1>Kamera-Service-Assistent</h1>
      <p>Lokaler Service-Assistent mit simulierten Geräten und dokumentierten Prüfhinweisen.</p>
      <AxisService />
      <h2>CAM-03: Dokumente und Temperaturprüfung (Simulation)</h2>
      <CameraStatus />
      <ServicePlan />
      <h2>Frage an die Dokumente</h2>
      <form onSubmit={handleSubmit}>
        <label htmlFor="question">Deine Frage</label>
        <input
          id="question"
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={1000}
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Antwort wird erstellt …' : 'Frage stellen'}
        </button>
      </form>

      {error && <p role="alert">{error}</p>}
      {loading && <p role="status">Dokumente werden durchsucht und die Antwort wird erstellt. Bitte warte.</p>}
      {submittedQuestion && (
        <section>
          <h2>Übernommene Frage</h2>
          <p>{submittedQuestion}</p>
        </section>
      )}
      {result && (
        <section>
          <h2>Antwort aus den Dokumenten</h2>
          <p className="answer">{result.answer}</p>
          {result.finish_reason === 'length' && (
            <p role="alert">Die Antwort wurde durch das Tokenlimit begrenzt und ist möglicherweise unvollständig.</p>
          )}
          {result.finish_reason !== 'stop' && result.finish_reason !== 'length' && (
            <p role="alert">Ungewöhnlicher Abbruchgrund: {result.finish_reason}. Prüfe die Antwort und die Server-Logs.</p>
          )}
          <h3>Mitgesendete Dokumentabschnitte</h3>
          <ul>
            {result.sources.map((source) => (
              <li key={`${source.source}|${source.section}`}>
                {source.source} | {source.section}
              </li>
            ))}
          </ul>
          <p>Prüfe, ob die Aussagen der Antwort durch die genannten Dokumentstellen belegt sind.</p>
        </section>
      )}
    </main>
  );
}
