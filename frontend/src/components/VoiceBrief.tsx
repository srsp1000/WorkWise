import React, { useState, useEffect, useRef } from 'react';
import type { PlanResponse } from '../types/api';
import { synthesizeAudioBrief } from '../services/api';
import {
  Volume2,
  VolumeX,
  Play,
  Pause,
  Share2,
  Printer,
  Languages,
  Check,
  Droplets,
} from 'lucide-react';

interface VoiceBriefProps {
  plan: PlanResponse;
  city?: string;
}

export const VoiceBrief: React.FC<VoiceBriefProps> = ({ plan, city }) => {
  const [lang, setLang] = useState<'hi' | 'en'>('hi');
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [playbackProgress, setPlaybackProgress] = useState<number>(0);
  const [shareSuccess, setShareSuccess] = useState(false);
  const [audioProvider, setAudioProvider] = useState<'idle' | 'amazon_polly' | 'browser_fallback'>('idle');
  const [isSynthesizing, setIsSynthesizing] = useState(false);

  const progressIntervalRef = useRef<any>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);

  const scheduled = plan.schedule.filter((s) => s.status === 'SCHEDULED');
  const unscheduled = plan.schedule.filter((s) => s.status === 'UNSCHEDULABLE');

  // Compute thermal protocol hours from plan matrix
  const heatHours = plan.matrix
    .filter((row) =>
      Object.values(row.tasks).some(
        (c) => c.state === 'EASE' || c.state === 'LIMIT' || c.state === 'STOP'
      )
    )
    .map((r) => new Date(r.time).getHours());

  let heatAdviceHi = 'मौसम अनुकूल है। कार्य स्थल पर स्वच्छ पेयजल और छायादार विश्राम की व्यवस्था रखें।';
  let heatAdviceEn = 'Weather conditions meet screening baseline. Maintain adequate cool potable water and shaded hydration stations.';

  if (heatHours.length > 0) {
    const minH = heatHours[0];
    const maxH = heatHours[heatHours.length - 1] + 1;
    const windowStr = `${minH}:00 से ${maxH}:00`;
    heatAdviceHi = `दोपहर ${windowStr} के दौरान अत्यधिक गर्मी का प्रभाव रहेगा। इस दौरान कार्य-विश्राम नियम का कड़ाई से पालन करें और हर 20 मिनट पर पानी पिएं।`;
    heatAdviceEn = `Peak heat protocol observed between ${minH}:00 and ${maxH}:00. Strictly enforce mandatory work-rest screening cycles and shaded hydration breaks.`;
  }

  // Dynamic verified text brief generator based strictly on evaluated schedule & recommendations
  const generateBriefText = (language: 'hi' | 'en') => {
    if (language === 'hi') {
      let text = `नमस्कार! ${city ? city + ' में ' : ''}आज WorkWise कार्य योजना: `;
      if (plan.top_recommendation) {
        text += `मुख्य निर्देश: ${plan.top_recommendation} `;
      }
      if (scheduled.length > 0) {
        text += scheduled
          .map((s) => `${s.task} का काम ${s.start} से ${s.end} बजे तक निर्धारित है। `)
          .join(' ');
      }
      text += heatAdviceHi;
      if (unscheduled.length > 0) {
        text += ` ध्यान दें, ${unscheduled.map((u) => u.task).join(', ')} का काम आज मौसम या प्रतिबंध के कारण स्थगित है।`;
      }
      return text;
    } else {
      let text = `Welcome! Today's WorkWise Work Plan${city ? ' for ' + city : ''}: `;
      if (plan.top_recommendation) {
        text += `Operational directive: ${plan.top_recommendation} `;
      }
      if (scheduled.length > 0) {
        text += scheduled
          .map((s) => `${s.task} is scheduled from ${s.start} to ${s.end}. `)
          .join(' ');
      }
      text += heatAdviceEn;
      if (unscheduled.length > 0) {
        text += ` Note: ${unscheduled.map((u) => u.task).join(', ')} is postponed today due to site screening limits.`;
      }
      return text;
    }
  };

  const briefText = generateBriefText(lang);

  // Clean up speech synthesis & HTML5 audio on unmount
  useEffect(() => {
    return () => {
      if (audioElementRef.current) {
        audioElementRef.current.pause();
        audioElementRef.current = null;
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, []);

  const startProgressTracking = (estimatedDurationSeconds: number) => {
    if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    const startTimestamp = Date.now();
    const durationMs = estimatedDurationSeconds * 1000;

    progressIntervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startTimestamp;
      const pct = Math.min(100, Math.round((elapsed / durationMs) * 100));
      setPlaybackProgress(pct);
      if (pct >= 100) {
        clearInterval(progressIntervalRef.current);
      }
    }, 250);
  };

  const playBrowserSpeech = () => {
    if (!('speechSynthesis' in window)) {
      alert('Browser does not support SpeechSynthesis.');
      setIsPlaying(false);
      setIsPaused(false);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(briefText);
    utterance.lang = lang === 'hi' ? 'hi-IN' : 'en-IN';
    utterance.rate = playbackSpeed;

    const wordsCount = briefText.split(/\s+/).length;
    const estimatedSec = Math.max(5, (wordsCount / 2.5) / playbackSpeed);

    utterance.onstart = () => {
      setIsPlaying(true);
      setIsPaused(false);
      setAudioProvider('browser_fallback');
      setPlaybackProgress(0);
      startProgressTracking(estimatedSec);
    };

    utterance.onend = () => {
      setIsPlaying(false);
      setIsPaused(false);
      setPlaybackProgress(100);
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    };

    utterance.onerror = () => {
      setIsPlaying(false);
      setIsPaused(false);
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  };

  const handleToggleAudio = async () => {
    // If audio is currently playing, handle pause / resume
    if (isPlaying) {
      if (audioElementRef.current) {
        if (isPaused) {
          audioElementRef.current.play();
          setIsPaused(false);
        } else {
          audioElementRef.current.pause();
          setIsPaused(true);
        }
        return;
      }
      if ('speechSynthesis' in window) {
        if (isPaused) {
          window.speechSynthesis.resume();
          setIsPaused(false);
        } else {
          window.speechSynthesis.pause();
          setIsPaused(true);
        }
        return;
      }
    }

    // Start playback: Try Amazon Polly neural first via /api/audio/synthesize
    handleStopAudio();
    setIsSynthesizing(true);

    try {
      const res = await synthesizeAudioBrief(
        briefText,
        lang === 'hi' ? 'hi-IN' : 'en-IN',
        'Kajal'
      );

      if (res && res.status === 'success' && res.audio_base64) {
        const audio = new Audio(`data:audio/mp3;base64,${res.audio_base64}`);
        audio.playbackRate = playbackSpeed;
        audioElementRef.current = audio;
        setAudioProvider('amazon_polly');

        audio.ontimeupdate = () => {
          if (audio.duration && audio.duration > 0) {
            const pct = Math.min(100, Math.round((audio.currentTime / audio.duration) * 100));
            setPlaybackProgress(pct);
          }
        };

        audio.onended = () => {
          setIsPlaying(false);
          setIsPaused(false);
          setPlaybackProgress(100);
          audioElementRef.current = null;
        };

        audio.onerror = () => {
          audioElementRef.current = null;
          playBrowserSpeech();
        };

        await audio.play();
        setIsPlaying(true);
        setIsPaused(false);
        setPlaybackProgress(0);
        return;
      } else {
        // Fallback to browser SpeechSynthesis
        playBrowserSpeech();
      }
    } catch {
      // Network or API failure fallback to browser SpeechSynthesis
      playBrowserSpeech();
    } finally {
      setIsSynthesizing(false);
    }
  };

  const handleStopAudio = () => {
    if (audioElementRef.current) {
      audioElementRef.current.pause();
      audioElementRef.current = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    setIsPlaying(false);
    setIsPaused(false);
    setPlaybackProgress(0);
  };

  const handleSpeedChange = (newSpeed: number) => {
    setPlaybackSpeed(newSpeed);
    if (audioElementRef.current) {
      audioElementRef.current.playbackRate = newSpeed;
    }
    if (isPlaying) {
      handleStopAudio();
    }
  };

  const shareBrief = () => {
    const shareData = {
      title: `WorkWise Plan: ${city || 'Construction Site'}`,
      text: briefText,
    };
    if (navigator.share) {
      navigator.share(shareData).catch(() => {});
    } else {
      navigator.clipboard.writeText(briefText);
      setShareSuccess(true);
      setTimeout(() => setShareSuccess(false), 2500);
    }
  };

  return (
    <div className="field-card">
      <div className="field-card-header">
        <div className="field-card-title">
          <Volume2 size={20} className="text-blue-700" />
          <span>Multimodal Daily Brief & Spoken Instructions</span>
        </div>

        <button
          onClick={() => {
            if (isPlaying) handleStopAudio();
            setLang(lang === 'hi' ? 'en' : 'hi');
          }}
          style={{
            border: '1px solid var(--border-strong)',
            background: '#ffffff',
            color: 'var(--brand-navy)',
            fontWeight: 700,
            fontSize: '0.8rem',
            padding: '0.4rem 0.8rem',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
          }}
        >
          <Languages size={15} /> {lang === 'hi' ? 'हिंदी → English' : 'English → हिंदी'}
        </button>
      </div>

      {/* Main Spoken Audio Player Card */}
      <div
        style={{
          background: '#ffffff',
          padding: '1.25rem',
          borderRadius: 'var(--radius-md)',
          border: '1.5px solid var(--border-light)',
          marginBottom: '1.25rem',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--brand-navy)' }}>
            {lang === 'hi' ? 'दैनिक कार्य दिशा-निर्देश (Site Briefing)' : 'Daily Shift Directive'}
          </h3>
          <span className="badge-status GO" style={{ fontSize: '0.7rem' }}>
            {audioProvider === 'amazon_polly'
              ? `Amazon Polly Neural (Kajal - ${lang === 'hi' ? 'hi-IN' : 'en-IN'})`
              : audioProvider === 'browser_fallback'
              ? `Browser Web Speech API (${lang === 'hi' ? 'hi-IN' : 'en-IN'})`
              : lang === 'hi'
              ? 'हिंदी स्वर (Kajal Neural / Speech API)'
              : 'English Voice (Kajal Neural / Speech API)'}
          </span>
        </div>

        <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--text-primary)', marginBottom: '1.25rem' }}>
          "{briefText}"
        </p>

        {/* Playback Progress Bar */}
        <div style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.3rem' }}>
            <span>{isPlaying ? (isPaused ? 'Paused' : 'Playing...') : 'Audio Progress'}</span>
            <span>{playbackProgress}%</span>
          </div>
          <div style={{ width: '100%', height: 6, background: 'var(--bg-muted)', borderRadius: 3, overflow: 'hidden' }}>
            <div
              style={{
                width: `${playbackProgress}%`,
                height: '100%',
                background: 'var(--brand-navy)',
                transition: 'width 0.2s ease',
              }}
            />
          </div>
        </div>

        {/* Player Controls & Action Buttons */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
          <button
            onClick={handleToggleAudio}
            disabled={isSynthesizing}
            className="btn-primary"
            style={{ padding: '0.65rem 1.25rem', opacity: isSynthesizing ? 0.7 : 1 }}
          >
            {isSynthesizing ? (
              <>
                <Volume2 size={16} /> Synthesizing Audio...
              </>
            ) : isPlaying && !isPaused ? (
              <>
                <Pause size={16} /> Pause Audio
              </>
            ) : (
              <>
                <Play size={16} /> {isPaused ? 'Resume Audio' : `Play Brief (${lang === 'hi' ? 'हिंदी' : 'English'})`}
              </>
            )}
          </button>

          {isPlaying && (
            <button
              onClick={handleStopAudio}
              style={{
                padding: '0.65rem 1rem',
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: 'var(--radius-md)',
                color: '#dc2626',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                fontWeight: 700,
                fontSize: '0.85rem',
              }}
            >
              <VolumeX size={16} /> Stop
            </button>
          )}

          {/* Speed Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', background: 'var(--bg-muted)', padding: '0.3rem 0.5rem', borderRadius: 'var(--radius-sm)' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>Speed:</span>
            {[0.85, 1.0, 1.15].map((spd) => (
              <button
                key={spd}
                onClick={() => handleSpeedChange(spd)}
                style={{
                  padding: '0.2rem 0.45rem',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  borderRadius: '3px',
                  border: 'none',
                  background: playbackSpeed === spd ? '#ffffff' : 'transparent',
                  color: playbackSpeed === spd ? 'var(--brand-navy)' : 'var(--text-muted)',
                  cursor: 'pointer',
                }}
              >
                {spd}x
              </button>
            ))}
          </div>

          <button
            onClick={shareBrief}
            style={{
              padding: '0.65rem 1rem',
              background: '#ffffff',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            {shareSuccess ? (
              <span style={{ color: '#059669', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Check size={16} /> Copied!
              </span>
            ) : (
              <>
                <Share2 size={16} /> Share Brief
              </>
            )}
          </button>

          <button
            onClick={() => window.print()}
            style={{
              padding: '0.65rem 1rem',
              background: '#ffffff',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
            title="Print 1-page physical briefing sheet"
          >
            <Printer size={16} /> Print Brief
          </button>
        </div>
      </div>

      {/* Mandatory Heat Rest Directive Card */}
      <div style={{ background: '#f8fafc', border: '1px solid var(--border-light)', borderRadius: 'var(--radius-md)', padding: '1rem', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', fontWeight: 800, color: 'var(--brand-navy)', fontSize: '0.95rem' }}>
          <Droplets size={18} className="text-blue-600" />
          <span>Rest & Hydration Directive</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem', fontSize: '0.82rem' }}>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block', fontWeight: 700 }}>Heat Protocol Window</span>
            <strong>{plan.rest_recommendations?.heat_protocol_window || 'Normal Operations'}</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block', fontWeight: 700 }}>Screening Work-Rest Cycle</span>
            <strong>{plan.rest_recommendations?.work_rest_cycle}</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block', fontWeight: 700 }}>Hydration Mandate</span>
            <span>{plan.rest_recommendations?.hydration_guideline}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block', fontWeight: 700 }}>Shade & Airflow</span>
            <span>{plan.rest_recommendations?.shade_requirement}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
