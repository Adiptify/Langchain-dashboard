import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, XCircle, Loader2, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

const IngestionPanel = ({ isOpen, onClose, onIngestionComplete }) => {
    const [file, setFile] = useState(null);
    const [status, setStatus] = useState('idle'); // idle, uploading, success, error
    const [message, setMessage] = useState('');
    const fileInputRef = useRef(null);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
            setStatus('idle');
            setMessage('');
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        setStatus('uploading');
        try {
            const response = await axios.post('http://localhost:5000/api/ingest', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            if (response.data.status === 'success') {
                setStatus('success');
                setMessage(response.data.message);
                if (onIngestionComplete) onIngestionComplete();
            } else {
                setStatus('error');
                setMessage(response.data.message || 'Ingestion failed.');
            }
        } catch (error) {
            setStatus('error');
            setMessage(error.response?.data?.error || error.message);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="glass-card max-w-lg w-full p-8 relative border border-white/10"
            >
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 p-2 text-white/40 hover:text-white transition-colors"
                >
                    <X className="w-5 h-5" />
                </button>

                <div className="text-center mb-10">
                    <h2 className="text-3xl font-bold text-white mb-3 glow-text">Ingest Intelligence</h2>
                    <p className="text-white/50 text-sm font-medium">Upload datasets to expand the neural knowledge base.</p>
                </div>

                <div
                    onClick={() => fileInputRef.current.click()}
                    className={`border-2 border-dashed rounded-3xl p-12 flex flex-col items-center justify-center transition-all cursor-pointer group ${file ? 'border-primary/40 bg-primary/5' : 'border-white/10 hover:border-primary/20 hover:bg-primary/5'
                        }`}
                >
                    <input
                        type="file"
                        className="hidden"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        accept=".xlsx,.csv"
                    />

                    {file ? (
                        <div className="flex flex-col items-center">
                            <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center mb-6 border border-primary/20 shadow-xl shadow-primary/10">
                                <FileText className="w-10 h-10 text-primary-light" />
                            </div>
                            <span className="text-white font-bold text-lg text-center break-all mb-1">{file.name}</span>
                            <span className="text-white/40 text-[10px] font-bold uppercase tracking-widest">{(file.size / 1024 / 1024).toFixed(2)} MB • READY</span>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center">
                            <div className="w-20 h-20 rounded-full bg-white/[0.03] flex items-center justify-center mb-6 border border-white/5 group-hover:border-primary/40 transition-all group-hover:scale-110">
                                <Upload className="w-8 h-8 text-white/20 group-hover:text-primary-light" />
                            </div>
                            <span className="text-white/60 font-bold text-center">Click to browse or drag data</span>
                            <span className="text-white/20 text-[10px] mt-2 font-bold uppercase tracking-[0.2em]">XLSX • CSV SOURCE</span>
                        </div>
                    )}
                </div>

                <AnimatePresence mode="wait">
                    {status === 'idle' && file && (
                        <motion.button
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            onClick={handleUpload}
                            className="w-full mt-8 py-5 bg-gradient-to-r from-primary to-primary-dark text-white rounded-2xl font-bold transition-all shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] uppercase tracking-widest text-xs"
                        >
                            Execute Ingestion
                        </motion.button>
                    )}

                    {status === 'uploading' && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="mt-8 p-6 rounded-2xl bg-primary/5 border border-primary/20 flex items-center gap-5"
                        >
                            <Loader2 className="w-8 h-8 text-primary-light animate-spin" />
                            <div className="flex-1">
                                <p className="text-white font-bold text-sm uppercase tracking-wider">Processing Neural Data...</p>
                                <p className="text-white/30 text-[10px] font-medium uppercase tracking-widest">Bypassing SLM for Maximum Velocity</p>
                            </div>
                        </motion.div>
                    )}

                    {status === 'success' && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="mt-8 p-6 rounded-2xl bg-green-500/5 border border-green-500/20 flex items-center gap-5"
                        >
                            <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center">
                                <CheckCircle2 className="w-6 h-6 text-green-500" />
                            </div>
                            <div className="flex-1">
                                <p className="text-white font-bold text-sm uppercase tracking-wider">Database Synchronized</p>
                                <p className="text-green-500/60 text-[10px] font-medium uppercase tracking-widest">{message}</p>
                            </div>
                        </motion.div>
                    )}

                    {status === 'error' && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="mt-8 p-6 rounded-2xl bg-red-500/5 border border-red-500/20 flex items-center gap-5"
                        >
                            <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center">
                                <XCircle className="w-6 h-6 text-red-500" />
                            </div>
                            <div className="flex-1">
                                <p className="text-white font-bold text-sm uppercase tracking-wider">Ingest Failed</p>
                                <p className="text-red-500/60 text-[10px] font-medium uppercase tracking-widest">{message}</p>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {status === 'success' && (
                    <button
                        onClick={onClose}
                        className="w-full mt-8 py-4 border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] text-white/40 hover:text-white/60 rounded-2xl transition-all text-[10px] font-bold uppercase tracking-widest"
                    >
                        Terminal Exit
                    </button>
                )}
            </motion.div>
        </div>
    );
};

export default IngestionPanel;
