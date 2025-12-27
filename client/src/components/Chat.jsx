import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

const Chat = ({ messages, setMessages }) => {
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isListening, setIsListening] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const [speakingMessageIndex, setSpeakingMessageIndex] = useState(null);
    const [currentWordIndex, setCurrentWordIndex] = useState(-1);
    const [suggestions, setSuggestions] = useState([]);
    const [kpis, setKpis] = useState(null);
    const messagesEndRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const audioPlayerRef = useRef(new Audio());

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        fetchSuggestions();
        fetchKPIs();
    }, []);

    const fetchKPIs = async () => {
        try {
            const response = await axios.get('http://localhost:5000/api/kpis');
            setKpis(response.data.kpis);
        } catch (error) {
            console.error('Failed to fetch KPIs:', error);
        }
    };

    const fetchSuggestions = async () => {
        try {
            const response = await axios.get('http://localhost:5000/api/suggestions', {
                params: { user_id: 'tester' }
            });
            setSuggestions(response.data.suggestions);
        } catch (error) {
            console.error('Failed to fetch suggestions:', error);
        }
    };

    // Handle Neural TTS Playback & Highlighting
    useEffect(() => {
        const lastMessage = messages[messages.length - 1];
        if (lastMessage && lastMessage.role === 'assistant' && !isMuted) {
            handleSpeech(lastMessage.content, messages.length - 1);
        }

        return () => {
            audioPlayerRef.current.pause();
            audioPlayerRef.current.src = "";
            setSpeakingMessageIndex(null);
            setCurrentWordIndex(-1);
        };
    }, [messages, isMuted]);

    const handleSpeech = async (text, index) => {
        setSpeakingMessageIndex(index);
        setCurrentWordIndex(-1);
        await speak(text);
    };

    // Words highlighting synchronizer
    useEffect(() => {
        const player = audioPlayerRef.current;

        const updateHighlight = () => {
            if (speakingMessageIndex !== null && player.duration > 0) {
                const text = messages[speakingMessageIndex].content;
                const words = text.split(/\s+/);
                const totalChars = text.length;
                const currentPos = player.currentTime / player.duration;
                const targetCharCount = totalChars * currentPos;

                let cumulativeChars = 0;
                let targetIndex = 0;
                for (let i = 0; i < words.length; i++) {
                    cumulativeChars += words[i].length + 1; // +1 for space
                    if (cumulativeChars >= targetCharCount) {
                        targetIndex = i;
                        break;
                    }
                }
                setCurrentWordIndex(targetIndex);
            }
        };

        const resetHighlight = () => {
            setSpeakingMessageIndex(null);
            setCurrentWordIndex(-1);
        };

        player.addEventListener('timeupdate', updateHighlight);
        player.addEventListener('ended', resetHighlight);
        player.addEventListener('pause', () => {
            if (player.currentTime === 0) resetHighlight();
        });

        return () => {
            player.removeEventListener('timeupdate', updateHighlight);
            player.removeEventListener('ended', resetHighlight);
        };
    }, [speakingMessageIndex, messages]);

    // STT Recording Logic
    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream);
            audioChunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorderRef.current.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                await sendAudioToBackend(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorderRef.current.start();
            setIsListening(true);
        } catch (error) {
            console.error('Error starting recording:', error);
            alert('Could not access microphone.');
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop();
            setIsListening(false);
        }
    };

    const sendAudioToBackend = async (blob) => {
        setIsLoading(true);
        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');

        try {
            const response = await axios.post('http://localhost:5000/api/stt', formData);
            if (response.data.text) {
                // Automatically send transcribed text
                await sendMessage(response.data.text);
            }
        } catch (error) {
            console.error('Transcription error:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const toggleListening = () => {
        if (isListening) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    const speak = async (text) => {
        if (!text || isMuted) return;

        try {
            const response = await axios.post('http://localhost:5000/api/tts',
                { prompt: text },
                { responseType: 'blob' }
            );

            const audioUrl = URL.createObjectURL(response.data);
            audioPlayerRef.current.src = audioUrl;
            audioPlayerRef.current.play();
        } catch (error) {
            console.error('TTS Error:', error);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        sendMessage(input);
    };

    const sendMessage = async (text) => {
        if (!text.trim() || isLoading) return;

        const userMessage = { role: 'user', content: text };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await axios.post('http://localhost:5000/api/chat', {
                prompt: text,
                chat_history: messages
            });

            const assistantMessage = {
                role: 'assistant',
                content: response.data.answer,
                results: response.data.results
            };
            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Error: ${error.response?.data?.error || error.message}`
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex-1 flex flex-col h-screen overflow-hidden bg-transparent">
            {/* Header */}
            <div className="p-6 border-b border-white/10 backdrop-blur-md z-10 flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-white">Assistant</h2>
                    <p className="text-xs text-white/40">Powered by LangChain & Ollama</p>
                </div>
                <button
                    onClick={() => setIsMuted(!isMuted)}
                    className={`p-2 rounded-lg transition-all ${isMuted ? 'text-white/20 hover:text-white/40' : 'text-primary-light hover:bg-primary/10'}`}
                    title={isMuted ? "Unmute Assistant" : "Mute Assistant"}
                >
                    {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <AnimatePresence>
                    {messages.length === 0 && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="h-full flex flex-col items-center justify-center text-center space-y-4"
                        >
                            <div className="p-4 bg-primary/10 rounded-full">
                                <Bot className="w-12 h-12 text-primary-light" />
                            </div>
                            <div>
                                <h3 className="text-xl font-medium text-white">How can I help you today?</h3>
                                <p className="text-white/40 max-w-sm">
                                    Ask me about your energy consumption, feeders, or plant summaries.
                                </p>
                            </div>
                        </motion.div>
                    )}

                    {messages.map((message, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div className={`flex gap-4 max-w-[80%] ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${message.role === 'user' ? 'bg-secondary/20 text-secondary-light' : 'bg-primary/20 text-primary-light'
                                    }`}>
                                    {message.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                                </div>
                                <div
                                    onClick={() => message.role === 'assistant' && handleSpeech(message.content, index)}
                                    className={`p-4 rounded-2xl relative group/msg transition-all duration-200 ${message.role === 'user'
                                        ? 'bg-secondary/20 text-white rounded-tr-none border border-secondary/10'
                                        : 'glass-card text-white rounded-tl-none cursor-pointer hover:bg-white/5 active:scale-[0.99] shadow-lg hover:shadow-primary/5'
                                        }`}>
                                    <div className="text-sm leading-relaxed whitespace-pre-wrap">
                                        {message.role === 'assistant' ? (
                                            message.content.split(/\s+/).map((word, wIdx) => (
                                                <span
                                                    key={wIdx}
                                                    className={`transition-all duration-150 inline-block px-0.5 rounded ${index === speakingMessageIndex && wIdx === currentWordIndex
                                                        ? 'text-primary-light font-bold scale-110 bg-primary/20 drop-shadow-[0_0_12px_rgba(var(--primary-rgb),0.6)]'
                                                        : 'text-white/90'}`}
                                                >
                                                    {word}{' '}
                                                </span>
                                            ))
                                        ) : (
                                            message.content
                                        )}
                                    </div>

                                    {message.role === 'assistant' && (
                                        <button
                                            onClick={() => handleSpeech(message.content, index)}
                                            className="absolute -right-10 top-0 p-2 text-white/20 hover:text-primary-light transition-all opacity-0 group-hover/msg:opacity-100"
                                            title="Re-listen"
                                        >
                                            <Volume2 className="w-4 h-4" />
                                        </button>
                                    )}

                                    {message.results && message.results.length > 0 && (
                                        <div className="mt-4 pt-4 border-t border-white/5 space-y-2">
                                            <p className="text-[10px] font-bold text-white/20 uppercase tracking-widest">Data Sources</p>
                                            <div className="flex flex-wrap gap-2">
                                                {message.results.map((res, i) => (
                                                    <div key={i} className="px-2 py-1 rounded bg-white/5 border border-white/5 text-[10px] text-white/40">
                                                        <span className="font-bold text-primary-light/60 uppercase">{res.doc_type?.replace('_', ' ')}</span>: {res.file_name}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>

                {isLoading && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="flex justify-start"
                    >
                        <div className="flex gap-4 max-w-[80%]">
                            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-primary/20 text-primary-light">
                                <Loader2 className="w-5 h-5 animate-spin" />
                            </div>
                            <div className="p-4 rounded-2xl glass-card rounded-tl-none">
                                <div className="flex gap-1">
                                    <span className="w-1.5 h-1.5 bg-primary-light/40 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <span className="w-1.5 h-1.5 bg-primary-light/40 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <span className="w-1.5 h-1.5 bg-primary-light/40 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* KPI Suggestions */}
            {kpis && (
                <div className="px-6 pb-2 overflow-x-auto no-scrollbar">
                    <div className="flex gap-3 whitespace-nowrap">
                        <motion.button
                            whileHover={{ y: -2 }}
                            whileActive={{ scale: 0.98 }}
                            onClick={() => sendMessage(`Show me the details for the peak day ${kpis.peak_day}`)}
                            className="flex flex-col items-start p-3 bg-primary/10 border border-primary/20 rounded-2xl min-w-[140px] text-left transition-all hover:bg-primary/20"
                        >
                            <span className="text-[9px] font-bold text-primary-light uppercase tracking-wider mb-1">Peak Intensity</span>
                            <span className="text-sm font-bold text-white">{kpis.peak_day_val.toLocaleString()} KWH</span>
                            <span className="text-[8px] text-white/40 mt-0.5">{kpis.peak_day}</span>
                        </motion.button>

                        <motion.button
                            whileHover={{ y: -2 }}
                            whileActive={{ scale: 0.98 }}
                            onClick={() => sendMessage(`Summarize consumption for ${kpis.peak_month}`)}
                            className="flex flex-col items-start p-3 bg-secondary/10 border border-secondary/20 rounded-2xl min-w-[140px] text-left transition-all hover:bg-secondary/20"
                        >
                            <span className="text-[9px] font-bold text-secondary-light uppercase tracking-wider mb-1">Highest Month</span>
                            <span className="text-sm font-bold text-white">{kpis.peak_month}</span>
                            <span className="text-[8px] text-white/40 mt-0.5">{kpis.coverage_months} Months Tracked</span>
                        </motion.button>
                    </div>
                </div>
            )}

            {/* Query Suggestions */}
            {suggestions.length > 0 && (
                <div className="px-6 pb-4">
                    <div className="flex flex-wrap gap-2">
                        {suggestions.slice(0, 3).map((sug, i) => (
                            <button
                                key={i}
                                onClick={() => sendMessage(sug)}
                                className="px-4 py-2 bg-white/[0.03] hover:bg-primary/10 border border-white/5 hover:border-primary/20 rounded-xl text-[10px] font-bold text-white/40 hover:text-primary-light transition-all active:scale-[0.98] uppercase tracking-wider"
                            >
                                {sug}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Input */}
            <div className="p-6 pt-0">
                <form
                    onSubmit={handleSubmit}
                    className="relative glass-card rounded-2xl p-2 flex items-center gap-2 border border-white/10"
                >
                    <button
                        type="button"
                        onClick={toggleListening}
                        className={`p-3 rounded-xl transition-all ${isListening
                            ? 'bg-red-500/20 text-red-500 pulse'
                            : 'bg-white/5 text-white/40 hover:text-white/80 hover:bg-white/10'
                            }`}
                    >
                        {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                    </button>

                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={isListening ? "Listening..." : "Type or speak your question..."}
                        className="flex-1 bg-transparent border-none focus:ring-0 text-white px-4 py-2 text-sm outline-none"
                        disabled={isLoading}
                    />

                    {isListening && (
                        <div className="flex items-center gap-1 px-2">
                            <span className="wave-bar" style={{ animationDelay: '0.1s' }} />
                            <span className="wave-bar" style={{ animationDelay: '0.2s' }} />
                            <span className="wave-bar" style={{ animationDelay: '0.3s' }} />
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className="p-3 bg-primary hover:bg-primary-dark disabled:bg-white/5 disabled:text-white/20 rounded-xl transition-all"
                    >
                        <Send className="w-4 h-4 text-white" />
                    </button>
                </form>
                <p className="text-[10px] text-center mt-3 text-white/20 uppercase tracking-widest font-bold">
                    Voice Enabled Energy Intelligence
                </p>
            </div>
        </div>
    );
};

export default Chat;
