import React from 'react';
import { Sparkles, X, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const BriefingModal = ({ isOpen, onClose, briefing }) => {
    if (!isOpen || !briefing) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            <motion.div
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 20, scale: 0.95 }}
                className="glass-card max-w-2xl w-full p-10 relative border border-primary/20 shadow-2xl shadow-primary/10"
            >
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-secondary to-primary" />

                <button
                    onClick={onClose}
                    className="absolute top-6 right-6 p-2 text-white/20 hover:text-white transition-colors hover:bg-white/5 rounded-lg"
                >
                    <X className="w-5 h-5" />
                </button>

                <div className="flex items-center gap-4 mb-8">
                    <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20">
                        <Sparkles className="w-8 h-8 text-primary-light" />
                    </div>
                    <div>
                        <h2 className="text-3xl font-bold text-white glow-text">Daily Intelligence Briefing</h2>
                        <p className="text-white/40 text-[10px] font-bold uppercase tracking-[0.2em] mt-1">Neural Analysis • Plant Operations</p>
                    </div>
                </div>

                <div className="bg-white/[0.03] rounded-3xl p-8 border border-white/5 mb-8">
                    <div className="prose prose-invert max-w-none">
                        <p className="text-lg text-white/90 leading-relaxed font-medium">
                            {briefing}
                        </p>
                    </div>
                </div>

                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
                        <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest">Analysis Synchronized</span>
                    </div>

                    <button
                        onClick={onClose}
                        className="group flex items-center gap-3 px-8 py-4 bg-primary hover:bg-primary-dark text-white rounded-2xl font-bold transition-all shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] uppercase tracking-widest text-[10px]"
                    >
                        Acknowledge & Sync
                        <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </button>
                </div>
            </motion.div>
        </div>
    );
};

export default BriefingModal;
