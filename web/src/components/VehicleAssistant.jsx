import { useEffect, useState, useCallback, useRef } from 'react';
import { 
  RotateCcw, Play, Square, Volume2, 
  ChevronDown, X, Zap 
} from 'lucide-react';
import { fetchSpeechToken, fetchSpeechIceToken } from '../api/services';
import {
    speakText as speakAvatarText,
    buildAvatarPipeline,
    initSpeechRecognizer
} from '../services/speechStreamService';
import { askAI } from '../api/services';

const LANGUAGE_OPTIONS = [
    { code: 'en-US', label: 'English', voice: 'en-US-AvaMultilingualNeural' },
    { code: 'ko-KR', label: 'Korean', voice: 'en-US-AvaMultilingualNeural' },
    { code: 'ja-JP', label: 'Japanese', voice: 'en-US-AvaMultilingualNeural' }
];

const VehicleAssistant = ({ vehicleId }) => {
    const recognizerRef = useRef(null);
    const synthesizerRef = useRef(null);
    const peerConnectionRef = useRef(null);
    const pipelineRef = useRef(null); // bundle { avatarSynthesizer, peerConnection, recognizer, speakText, stop }

    const speechTokenRef = useRef(null);
    const speechIceTokenRef = useRef(null);
    const tokenFetchedAtRef = useRef(0);

    const [region, setRegion] = useState('');
    const [tokenError, setTokenError] = useState(null);
    const [loadingTokens, setLoadingTokens] = useState(false);

    // --- UI states ---
    const [sessionActive, setSessionActive] = useState(false);
    const [avatarConnecting, setAvatarConnecting] = useState(false);
    const [avatarStreamReady, setAvatarStreamReady] = useState(false);
    const [avatarMuted, setAvatarMuted] = useState(true);
    const [message, setMessage] = useState('Hello! I am your in-vehicle assistant.');
    const [showSubtitles, setShowSubtitles] = useState(true);
    const [transcript, setTranscript] = useState([]);
    const [subtitleText, setSubtitleText] = useState('');
    const [isRecognizing, setIsRecognizing] = useState(false);
    const [selectedLanguage, setSelectedLanguage] = useState('en-US');
    const [avatarMeta, setAvatarMeta] = useState({ character: 'meg', style: 'formal', voice: 'en-US-AvaMultilingualNeural' });
    const [avatarEnabled, setAvatarEnabled] = useState(true); // Toggle avatar active/inactive
    const [continuousListening, setContinuousListening] = useState(false); // Continuous STT mode

    const videoRef = useRef(null);
    const audioRef = useRef(null);

    // --- Load Speech SDK (now only for cleanup) ---
    useEffect(() => {
        return () => {
            try { pipelineRef.current?.stop(); } catch { }
            pipelineRef.current = null;
            peerConnectionRef.current = null;
            synthesizerRef.current = null;
            recognizerRef.current = null;
        };
    }, []);

    // --- Token helpers ---
    const ensureSpeechToken = useCallback(async (force = false) => {
        const now = Date.now();
        if (
            !force &&
            speechTokenRef.current &&
            tokenFetchedAtRef.current &&
            (now - tokenFetchedAtRef.current) < 8 * 60 * 1000
        ) {
            return speechTokenRef.current;
        }
        try {
            setLoadingTokens(true);
            const data = await fetchSpeechToken(); // expects { token, region }
            if (!data || !data.token || !data.region) {
                setTokenError('Invalid speech token response.');
                return null;
            }
            speechTokenRef.current = data;
            tokenFetchedAtRef.current = now;
            setRegion(data.region);
            setTokenError(null);
            return data;
        } catch (e) {
            setTokenError(e.message || 'Token fetch failed');
            return null;
        } finally {
            setLoadingTokens(false);
        }
    }, []);

    const ensureSpeechIceToken = useCallback(async (force = false) => {
        if (!force && speechIceTokenRef.current) return speechIceTokenRef.current;
        try {
            const data = await fetchSpeechIceToken();
            speechIceTokenRef.current = data;
            return data;
        } catch {
            return null;
        }
    }, []);

    const stopSession = useCallback(() => {
        try {
            if (recognizerRef.current && continuousListening) {
                console.log('[VoiceControl] Stopping continuous recognition...');
                try {
                    recognizerRef.current.stopContinuousRecognitionAsync(
                        () => console.log('[VoiceControl] Continuous recognition stopped.'),
                        err => console.warn('[VoiceControl] Failed stopping continuous recognition:', err)
                    );
                } catch { }
            }
            pipelineRef.current?.stop();
        } catch { }
        pipelineRef.current = null;
        peerConnectionRef.current = null;
        synthesizerRef.current = null;
        recognizerRef.current = null;
        setSessionActive(false);
        setAvatarConnecting(false);
        setAvatarStreamReady(false);
        setSubtitleText('');
        setAvatarEnabled(false); // reset to enabled on full stop
        setContinuousListening(false);
    }, [continuousListening]);

    // Send recognized user speech to AI endpoint and speak AI response
    const sendToAI = useCallback(async (userText) => {
        if (!userText || !userText.trim()) return;
        setTranscript(p => [...p, `AI_REQUEST: ${userText}`]);
        try {
            const aiText = await askAI({
                messages: [{ role: 'user', content: userText }],
                languageCode: selectedLanguage
            });
            const safeText = aiText || '(no response)';
            setTranscript(p => [...p, `AI: ${safeText}`]);
            setMessage(safeText);
            if (synthesizerRef.current && safeText) {
                speakAvatarText(synthesizerRef.current, safeText, {
                    onStart: () => setTranscript(p => [...p, `SPEAKING: ${safeText}`])
                });
            }
        } catch (err) {
            // setTranscript(p => [...p, `AI_ERROR: ${err.message || err}`]);
            alert('AI request failed: ' + (err.message || err));
        }
    }, [selectedLanguage]);

    const startSession = useCallback(async () => {
        if (sessionActive || avatarConnecting) return;
        setAvatarConnecting(true);

        const tokenData = await ensureSpeechToken(true);
        const iceTokenData = await ensureSpeechIceToken(true);
        if (!tokenData || !iceTokenData) {
            setTokenError('Failed to get necessary tokens for session.');
            setAvatarConnecting(false);
            return;
        }

        try {
            const { token: authToken, region } = tokenData;

            // Handle iceServers array format from fetchSpeechIceToken
            const iceServer = iceTokenData.iceServers[0];
            const { urls, username, credential } = iceServer || {};
            // console.log('Starting session with:', { iceTokenData, iceServer, authToken, region, urls, username, credential });

            if (!Array.isArray(urls) || urls.length === 0) {
                setTokenError('ICE token missing valid URLs.');
                setAvatarConnecting(false);
                return;
            }

            const pipeline = await buildAvatarPipeline({
                token: authToken,
                region,
                iceServer: {
                    urls: urls,
                    username: username,
                    credential: credential
                },
                voiceName: avatarMeta.voice,
                character: avatarMeta.character,
                style: avatarMeta.style,
                onTrack: (event) => {
                    if (event.track.kind === 'video' && videoRef.current) {
                        videoRef.current.srcObject = event.streams[0];
                        videoRef.current.play().catch(() => { });
                        setAvatarStreamReady(true);
                    }
                    if (event.track.kind === 'audio' && audioRef.current) {
                        audioRef.current.srcObject = event.streams[0];
                        audioRef.current.play().catch(() => { });
                    }
                },
                onConnectionState: (state) => {
                    if (state === 'failed' || state === 'disconnected') stopSession();
                }
            });

            pipelineRef.current = pipeline;
            synthesizerRef.current = pipeline.avatarSynthesizer;
            peerConnectionRef.current = pipeline.peerConnection;
            recognizerRef.current = pipeline.recognizer || recognizerRef.current;
            if (pipeline.recognizer) {
                console.log('[VoiceControl] Reusing recognizer from avatar pipeline.');
            }
            if (!recognizerRef.current) {
                console.log('[VoiceControl] No recognizer in pipeline. Creating new SpeechRecognizer...');
                recognizerRef.current = initSpeechRecognizer({
                    token: authToken,
                    region,
                    language: selectedLanguage
                });
                if (recognizerRef.current) {
                    console.log('[VoiceControl] Created new recognizer instance.');
                } else {
                    console.warn('[VoiceControl] Failed to create recognizer instance.');
                }
            }

            if (synthesizerRef.current) {
                synthesizerRef.current.wordBoundary = (_s, e) => {
                    if (showSubtitles) setSubtitleText(e.text);
                };
                synthesizerRef.current.synthesisCompleted = () => setSubtitleText('');
            }

            if (recognizerRef.current) {
                recognizerRef.current.recognizing = (_s, e) => {
                    // Skip updating transcript on intermediate results to reduce clutter
                };
                recognizerRef.current.recognized = (_s, e) => {
                    const recognizedText = e.result.text;
                    console.log('[VoiceControl] Recognized text:', recognizedText);
                    if (recognizedText) {
                        setTranscript(prev => [...prev, `RECOGNIZED${continuousListening ? ' (cont)' : ''}: ${recognizedText}`]);
                        // Send to AI
                        sendToAI(recognizedText);
                    }
                    if (!continuousListening) setIsRecognizing(false);

                    // Debug: Auto TTS echo - Debugging to test connection to avatar TTS
                    // if (recognizedText && recognizedText.trim()) {
                    //     setMessage(recognizedText);
                    //     setTimeout(() => {
                    //         if (synthesizerRef.current) {
                    //             speakAvatarText(synthesizerRef.current, recognizedText, {
                    //                 onStart: () => setTranscript(p => [...p, `SPEAKING: ${recognizedText}`])
                    //             });
                    //         }
                    //     }, 100);
                    // }
                };
                recognizerRef.current.canceled = (_s, e) => {
                    //setTranscript(prev => [...prev, `CANCELED: Reason=${e.reason}`]);
                    if (!continuousListening) setIsRecognizing(false);
                };
            } else {
                console.warn('[VoiceControl] Recognizer not available; voice input disabled.');
            }

            // Auto-start continuous recognition
            if (recognizerRef.current && !continuousListening) {
                console.log('[VoiceControl] Starting continuous recognition...');
                recognizerRef.current.startContinuousRecognitionAsync(
                    () => {
                        console.log('[VoiceControl] Continuous recognition started.');
                        setContinuousListening(true);
                        setIsRecognizing(true);
                    },
                    err => {
                        console.error('[VoiceControl] Continuous recognition start failed:', err);
                        setTranscript(p => [...p, `CONTINUOUS RECOGNITION ERROR: ${err}`]);
                    }
                );
            } else if (!recognizerRef.current) {
                console.warn('[VoiceControl] Cannot start continuous recognition (no recognizer).');
            }

            setSessionActive(true);
        } catch (err) {
            console.error('[VoiceControl] Start session failed', err);
            setTokenError(err?.message || 'Avatar failed to start.');
            stopSession();
        } finally {
            setAvatarConnecting(false);
        }
    }, [sessionActive, avatarConnecting, ensureSpeechToken, ensureSpeechIceToken, stopSession, showSubtitles, avatarMeta, continuousListening, selectedLanguage, sendToAI]);

    const handleSpeak = useCallback(async () => {
        if (!sessionActive && !avatarConnecting) {
            await startSession();
        }
        // Defer until synthesizer exists
        const trySpeak = () => {
            if (synthesizerRef.current) {
                speakAvatarText(synthesizerRef.current, message, {
                    onStart: () => setTranscript(p => [...p, `SPEAKING: ${message}`])
                });
            } else {
                setTimeout(trySpeak, 50);
            }
        };
        trySpeak();
    }, [sessionActive, avatarConnecting, startSession, message]);

    const doRecognizeOnce = useCallback(() => {
        if (continuousListening) return; // Ignore in continuous mode
        if (!recognizerRef.current) {
            alert('Session not started or recognizer not ready.');
            return;
        }
        setIsRecognizing(true);
        setMessage(''); // Clear message field before starting recognition
        setTranscript(prev => [...prev, 'RECOGNIZING...']);
        recognizerRef.current.recognizeOnceAsync(
            () => { },
            err => {
                setTranscript(prev => [...prev, `ERROR: ${err}`]);
                setIsRecognizing(false);
            }
        );
    }, [continuousListening]);

    const toggleContinuousRecognition = useCallback(() => { /* logic removed */ }, []);
    const unmuteAvatar = useCallback(() => setAvatarMuted(false), []);

    // Update avatar voice when language changes
    useEffect(() => {
        const langOption = LANGUAGE_OPTIONS.find(lang => lang.code === selectedLanguage);
        if (langOption) {
            setAvatarMeta(prev => ({ ...prev, voice: langOption.voice }));
        }
    }, [selectedLanguage]);

    const toggleAvatarEnabled = useCallback(() => {
        setAvatarEnabled(prev => {
            const next = !prev;
            const vStream = videoRef.current?.srcObject;
            if (vStream) {
                vStream.getVideoTracks().forEach(t => (t.enabled = next));
            }
            const aStream = audioRef.current?.srcObject;
            if (aStream) {
                aStream.getAudioTracks().forEach(t => (t.enabled = next));
            }
            return next;
        });
    }, []);

    const sessionStatusBadge = (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            sessionActive 
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
        }`}>
            {sessionActive ? 'Session Active' : 'Inactive'}
        </span>
    );

    // Periodic speech token refresh (token valid ~10 min; refresh at 8 min)
    useEffect(() => {
        if (!sessionActive) return;
        const REFRESH_THRESHOLD_MS = 8 * 60 * 1000;
        const CHECK_INTERVAL_MS = 60 * 1000;
        const id = setInterval(async () => {
            try {
                if (Date.now() - tokenFetchedAtRef.current > REFRESH_THRESHOLD_MS) {
                    const data = await ensureSpeechToken(true);
                    if (data?.token) {
                        if (synthesizerRef.current) {
                            synthesizerRef.current.authorizationToken = data.token;
                        }
                        if (recognizerRef.current) {
                            recognizerRef.current.authorizationToken = data.token;
                        }
                        console.log('[VoiceControl] Refreshed speech token (age exceeded threshold).');
                    }
                }
            } catch (err) {
                console.warn('[VoiceControl] Token refresh failed:', err);
            }
        }, CHECK_INTERVAL_MS);
        return () => clearInterval(id);
    }, [sessionActive, ensureSpeechToken]);

    return (
        <div className="rounded-lg border bg-card p-5 shadow-sm h-[calc(85vh)]">
            <div className="flex flex-col gap-2.5 h-full">
                <div className="flex items-center justify-between">
                    <h1 className="text-xl font-semibold mb-3">
                        Vehicle Assistant — Voice & Avatar {vehicleId && <span className="text-sm text-muted-foreground"> (Vehicle {vehicleId})</span>}
                    </h1>
                    <div className="flex items-center gap-1.5">
                        {sessionStatusBadge}
                        <button
                            className="px-1.5 py-0.5 text-sm rounded-md bg-secondary hover:bg-secondary/80"
                            onClick={() => {
                                stopSession();
                                setTranscript([]);
                            }}
                            title="Reset all (stop session and clear transcript)"
                        >
                            <RotateCcw className="h-3.5 w-3.5" />
                        </button>
                        {sessionActive && (
                            <button 
                                className="px-1.5 py-0.5 text-sm rounded-md bg-red-100 text-red-600 hover:bg-red-200" 
                                onClick={stopSession}
                                title="Close session"
                            >
                                <X className="h-3.5 w-3.5" />
                            </button>
                        )}
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 flex-1">
                    <div className="flex flex-col gap-1.5">
                        <h2 className="text-base font-bold">Configuration</h2>
                        <div className="flex flex-col gap-1.5">
                            <div>
                                <label className="block text-xs font-medium mb-0.5">Message / Prompt</label>
                                <textarea
                                    rows={8}
                                    value={message}
                                    onChange={e => setMessage(e.target.value)}
                                    className="w-full px-2.5 py-1.5 text-sm border border-input rounded-md bg-background resize-none"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-0.5">Language</label>
                                <div className="relative">
                                    <select 
                                        value={selectedLanguage} 
                                        onChange={e => setSelectedLanguage(e.target.value)} 
                                        disabled={sessionActive}
                                        className="w-full px-2.5 py-1.5 text-sm border border-input rounded-md bg-background appearance-none pr-8 disabled:opacity-50"
                                    >
                                        {LANGUAGE_OPTIONS.map(lang => (
                                            <option key={lang.code} value={lang.code}>
                                                {lang.label}
                                            </option>
                                        ))}
                                    </select>
                                    <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 pointer-events-none" />
                                </div>
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                                {!sessionActive && (
                                    <button 
                                        className="px-2.5 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                                        onClick={startSession} 
                                        disabled={loadingTokens || sessionActive || avatarConnecting}
                                    >
                                        <Play className="h-3.5 w-3.5" /> Start
                                    </button>
                                )}
                                <button 
                                    className="px-2.5 py-1.5 text-sm rounded-md border border-input bg-background hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                                    onClick={handleSpeak} 
                                    disabled={loadingTokens || avatarConnecting}
                                >
                                    <Volume2 className="h-3.5 w-3.5" /> {sessionActive ? 'Send' : 'Start & Send'}
                                </button>
                                <button 
                                    className="px-2.5 py-1.5 text-sm rounded-md border border-input bg-background hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                                    onClick={doRecognizeOnce} 
                                    disabled={!sessionActive || isRecognizing || continuousListening}
                                >
                                    🎤 Recognize Once
                                </button>
                                <button 
                                    className="px-2.5 py-1.5 text-sm rounded-md border border-input bg-background hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                                    onClick={toggleContinuousRecognition} 
                                    disabled
                                >
                                    <Zap className="h-3.5 w-3.5" /> Continuous Recognition
                                </button>
                                <button 
                                    className="px-2.5 py-1.5 text-sm rounded-md border border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                                    onClick={stopSession} 
                                    disabled={!sessionActive && !avatarConnecting}
                                >
                                    <Square className="h-3.5 w-3.5" /> Stop
                                </button>
                                <button 
                                    className={`px-2.5 py-1.5 text-sm rounded-md border inline-flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed ${
                                        avatarEnabled 
                                            ? 'border-blue-500 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950' 
                                            : 'border-orange-500 text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-950'
                                    }`}
                                    onClick={toggleAvatarEnabled} 
                                    disabled={!sessionActive || avatarConnecting || !avatarStreamReady}
                                >
                                    {avatarEnabled ? 'Avatar Active' : 'Avatar Inactive'}
                                </button>
                            </div>
                        </div>

                        <div className="h-px bg-border my-4" />
                        <div>
                            <h3 className="text-lg font-bold mb-2">Toggles</h3>
                            <div className="flex items-center gap-2 mb-2">
                                <button
                                    onClick={() => setShowSubtitles(!showSubtitles)}
                                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                                        showSubtitles ? 'bg-primary' : 'bg-muted-foreground'
                                    }`}
                                >
                                    <span
                                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                            showSubtitles ? 'translate-x-6' : 'translate-x-1'
                                        }`}
                                    />
                                </button>
                                <span className="text-sm">💬 Subtitles</span>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Tokens auto-refresh every 8 mins. Region: {region || (loadingTokens ? 'Loading...' : '—')}
                                {tokenError && ' | ' + tokenError}
                            </p>
                        </div>
                    </div>

                    <div className="flex flex-col flex-1">
                        <h2 className="text-base font-bold mb-1.5">Avatar / Playback (Real-time)</h2>
                        <div className="relative w-full flex-1 bg-muted rounded-lg overflow-hidden" style={{ minHeight: '450px' }}>
                            <video
                                ref={videoRef}
                                className="w-full h-full object-contain"
                                style={{ display: avatarStreamReady && avatarEnabled ? 'block' : 'none' }}
                                muted
                            />
                            <audio ref={audioRef} className="hidden" />

                            {avatarStreamReady && avatarMuted && (
                                <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                                    <button className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90" onClick={unmuteAvatar}>Unmute</button>
                                </div>
                            )}

                            {!avatarStreamReady && !avatarConnecting && (
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <p className="text-sm text-muted-foreground text-center px-4">
                                        {avatarConnecting ? 'Connecting to avatar...' : 'Session inactive. Click "Start" to begin.'}
                                    </p>
                                </div>
                            )}

                            {avatarStreamReady && <div className="absolute bottom-0 left-0 right-0 h-1 bg-primary/30" />}

                            {subtitleText && (
                                <div className="absolute bottom-4 left-0 right-0 flex justify-center px-4">
                                    <div className="bg-black/75 text-white px-4 py-2 rounded-md">
                                        <p className="text-sm">{subtitleText}</p>
                                    </div>
                                </div>
                            )}

                            {!avatarEnabled && avatarStreamReady && (
                                <div className="absolute inset-0 flex items-center justify-center bg-black/75">
                                    <p className="text-xs text-white text-center px-4">
                                        Avatar inactive (video/audio tracks paused). Use the button to reactivate.
                                    </p>
                                </div>
                            )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                            Avatar Character: {avatarMeta.character} | Style: {avatarMeta.style} | Voice: {avatarMeta.voice} | {sessionActive ? (avatarEnabled ? 'Active' : 'Paused') : 'Idle'} | STT: {continuousListening ? 'Continuous' : 'Idle'}
                        </p>
                    </div>

                    <div className="flex flex-col flex-1">
                        <h2 className="text-base font-bold mb-1.5">Transcription</h2>
                        <div className="p-3 border border-input rounded-md bg-muted/50 flex-1 overflow-y-auto font-mono text-[10px]" style={{ minHeight: '450px' }}>
                            {transcript.length === 0 ? (
                                <p className="text-muted-foreground">(Inactive) Transcript will appear here.</p>
                            ) : transcript.map((line, index) => (
                                <div key={index} className="mb-1">{line}</div>
                            ))}
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                            Last recognized: {
                                (() => {
                                    const last = [...transcript].reverse().find(t => t.startsWith('RECOGNIZED'));
                                    return last ? last.split(':').slice(1).join(':').trim() : '—';
                                })()
                            }
                        </p>
                        <div className="h-px bg-border my-4" />
                    </div>

                </div>

                <div className="h-px bg-border" />
                <p className="text-xs text-muted-foreground">
                    Azure Speech with Avatar demo. Implements session management, STT (recognize once), and TTS with avatar video.
                </p>
            </div>
        </div>
    );
};

export default VehicleAssistant;