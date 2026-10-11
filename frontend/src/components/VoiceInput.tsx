import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Send, CheckCircle2, AlertCircle, Sparkles, X } from 'lucide-react';
import { parseNaturalLanguageInput, type ParsedWorkday } from '../services/nlpParser';
import type { TaskCatalogItem, TaskItemInput } from '../types/api';

interface VoiceInputProps {
  catalog: Record<string, TaskCatalogItem>;
  onApplyParsedPlan: (parsed: {
    crewSize?: number;
    shiftStart?: number;
    shiftEnd?: number;
    newCrew?: boolean;
    grapStage?: number;
    tasks: TaskItemInput[];
  }) => void;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({ catalog, onApplyParsedPlan }) => {
  const [isListening, setIsListening] = useState(false);
  const [language, setLanguage] = useState<'hi-IN' | 'en-IN'>('hi-IN');
  const [transcript, setTranscript] = useState('');
  const [textInput, setTextInput] = useState('');
  const [speechSupported, setSpeechSupported] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [parsedReview, setParsedReview] = useState<ParsedWorkday | null>(null);

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setIsListening(true);
        setErrorMessage(null);
      };

      recognition.onresult = (event: any) => {
        let currentTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          currentTranscript += event.results[i][0].transcript;
        }
        setTranscript(currentTranscript);
        setTextInput(currentTranscript);
      };

      recognition.onerror = (event: any) => {
        setIsListening(false);
        if (event.error === 'not-allowed') {
          setErrorMessage('Microphone access denied. Please grant browser permissions or use text entry.');
        } else if (event.error === 'no-speech') {
          setErrorMessage('No speech detected. Try speaking closer to the microphone.');
        } else {
          setErrorMessage(`Speech recognition error: ${event.error}`);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    } catch (e) {
      setSpeechSupported(false);
    }
  }, []);

  const handleToggleListening = () => {
    if (!speechSupported || !recognitionRef.current) {
      setErrorMessage('Speech Recognition is not supported on this browser. Please use the text entry below.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      setErrorMessage(null);
      setTranscript('');
      recognitionRef.current.lang = language;
      try {
        recognitionRef.current.start();
      } catch (err: any) {
        setErrorMessage('Could not start microphone: ' + err.message);
      }
    }
  };

  const handleParseAndReview = (rawTextToParse?: string) => {
    const textToUse = rawTextToParse || textInput || transcript;
    if (!textToUse.trim()) return;

    const parsed = parseNaturalLanguageInput(textToUse, catalog);
    setParsedReview(parsed);
  };

  const handleConfirmAndApply = () => {
    if (!parsedReview) return;

    onApplyParsedPlan({
      crewSize: parsedReview.crewSize,
      shiftStart: parsedReview.shiftStart,
      shiftEnd: parsedReview.shiftEnd,
      newCrew: parsedReview.newCrew,
      grapStage: parsedReview.grapStage,
      tasks: parsedReview.tasks.length > 0 ? parsedReview.tasks : [],
    });

    setParsedReview(null);
    setTextInput('');
    setTranscript('');
  };

  const handleSampleClick = (sample: string) => {
    setTextInput(sample);
    handleParseAndReview(sample);
  };

  return (
    <div className="field-card" style={{ marginBottom: '1.25rem', background: '#ffffff', border: '1.5px solid var(--border-light)' }}>
      <div className="panel-header" style={{ marginBottom: '0.75rem' }}>
        <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Sparkles size={20} className="text-emerald-600" />
          <span>Multimodal Workday Assistant (Voice & Text)</span>
        </div>
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          <button
            onClick={() => setLanguage('hi-IN')}
            className={`nav-tab-btn ${language === 'hi-IN' ? 'active' : ''}`}
            style={{
              cursor: 'pointer',
              border: language === 'hi-IN' ? '1px solid var(--state-go-border)' : '1px solid var(--border-light)',
              background: language === 'hi-IN' ? 'var(--state-go-bg)' : '#ffffff',
              color: language === 'hi-IN' ? 'var(--state-go-text)' : 'var(--text-muted)',
              fontSize: '0.78rem',
              padding: '0.3rem 0.65rem',
            }}
          >
            हिंदी (Hindi)
          </button>
          <button
            onClick={() => setLanguage('en-IN')}
            className={`nav-tab-btn ${language === 'en-IN' ? 'active' : ''}`}
            style={{
              cursor: 'pointer',
              border: language === 'en-IN' ? '1px solid var(--state-go-border)' : '1px solid var(--border-light)',
              background: language === 'en-IN' ? 'var(--state-go-bg)' : '#ffffff',
              color: language === 'en-IN' ? 'var(--state-go-text)' : 'var(--text-muted)',
              fontSize: '0.78rem',
              padding: '0.3rem 0.65rem',
            }}
          >
            English
          </button>
        </div>
      </div>

      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
        Speak or type your daily workforce instructions. WorkWise extracts tasks, durations, and crew numbers for your review before planning.
      </p>

      {/* Voice Mic + Text Input Row */}
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.75rem' }}>
        {/* Large Ergonomic Mic Button */}
        <button
          onClick={handleToggleListening}
          className={`mic-button ${isListening ? 'listening' : ''}`}
          style={{
            width: 54,
            height: 54,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            cursor: 'pointer',
            border: isListening ? '2px solid var(--state-stop)' : '2px solid var(--state-go)',
            background: isListening ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.2)',
            color: isListening ? '#ef4444' : '#10b981',
            boxShadow: isListening ? '0 0 20px rgba(239, 68, 68, 0.4)' : '0 0 15px rgba(16, 185, 129, 0.25)',
            transition: 'all 0.2s ease',
          }}
          title={isListening ? 'Tap to Stop Listening' : 'Tap to Speak'}
          aria-label="Voice input microphone"
        >
          {isListening ? <MicOff size={26} /> : <Mic size={26} />}
        </button>

        {/* Text Input Field */}
        <div style={{ flex: 1, position: 'relative' }}>
          <input
            type="text"
            placeholder={
              language === 'hi-IN'
                ? 'उदा: "18 मजदूर, कंक्रीट 3 घंटे, सरिया 4 घंटे, शिफ्ट 6 से 18"...'
                : 'e.g. "18 workers, concrete for 3 hours, rebar for 4 hours, shift 6 AM to 6 PM"...'
            }
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleParseAndReview()}
            style={{
              width: '100%',
              padding: '0.8rem 3rem 0.8rem 1rem',
              background: '#f8fafc',
              border: '1.5px solid var(--border-light)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-main)',
              fontSize: '0.9rem',
              outline: 'none',
            }}
          />
          <button
            onClick={() => handleParseAndReview()}
            disabled={!textInput.trim()}
            style={{
              position: 'absolute',
              right: 8,
              top: '50%',
              transform: 'translateY(-50%)',
              background: 'none',
              border: 'none',
              color: textInput.trim() ? 'var(--state-go-text)' : 'var(--text-muted)',
              cursor: textInput.trim() ? 'pointer' : 'default',
              padding: 6,
            }}
            title="Parse instructions"
          >
            <Send size={18} />
          </button>
        </div>
      </div>

      {/* Live Audio Listening Feedback */}
      {isListening && (
        <div
          style={{
            padding: '0.6rem 1rem',
            background: 'var(--state-stop-bg)',
            border: '1px dashed var(--state-stop-border)',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            color: 'var(--state-stop-text)',
            fontSize: '0.85rem',
          }}
        >
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#dc2626', animation: 'pulse 1s infinite' }} />
          <span>Listening ({language === 'hi-IN' ? 'सुन रहे हैं...' : 'listening...'}): <em>{transcript || 'Speak now...'}</em></span>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div
          style={{
            padding: '0.5rem 0.8rem',
            background: 'var(--state-stop-bg)',
            border: '1px solid var(--state-stop-border)',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '0.75rem',
            color: 'var(--state-stop-text)',
            fontSize: '0.82rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Quick Example Voice Chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', alignItems: 'center' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Try demo phrases:</span>
        <button
          onClick={() => handleSampleClick('18 workers, concrete for 3 hours, rebar for 4 hours, shift 6 AM to 6 PM')}
          className="badge-value"
          style={{ cursor: 'pointer', background: '#f1f5f9', border: '1px solid var(--border-light)', color: 'var(--text-main)', fontSize: '0.75rem' }}
        >
          18 workers, concrete 3h, rebar 4h (6 AM – 6 PM)
        </button>
        <button
          onClick={() => handleSampleClick('Aaj 20 mazdoor hain, sariya teen ghante, dhalai chaar ghante, subah 6 se shaam 6')}
          className="badge-value"
          style={{ cursor: 'pointer', background: '#f1f5f9', border: '1px solid var(--border-light)', color: 'var(--text-main)', fontSize: '0.75rem' }}
        >
          20 मजदूर, सरिया 3h, ढलाई 4h (सुबह 6 से शाम 6)
        </button>
        <button
          onClick={() => handleSampleClick('New unacclimated crew, 15 workers, material prep 2 hours, painting 3 hours')}
          className="badge-value"
          style={{ cursor: 'pointer', background: '#f1f5f9', border: '1px solid var(--border-light)', color: 'var(--text-main)', fontSize: '0.75rem' }}
        >
          New unacclimated crew (15 workers, prep 2h, paint 3h)
        </button>
      </div>

      {/* Confirmation & Review Modal */}
      {parsedReview && (
        <div className="modal-overlay" onClick={() => setParsedReview(null)}>
          <div className="modal-sheet" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle2 size={22} className="text-emerald-600" />
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800 }}>Confirm Workday Parameters</h3>
              </div>
              <button
                onClick={() => setParsedReview(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
              WorkWise parsed the following from: <strong style={{ color: 'var(--text-main)' }}>"{parsedReview.rawText}"</strong>. Please verify before applying to today's setup:
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
              {/* Crew Size */}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0.8rem', background: '#f8fafc', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Crew Size:</span>
                <strong style={{ color: 'var(--state-go-text)' }}>{parsedReview.crewSize ? `${parsedReview.crewSize} Workers` : 'Kept as configured'}</strong>
              </div>

              {/* Shift Hours */}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0.8rem', background: '#f8fafc', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Shift Hours:</span>
                <strong>{parsedReview.shiftStart && parsedReview.shiftEnd ? `${parsedReview.shiftStart}:00 – ${parsedReview.shiftEnd}:00` : 'Kept as configured'}</strong>
              </div>

              {/* Acclimatization */}
              {parsedReview.newCrew && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0.8rem', background: 'var(--state-ease-bg)', border: '1px solid var(--state-ease-border)', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--state-ease-text)' }}>Acclimatization:</span>
                  <strong style={{ color: 'var(--state-ease-text)' }}>New / Unacclimated Crew (Strict NIOSH Limits)</strong>
                </div>
              )}

              {/* Tasks Extracted */}
              <div style={{ padding: '0.6rem 0.8rem', background: '#f8fafc', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-sm)' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.4rem' }}>
                  Identified Activities ({parsedReview.tasks.length}):
                </span>
                {parsedReview.tasks.length === 0 ? (
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-dim)' }}>No specific task matched. Existing task list will be retained.</span>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    {parsedReview.tasks.map((t) => {
                      const item = catalog[t.id];
                      return (
                        <span key={t.id} className="badge-value" style={{ background: 'var(--state-go-bg)', color: 'var(--state-go-text)', border: '1px solid var(--state-go-border)' }}>
                          {item ? item.label : t.id} ({t.duration_h}h)
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setParsedReview(null)}
                style={{
                  padding: '0.6rem 1.2rem',
                  background: 'transparent',
                  border: '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Cancel / Edit
              </button>
              <button
                onClick={handleConfirmAndApply}
                className="btn-primary"
                style={{ padding: '0.6rem 1.4rem' }}
              >
                <CheckCircle2 size={18} />
                Confirm & Apply Setup
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
