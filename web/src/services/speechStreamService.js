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

export const createAvatarSynthesizer = (token, region) => {
    // Option 1. API Key based authentication
    // const speechSynthesisConfig = SpeechSDK.SpeechConfig.fromSubscription(token, region)
    // Option 2. Temporary token-based authentication — short-lived (10 minutes) (recommended)
    const speechSynthesisConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region)

    speechSynthesisConfig.speechSynthesisVoiceName = avatarAppConfig.voiceName;

    const videoFormat = new SpeechSDK.AvatarVideoFormat()

    let videoCropTopLeftX = 600
    let videoCropBottomRightX = 1320
    videoFormat.setCropRange(new SpeechSDK.Coordinate(videoCropTopLeftX, 50), new SpeechSDK.Coordinate(videoCropBottomRightX, 1080));

    const talkingAvatarCharacter = avatarAppConfig.avatarCharacter
    const talkingAvatarStyle = avatarAppConfig.avatarStyle

    const avatarConfig = new SpeechSDK.AvatarConfig(talkingAvatarCharacter, talkingAvatarStyle, videoFormat)
    avatarConfig.backgroundColor = avatarAppConfig.avatarBackgroundColor;
    let avatarSynthesizer = new SpeechSDK.AvatarSynthesizer(speechSynthesisConfig, avatarConfig)

    avatarSynthesizer.avatarEventReceived = function (s, e) {
        var offsetMessage = ", offset from session start: " + e.offset / 10000 + "ms."
        if (e.offset === 0) {
            offsetMessage = ""
        }
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
