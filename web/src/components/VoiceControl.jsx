import { useEffect, useState, useCallback, useRef } from 'react';
import {
    Box, Paper, Typography, Grid, Button, TextField, Switch,
    FormControlLabel, Divider, Chip, LinearProgress, IconButton, Tooltip,
    Select, MenuItem, FormControl, InputLabel
} from '@mui/material';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import HearingIcon from '@mui/icons-material/Hearing';
import SubtitlesIcon from '@mui/icons-material/Subtitles';
import BoltIcon from '@mui/icons-material/Bolt';
import CloseIcon from '@mui/icons-material/Close';
import { fetchSpeechToken, fetchSpeechIceToken } from '../api/services';
import {
    speakText as speakAvatarText,
    buildAvatarPipeline,
    initSpeechRecognizer
} from '../services/speechStreamService';
import { askAI } from '../api/services'; // ADDED

const LANGUAGE_OPTIONS = [
    { code: 'en-US', label: 'English', voice: 'en-US-AvaMultilingualNeural' },
    { code: 'ko-KR', label: 'Korean', voice: 'en-US-AvaMultilingualNeural' },
    { code: 'ja-JP', label: 'Japanese', voice: 'en-US-AvaMultilingualNeural' }
];

const VoiceControl = ({ vehicleId }) => {
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

    const sessionStatusChip = (
        <Chip
            size="small"
            label={sessionActive ? 'Session Active' : 'Inactive'}
            color={sessionActive ? 'success' : 'default'}
            variant={sessionActive ? 'filled' : 'outlined'}
        />
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
        <Paper sx={{ p: 3 }}>
            <Grid container spacing={3}>
                <Grid item xs={12} display="flex" alignItems="center" justifyContent="space-between">
                    <Typography variant="h6">
                        In-Vehicle Assistant — Voice & Avatar {vehicleId && <Typography component="span" variant="subtitle2" color="text.secondary"> (Vehicle {vehicleId})</Typography>}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                        {sessionStatusChip}
                        <Tooltip title="Reset all (stop session and clear transcript)">
                            <IconButton
                                size="small"
                                onClick={() => {
                                    stopSession();
                                    setTranscript([]);
                                }}
                            >
                                <RestartAltIcon fontSize="small" />
                            </IconButton>
                        </Tooltip>
                        {sessionActive && (
                            <Tooltip title="Close session">
                                <IconButton size="small" color="error" onClick={stopSession}>
                                    <CloseIcon fontSize="small" />
                                </IconButton>
                            </Tooltip>
                        )}
                    </Box>
                </Grid>

                <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" gutterBottom>Configuration</Typography>
                    <Grid container spacing={2}>
                        <Grid item xs={12}>
                            <TextField
                                multiline
                                minRows={8}
                                fullWidth
                                label="Message / Prompt"
                                value={message}
                                onChange={e => setMessage(e.target.value)}
                            />
                        </Grid>
                        <Grid item xs={12}>
                            <FormControl fullWidth size="small">
                                <InputLabel>Language</InputLabel>
                                <Select
                                    value={selectedLanguage}
                                    label="Language"
                                    onChange={e => setSelectedLanguage(e.target.value)}
                                    disabled={sessionActive}
                                >
                                    {LANGUAGE_OPTIONS.map(lang => (
                                        <MenuItem key={lang.code} value={lang.code}>
                                            {lang.label}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12}>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                                {!sessionActive && (
                                    <Button
                                        variant="contained"
                                        startIcon={<PlayArrowIcon />}
                                        onClick={startSession}
                                        disabled={loadingTokens || sessionActive || avatarConnecting}
                                    >
                                        Start
                                    </Button>
                                )}
                                <Button
                                    variant="outlined"
                                    startIcon={<RecordVoiceOverIcon />}
                                    onClick={handleSpeak}
                                    disabled={loadingTokens || avatarConnecting}
                                >
                                    {sessionActive ? 'Send' : 'Start & Send'}
                                </Button>
                                <Button
                                    variant="outlined"
                                    startIcon={<HearingIcon />}
                                    onClick={doRecognizeOnce}
                                    disabled={!sessionActive || isRecognizing || continuousListening} // modified
                                >
                                    Recognize Once
                                </Button>
                                <Button
                                    variant="outlined"
                                    startIcon={<BoltIcon />}
                                    onClick={toggleContinuousRecognition}
                                    disabled
                                >
                                    Continuous Recognition
                                </Button>
                                <Button
                                    variant="outlined"
                                    color="error"
                                    startIcon={<StopIcon />}
                                    onClick={stopSession}
                                    disabled={!sessionActive && !avatarConnecting}
                                >
                                    Stop
                                </Button>
                                <Button
                                    variant="outlined"
                                    color={avatarEnabled ? 'primary' : 'warning'}
                                    onClick={toggleAvatarEnabled}
                                    disabled={!sessionActive || avatarConnecting || !avatarStreamReady}
                                >
                                    {avatarEnabled ? 'Avatar Active' : 'Avatar Inactive'}
                                </Button>
                            </Box>
                        </Grid>
                    </Grid>

                    <Divider sx={{ my: 2 }} />

                    <Typography variant="subtitle2" gutterBottom>Toggles</Typography>
                    <FormControlLabel
                        control={<Switch checked={showSubtitles} onChange={e => setShowSubtitles(e.target.checked)} />}
                        label={<Box sx={{ display: 'flex', alignItems: 'center', gap: .5 }}><SubtitlesIcon fontSize="small" />Subtitles</Box>}
                    />
                    <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                            Tokens auto-refresh every 8 mins. Region: {region || (loadingTokens ? 'Loading...' : '—')}
                            {tokenError && ' | ' + tokenError}
                        </Typography>
                    </Box>
                </Grid>

                <Grid item xs={12} md={4} sx={{ display: 'flex', flexDirection: 'column', height: 600 }}>
                    <Typography variant="subtitle2" gutterBottom>Avatar / Playback (Real-time)</Typography>
                    <Box
                        sx={{
                            position: 'relative',
                            width: '100%',
                            height: '90%',
                            minHeight: 300,
                            borderRadius: 2,
                            overflow: 'hidden',
                            bgcolor: 'background.default',
                            border: theme => `1px solid ${theme.palette.divider}`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        {/* Avatar video/audio placeholders (logic removed) */}
                        <video
                            ref={videoRef}
                            style={{
                                position: 'absolute',
                                inset: 0,
                                width: '100%',
                                height: '100%',
                                objectFit: 'cover',
                                background: '#000',
                                display: avatarStreamReady && avatarEnabled ? 'block' : 'none',
                                zIndex: 1
                            }}
                            muted
                        />
                        <audio ref={audioRef} style={{ display: 'none' }} />

                        {avatarStreamReady && avatarMuted && (
                            <Box sx={{
                                position: 'absolute',
                                top: 8,
                                right: 8,
                                zIndex: 5,
                                backdropFilter: 'blur(4px)',
                                bgcolor: 'rgba(0,0,0,0.45)',
                                p: .5,
                                borderRadius: 1
                            }}>
                                <Button size="small" variant="contained" onClick={unmuteAvatar}>
                                    Unmute
                                </Button>
                            </Box>
                        )}

                        {!avatarStreamReady && !avatarConnecting && (
                            <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', px: 2, textAlign: 'center', zIndex: 2 }}>
                                <Typography variant="body2" color="text.secondary">
                                    {avatarConnecting ? 'Connecting to avatar...' : 'Session inactive. Click "Start" to begin.'}
                                </Typography>
                            </Box>
                        )}

                        {avatarStreamReady && (
                            <Box
                                sx={{
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    zIndex: 3
                                }}
                            >
                                <LinearProgress />
                            </Box>
                        )}

                        {subtitleText && (
                            <Box
                                component={Paper}
                                elevation={3}
                                sx={{
                                    display: 'inline-block',
                                    px: 1.5,
                                    py: 0.5,
                                    bgcolor: 'rgba(0,0,0,0.55)',
                                    backdropFilter: 'blur(4px)',
                                    position: 'absolute',
                                    bottom: 8,
                                    left: 0,
                                    right: 0,
                                    textAlign: 'center',
                                    zIndex: 4
                                }}
                            >
                                <Typography variant="caption" sx={{ color: '#fff' }}>
                                    {subtitleText}
                                </Typography>
                            </Box>
                        )}

                        {!avatarEnabled && avatarStreamReady && (
                            <Box sx={{
                                position: 'absolute',
                                inset: 0,
                                zIndex: 4,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                backdropFilter: 'blur(6px)',
                                bgcolor: 'rgba(0,0,0,0.55)',
                                color: '#fff',
                                px: 2,
                                textAlign: 'center'
                            }}>
                                <Typography variant="caption">
                                    Avatar inactive (video/audio tracks paused). Use the button to reactivate.
                                </Typography>
                            </Box>
                        )}
                    </Box>
                    <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                            Avatar Character: {avatarMeta.character} | Style: {avatarMeta.style} | Voice: {avatarMeta.voice} | {sessionActive ? (avatarEnabled ? 'Active' : 'Paused') : 'Idle'} | STT: {continuousListening ? 'Continuous' : 'Idle'}
                        </Typography>
                    </Box>
                </Grid>

                <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" gutterBottom>Transcription</Typography>
                    <Paper
                        variant="outlined"
                        sx={{
                            p: 1.5,
                            height: 350,
                            overflowY: 'auto',
                            fontFamily: 'monospace',
                            fontSize: '0.75rem',
                            lineHeight: 1.4,
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word'
                        }}
                    >
                        {transcript.length === 0 ? (
                            <Typography variant="caption" color="text.secondary">
                                (Inactive) Transcript will appear here.
                            </Typography>
                        ) : transcript.map((line, index) => (
                            <div key={index}>{line}</div>
                        ))}
                    </Paper>
                    <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                            {/* UPDATED: handle both standard and (cont) prefixes */}
                            Last recognized: {
                                (() => {
                                    const last = [...transcript].reverse().find(t => t.startsWith('RECOGNIZED'));
                                    return last ? last.split(':').slice(1).join(':').trim() : '—';
                                })()
                            }
                        </Typography>
                    </Box>
                    <Divider sx={{ my: 2 }} />
                </Grid>

                <Grid item xs={12}>
                    <Divider sx={{ mb: 2 }} />
                    <Typography variant="caption" color="text.secondary">
                        Azure Speech with Avatar demo. Implements session management, STT (recognize once), and TTS with avatar video.
                    </Typography>
                </Grid>
            </Grid>
        </Paper>
    );
};

export default VoiceControl;