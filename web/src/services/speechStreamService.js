import * as SpeechSDK from "microsoft-cognitiveservices-speech-sdk";

const avatarAppConfig = {
    voiceName: "en-US-AvaMultilingualNeural",
    avatarCharacter: "meg", //lisa, meg
    avatarStyle: "casual-sitting", // casual-sitting, formal
    avatarBackgroundColor: "#FFFFFFFF"

}

export const speechSDKConfig = {
    autoDetectionLanguageCode: ["en-US", "ko-KR", "ja-JP"]
}

export const createWebRTCConnection = (iceConfig) => {
    let iceServers =
        (iceConfig && Array.isArray(iceConfig.iceServers) && iceConfig.iceServers.length > 0 && iceConfig.iceServers) ||
        (Array.isArray(iceConfig) && iceConfig) ||
        [{
            urls: iceConfig.iceUrl,
            username: iceConfig.iceUsername,
            credential: iceConfig.iceCredential
        }];

    var peerConnection = new RTCPeerConnection({
        iceServers: iceServers
    })

    return peerConnection;
}

export const createAvatarSynthesizer = (token, region, {
    voiceName = avatarAppConfig.voiceName,
    character = avatarAppConfig.avatarCharacter,
    style = avatarAppConfig.avatarStyle,
    backgroundColor = avatarAppConfig.avatarBackgroundColor,
    crop = { topLeft: { x: 600, y: 50 }, bottomRight: { x: 1320, y: 1080 } }
} = {}) => {
    // Option 1. API Key based authentication
    // const speechSynthesisConfig = SpeechSDK.SpeechConfig.fromSubscription(token, region)
    // Option 2. Temporary token-based authentication — short-lived (10 minutes) (recommended)
    const speechSynthesisConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region)
    speechSynthesisConfig.speechSynthesisVoiceName = voiceName;

    const videoFormat = new SpeechSDK.AvatarVideoFormat()
    if (crop) {
        videoFormat.setCropRange(
            new SpeechSDK.Coordinate(crop.topLeft.x, crop.topLeft.y),
            new SpeechSDK.Coordinate(crop.bottomRight.x, crop.bottomRight.y)
        );
    }

    const avatarConfig = new SpeechSDK.AvatarConfig(character, style, videoFormat)
    avatarConfig.backgroundColor = backgroundColor;
    let avatarSynthesizer = new SpeechSDK.AvatarSynthesizer(speechSynthesisConfig, avatarConfig)

    avatarSynthesizer.avatarEventReceived = function (s, e) {
        var offsetMessage = ", offset from session start: " + e.offset / 10000 + "ms."
        if (e.offset === 0) offsetMessage = ""
        console.log("[" + (new Date()).toISOString() + "] Event received: " + e.description + offsetMessage)
    }

    return avatarSynthesizer;
}

// Speech recognizer initializer
export const initSpeechRecognizer = ({
    token, region, language, onRecognizing, onRecognized, onCanceled, onSessionStarted, onSessionStopped
}) => {
    const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region);
    speechConfig.speechRecognitionLanguage = language;
    const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
    const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

    recognizer.recognizing = (_s, e) => {
        onRecognizing && onRecognizing(e?.result?.text || '');
    };
    recognizer.recognized = (_s, e) => {
        if (e.result?.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
            onRecognized && onRecognized(e.result.text);
        }
    };
    recognizer.canceled = (_s, e) => {
        onCanceled && onCanceled(e);
    };
    recognizer.sessionStarted = () => {
        onSessionStarted && onSessionStarted();
    };
    recognizer.sessionStopped = () => {
        onSessionStopped && onSessionStopped();
    };

    return recognizer;
};

// Auto language detection (universal) recognizer (reference: chat.js)
export const initAutoDetectRecognizer = ({
    token,
    region,
    languages = speechSDKConfig.autoDetectionLanguageCode,
    onRecognizing,
    onRecognized,
    onCanceled,
    onSessionStarted,
    onSessionStopped
}) => {
    const speechConfig = SpeechSDK.SpeechConfig.fromEndpoint(
        new URL(`wss://${region}.stt.speech.microsoft.com/speech/universal/v2`),
    );
    speechConfig.authorizationToken = token; // Same as fromAuthorizationToken
    speechConfig.setProperty(
        SpeechSDK.PropertyId.SpeechServiceConnection_LanguageIdMode,
        "Continuous"
    );
    const autoDetectCfg = SpeechSDK.AutoDetectSourceLanguageConfig.fromLanguages(languages);
    const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
    const recognizer = SpeechSDK.SpeechRecognizer.FromConfig(
        speechConfig,
        autoDetectCfg,
        audioConfig
    );

    recognizer.recognizing = (_s, e) => onRecognizing && onRecognizing(e?.result?.text || "");
    recognizer.recognized = (_s, e) => {
        if (e.result?.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
            onRecognized && onRecognized(e.result.text);
        }
    };
    recognizer.canceled = (_s, e) => onCanceled && onCanceled(e);
    recognizer.sessionStarted = () => onSessionStarted && onSessionStarted();
    recognizer.sessionStopped = () => onSessionStopped && onSessionStopped();

    return recognizer;
};

// Speaking queue utilities (reference: chat.js)
let _isSpeaking = false;
let _speakQueue = [];
let _currentSpeakingText = "";
let _lastSpeakTime;

/**
 * Internal speak helper (SSML already prepared)
 */
