import { useEffect, useState, useCallback, useRef } from 'react';
import {
    Box, Paper, Typography, Grid, Button, TextField, Switch,
    FormControlLabel, Divider, Chip, LinearProgress, IconButton, Tooltip
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

const QUICK_REPLIES = [
    'Let me check that.',
    'One moment please.',
    'Analyzing your request.',
    'Working on it now.'
];

const VoiceControl = ({ vehicleId }) => {
    // --- Token issuing only ---
    const speechTokenRef = useRef(null);
    const speechIceTokenRef = useRef(null);
    const tokenFetchedAtRef = useRef(0);

    const [region, setRegion] = useState('');
    const [tokenError, setTokenError] = useState(null);
    const [loadingTokens, setLoadingTokens] = useState(false);

    // --- Minimal placeholder UI states kept for layout ---
    const [sessionActive] = useState(false);
    const [avatarConnecting] = useState(false);
    const [avatarStreamReady] = useState(false);
    const [avatarMuted, setAvatarMuted] = useState(true);
    const [message, setMessage] = useState('Hello! I am your in-vehicle assistant.');
    const [showSubtitles, setShowSubtitles] = useState(true);
    const [transcript, setTranscript] = useState([]);
    const [subtitleText] = useState('');

    // --- Token helpers (retained) ---
    const ensureSpeechToken = useCallback(async (force = false) => {
        const now = Date.now();
        if (!force && speechTokenRef.current && tokenFetchedAtRef.current && (now - tokenFetchedAtRef.current) < 8 * 60 * 1000) {
            return speechTokenRef.current;
        }
        try {
            setLoadingTokens(true);
            const data = await fetchSpeechToken();
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

    // Initial token fetch
    useEffect(() => {
        ensureSpeechToken();
        ensureSpeechIceToken();
    }, [ensureSpeechToken, ensureSpeechIceToken]);

    // --- No-op / stub handlers (logic removed) ---
    const startSession = useCallback(() => { ensureSpeechToken(true); }, [ensureSpeechToken]);
    const stopSession = useCallback(() => { /* logic removed */ }, []);
    const handleSpeak = useCallback(() => { ensureSpeechToken(true); }, [ensureSpeechToken]);
    const doRecognizeOnce = useCallback(() => { /* logic removed */ }, []);
    const toggleContinuousRecognition = useCallback(() => { /* logic removed */ }, []);
    const unmuteAvatar = useCallback(() => setAvatarMuted(false), []);
    const requestAI = useCallback(() => { /* logic removed */ }, []);

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
                        Voice & Avatar Control {vehicleId && <Typography component="span" variant="subtitle2" color="text.secondary"> (Vehicle {vehicleId})</Typography>}
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
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                                {!sessionActive && (
                                    <Button
                                        variant="contained"
                                        startIcon={<PlayArrowIcon />}
                                        onClick={startSession}
                                        disabled={loadingTokens}
                                    >
                                        Start
                                    </Button>
                                )}
                                <Button
                                    variant="outlined"
                                    startIcon={<RecordVoiceOverIcon />}
                                    onClick={handleSpeak}
                                    disabled={loadingTokens}
                                >
                                    {sessionActive ? 'Send' : 'Start & Send'}
                                </Button>
                                <Button
                                    variant="outlined"
                                    startIcon={<HearingIcon />}
                                    onClick={doRecognizeOnce}
                                    disabled
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
                                    disabled
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
                            Tokens auto-refresh disabled (manual fetch only). Region: {region || (loadingTokens ? 'Loading...' : '—')}
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
                        <audio style={{ display: 'none' }} />

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
                                    Avatar logic removed. Token fetch only.
                                </Typography>
                            </Box>
                        )}
                        {avatarConnecting && (
                            <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 3 }}>
                                <LinearProgress />
                            </Box>
                        )}
                        {showSubtitles && subtitleText && (
                            <Box
                                sx={{
                                    position: 'absolute',
                                    bottom: 8,
                                    left: 0,
                                    right: 0,
                                    textAlign: 'center',
                                    px: 2,
                                    zIndex: 4
                                }}
                            >
                                <Paper
                                    elevation={3}
                                    sx={{
                                        display: 'inline-block',
                                        px: 1.5,
                                        py: 0.5,
                                        bgcolor: 'rgba(0,0,0,0.55)',
                                        backdropFilter: 'blur(4px)'
                                    }}
                                >
                                    <Typography variant="caption" sx={{ color: '#fff' }}>
                                        {subtitleText}
                                    </Typography>
                                </Paper>
                            </Box>
                        )}
                    </Box>
                    <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                            Avatar Character: meg | Style: formal | Voice: en-US-AvaMultilingualNeural | Idle
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
                            lineHeight: 1.4
                        }}
                    >
                        {transcript.length === 0 ? (
                            <Typography variant="caption" color="text.secondary">
                                (Inactive) No transcriptions – logic removed.
                            </Typography>
                        ) : null}
                    </Paper>
                    <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                            Last recognized: —
                        </Typography>
                    </Box>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="subtitle2" gutterBottom>Quick Replies</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {QUICK_REPLIES.map(q => (
                            <Chip
                                key={q}
                                label={q}
                                size="small"
                                onClick={() => requestAI(q)}
                                disabled
                                variant="outlined"
                            />
                        ))}
                    </Box>
                </Grid>

                <Grid item xs={12}>
                    <Divider sx={{ mb: 2 }} />
                    <Typography variant="caption" color="text.secondary">
                        Azure Speech token issuing demo (fetch speech + ICE tokens only). All other functionality removed.
                    </Typography>
                </Grid>
            </Grid>
        </Paper>
    );
};

export default VoiceControl;