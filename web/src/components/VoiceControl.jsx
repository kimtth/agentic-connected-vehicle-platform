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
    buildAvatarPipeline
} from '../services/speechStreamService';

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

    const videoRef = useRef(null);
    const audioRef = useRef(null);

    // --- Load Speech SDK (now only for cleanup) ---
    useEffect(() => {
        return () => {
            try { pipelineRef.current?.stop(); } catch {}
            pipelineRef.current = null;
            peerConnectionRef.current = null;
            synthesizerRef.current = null;
            recognizerRef.current = null;
        };
    }, []);

    // --- Token helpers (simplified) ---
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
        try { pipelineRef.current?.stop(); } catch {}
        pipelineRef.current = null;
        peerConnectionRef.current = null;
        synthesizerRef.current = null;
        recognizerRef.current = null;
        setSessionActive(false);
        setAvatarConnecting(false);
        setAvatarStreamReady(false);
        setSubtitleText('');
    }, []);

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
                        videoRef.current.play().catch(()=>{});
                        setAvatarStreamReady(true);
                    }
                    if (event.track.kind === 'audio' && audioRef.current) {
                        audioRef.current.srcObject = event.streams[0];
                        audioRef.current.play().catch(()=>{});
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

            if (synthesizerRef.current) {
                synthesizerRef.current.wordBoundary = (_s, e) => {
                    if (showSubtitles) setSubtitleText(e.text);
                };
                synthesizerRef.current.synthesisCompleted = () => setSubtitleText('');
            }

            if (recognizerRef.current) {
                recognizerRef.current.recognizing = (_s, e) => {
                    setTranscript(prev => {
                        const copy = [...prev];
                        if (copy.length && copy[copy.length - 1].startsWith('RECOGNIZING:')) {
                            copy[copy.length - 1] = `RECOGNIZING: ${e.result?.text || ''}`;
                        } else {
                            copy.push(`RECOGNIZING: ${e.result?.text || ''}`);
                        }
                        return copy;
                    });
                };
                recognizerRef.current.recognized = (_s, e) => {
                    const recognizedText = e.result.text;
                    setTranscript(prev => [...prev, `RECOGNIZED: ${recognizedText}`]);
                    setIsRecognizing(false);
                    
                    // Set recognized text to message field and auto-send
                    if (recognizedText && recognizedText.trim()) {
                        setMessage(recognizedText);
                        // Auto-send after a brief delay to allow UI update
                        setTimeout(() => {
                            if (synthesizerRef.current) {
                                speakAvatarText(synthesizerRef.current, recognizedText, {
                                    onStart: () => setTranscript(p => [...p, `SPEAKING: ${recognizedText}`])
                                });
                            }
                        }, 100);
                    }
                };
                recognizerRef.current.canceled = (_s, e) => {
                    setTranscript(prev => [...prev, `CANCELED: Reason=${e.reason}`]);
                    setIsRecognizing(false);
                };
            }

            setSessionActive(true);
        } catch (err) {
            console.error('[VoiceControl] Start session failed', err);
            setTokenError(err?.message || 'Avatar failed to start.');
            stopSession();
        } finally {
            setAvatarConnecting(false);
        }
    }, [sessionActive, avatarConnecting, ensureSpeechToken, ensureSpeechIceToken, stopSession, showSubtitles, avatarMeta]);

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
        if (!recognizerRef.current) {
            alert('Session not started or recognizer not ready.');
            return;
        }
        setIsRecognizing(true);
        setMessage(''); // Clear message field before starting recognition
        setTranscript(prev => [...prev, 'RECOGNIZING...']);
        recognizerRef.current.recognizeOnceAsync(
            () => {},
            err => {
                setTranscript(prev => [...prev, `ERROR: ${err}`]);
                setIsRecognizing(false);
            }
        );
    }, []);

    const toggleContinuousRecognition = useCallback(() => { /* logic removed */ }, []);
    const unmuteAvatar = useCallback(() => setAvatarMuted(false), []);

    // Update avatar voice when language changes
    useEffect(() => {
        const langOption = LANGUAGE_OPTIONS.find(lang => lang.code === selectedLanguage);
        if (langOption) {
            setAvatarMeta(prev => ({ ...prev, voice: langOption.voice }));
        }
    }, [selectedLanguage]);

    const sessionStatusChip = (
        <Chip
            size="small"
            label={sessionActive ? 'Session Active' : 'Inactive'}
            color={sessionActive ? 'success' : 'default'}
            variant={sessionActive ? 'filled' : 'outlined'}
        />
    );

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
                                    disabled={!sessionActive || isRecognizing}
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
                                display: avatarStreamReady ? 'block' : 'none',
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
                    </Box>
                    <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                            Avatar Character: {avatarMeta.character} | Style: {avatarMeta.style} | Voice: {avatarMeta.voice} | {sessionActive ? 'Active' : 'Idle'}
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
                            Last recognized: {transcript.findLast(t => t.startsWith('RECOGNIZED:'))?.substring(11) || '—'}
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