const _speakSsmlInternal = (avatarSynthesizer, ssml, {
    onStart,
    onDone,
    onError
} = {}) => {
    _isSpeaking = true;
    onStart && onStart(ssml);
    avatarSynthesizer.speakSsmlAsync(ssml).then(result => {
        if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
            _lastSpeakTime = new Date();
        }
        _isSpeaking = false;
        _currentSpeakingText = "";
        onDone && onDone(result);
        if (_speakQueue.length > 0) {
            const next = _speakQueue.shift();
            _doSpeak(avatarSynthesizer, next.text, next.options);
        }
    }).catch(err => {
        _isSpeaking = false;
        _currentSpeakingText = "";
        onError && onError(err);
        if (_speakQueue.length > 0) {
            const next = _speakQueue.shift();
            _doSpeak(avatarSynthesizer, next.text, next.options);
        }
    });
};

const buildPlainTextSsml = (voice, text, endingSilenceMs = 0) => {
    const silenceTag = endingSilenceMs > 0 ? `<break time='${endingSilenceMs}ms' />` : "";
    return `<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'><voice name='${voice}'><mstts:leadingsilence-exact value='0'/>${escapeXml(text)}${silenceTag}</voice></speak>`;
};

const escapeXml = (s) => s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");

const _doSpeak = (avatarSynthesizer, text, {
    voice,
    endingSilenceMs,
    onStart,
    onDone,
    onError
} = {}) => {
    _currentSpeakingText = text;
    const effectiveVoice = voice || avatarSynthesizer?.properties?.getProperty?.(SpeechSDK.PropertyId.SpeechServiceConnection_SynthVoice) || avatarAppConfig.voiceName;
    const ssml = buildPlainTextSsml(effectiveVoice, text, endingSilenceMs);
    _speakSsmlInternal(avatarSynthesizer, ssml, { onStart, onDone, onError });
};

export const speakText = (avatarSynthesizer, text, options = {}) => {
    if (!avatarSynthesizer || !text) return;
    if (_isSpeaking) {
        _speakQueue.push({ text, options });
        return;
    }
    _doSpeak(avatarSynthesizer, text, options);
};

export const speakSsml = (avatarSynthesizer, ssml, callbacks = {}) => {
    if (!avatarSynthesizer || !ssml) return;
    if (_isSpeaking) {
        _speakQueue.push({
            text: ssml,
            options: { isRawSsml: true, ...callbacks }
        });
        return;
    }
    _speakSsmlInternal(avatarSynthesizer, ssml, callbacks);
};

export const stopSpeaking = (avatarSynthesizer) => {
    _speakQueue = [];
    if (!avatarSynthesizer) return;
    return avatarSynthesizer.stopSpeakingAsync().finally(() => {
        _isSpeaking = false;
        _currentSpeakingText = "";
    });
};

export const speakingState = () => ({
    isSpeaking: _isSpeaking,
    queueLength: _speakQueue.length,
    currentText: _currentSpeakingText,
    lastSpeakTime: _lastSpeakTime
});

// Avatar + WebRTC session helper (condensed from chat.js logic)
export const startAvatarSession = async ({
    avatarSynthesizer,
    iceServer,
    onTrack,
    onConnectionState,
    addDataChannel = false,
    transceivers = { video: 'recvonly', audio: 'recvonly' }
}) => {
    if (!avatarSynthesizer) throw new Error("avatarSynthesizer required");
    
    // Extract URLs from iceServer object
    let urls = [];
    if (Array.isArray(iceServer?.urls)) {
        urls = iceServer.urls;
    } else if (iceServer?.url) {
        urls = [iceServer.url];
    }
    
    if (urls.length === 0) {
        throw new Error("iceServer url(s) required");
    }

    // console.log('Creating RTCPeerConnection with ICE config:', {
    //     urls,
    //     username: iceServer.username,
    //     credential: iceServer.credential
    // });

    const pc = new RTCPeerConnection({
        iceServers: [{
            urls: urls,
            username: iceServer.username,
            credential: iceServer.credential
        }]
    });

    pc.ontrack = (e) => onTrack && onTrack(e);
    pc.oniceconnectionstatechange = () => onConnectionState && onConnectionState(pc.iceConnectionState);

    pc.addTransceiver('video', { direction: transceivers.video });
    pc.addTransceiver('audio', { direction: transceivers.audio });

    if (addDataChannel) pc.createDataChannel("eventChannel");

    const result = await avatarSynthesizer.startAvatarAsync(pc);
    if (result.reason !== SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
        try { pc.close(); } catch {}
        throw new Error("Avatar failed to start.");
    }
    return { peerConnection: pc, result };
};

export const stopAvatarSession = ({ peerConnection, avatarSynthesizer, recognizer } = {}) => {
    try { recognizer && recognizer.close && recognizer.close(); } catch {}
    try { avatarSynthesizer && avatarSynthesizer.close && avatarSynthesizer.close(); } catch {}
    try { peerConnection && peerConnection.close && peerConnection.close(); } catch {}
};

// Convenience: dispose all (alias)
export const disposeAvatarResources = stopAvatarSession;

// Lightweight convenience bundle
export const buildAvatarPipeline = async ({
    token,
    region,
    iceServer,
    voiceName,
    character,
    style,
    crop,
    languages,
    onTrack,
    onConnectionState
}) => {
    const avatarSynthesizer = createAvatarSynthesizer(token, region, { voiceName, character, style, crop });
    const { peerConnection } = await startAvatarSession({
        avatarSynthesizer,
        iceServer,
        onTrack,
        onConnectionState
    });

    const recognizer = languages
        ? initAutoDetectRecognizer({ token, region, languages })
        : null;

    return {
        avatarSynthesizer,
        peerConnection,
        recognizer,
        speakText: (t, o) => speakText(avatarSynthesizer, t, o),
        stop: () => stopAvatarSession({ peerConnection, avatarSynthesizer, recognizer })
    };
};