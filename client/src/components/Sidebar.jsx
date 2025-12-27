import React, { useState, useEffect } from 'react';
import { Database, Zap, Activity, UploadCloud, Trash2, RotateCcw } from 'lucide-react';
import axios from 'axios';

const Sidebar = ({ onClearChat, onIngestClick, refreshTrigger }) => {
    const [stats, setStats] = useState({ document_count: 0, status: 'loading' });
    const [kpis, setKpis] = useState(null);

    useEffect(() => {
        fetchStats();
        fetchKPIs();
    }, [refreshTrigger]);

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 10000);
        return () => clearInterval(interval);
    }, []);

    const fetchStats = async () => {
        try {
            const response = await axios.get('http://localhost:5000/api/stats');
            setStats(response.data);
        } catch (error) {
            setStats({ document_count: 0, status: 'error' });
        }
    };

    const fetchKPIs = async () => {
        try {
            const response = await axios.get('http://localhost:5000/api/kpis');
            setKpis(response.data.kpis);
        } catch (error) {
            console.error('Failed to fetch KPIs:', error);
            setKpis(null);
        }
    };

    const handleClearSystem = async () => {
        if (window.confirm("⚠️ WARNING: This will permanently delete ALL ingested data, summaries, and KPIs. Are you sure?")) {
            try {
                await axios.post('http://localhost:5000/api/clear');
                fetchStats();
                fetchKPIs();
                alert("System data cleared successfully.");
            } catch (error) {
                alert("Failed to clear data: " + error.message);
            }
        }
    };

    return (
        <div className="w-72 h-full flex flex-col glass-card border-r border-white/10 p-8 z-10">
            <div className="flex items-center gap-4 mb-12">
                <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-lg shadow-primary/10">
                    <Zap className="w-7 h-7 text-primary-light" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-primary-light to-secondary-light bg-clip-text text-transparent glow-text">
                        MendyGo
                    </h1>
                    <p className="text-[10px] text-white/30 uppercase tracking-[0.2em] font-bold">Intelligence</p>
                </div>
            </div>

            <nav className="flex-1 space-y-10">
                <div>
                    <h2 className="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em] mb-6">
                        Data Overview
                    </h2>
                    <div className="space-y-4">
                        {/* Indexed Records */}
                        <div className="bg-white/[0.03] rounded-2xl p-6 border border-white/5 transition-all hover:border-primary/20 hover:bg-white/[0.05]">
                            <div className="flex items-center gap-3 mb-3">
                                <Database className="w-4 h-4 text-primary-light" />
                                <span className="text-xs font-bold text-white/60 tracking-wider text-[10px] uppercase">INDEXED RECORDS</span>
                            </div>
                            <div className="text-4xl font-bold text-white mb-3 tabular-nums">
                                {stats.document_count.toLocaleString()}
                            </div>
                            <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${stats.status === 'ok' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'}`} />
                                <span className="text-[10px] font-bold text-white/40 uppercase tracking-wider">
                                    {stats.status === 'ok' ? 'System Optimized' : 'Data Missing'}
                                </span>
                            </div>
                        </div>

                        {/* Peak Consumption KPI */}
                        {kpis && (
                            <div className="bg-white/[0.03] rounded-2xl p-6 border border-white/5 border-l-primary/40 border-l-4 transition-all hover:bg-white/[0.05]">
                                <div className="flex items-center gap-3 mb-3">
                                    <Zap className="w-4 h-4 text-secondary-light" />
                                    <span className="text-xs font-bold text-white/60 tracking-wider text-[10px] uppercase">Peak Intensity</span>
                                </div>
                                <div className="text-2xl font-bold text-white mb-1 tabular-nums">
                                    {kpis.peak_day_val.toLocaleString()} KWH
                                </div>
                                <div className="text-[10px] font-bold text-secondary-light/60 uppercase tracking-wider">
                                    RECORDED ON {kpis.peak_day}
                                </div>
                            </div>
                        )}

                        {/* Monthly Overview */}
                        {kpis && (
                            <div className="bg-white/[0.03] rounded-2xl p-6 border border-white/5 transition-all hover:bg-white/[0.05]">
                                <div className="flex items-center gap-3 mb-2">
                                    <Activity className="w-4 h-4 text-primary-light" />
                                    <span className="text-xs font-bold text-white/60 tracking-wider text-[10px] uppercase">Data Coverage</span>
                                </div>
                                <div className="text-sm font-bold text-white mb-1">
                                    {kpis.coverage_months} Months Analyzed
                                </div>
                                <div className="text-[10px] font-bold text-white/30 uppercase tracking-wider">
                                    MAX CONS: {kpis.peak_month}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <div>
                    <h2 className="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em] mb-6">
                        Security & Controls
                    </h2>
                    <button
                        onClick={onIngestClick}
                        className="w-full flex items-center gap-3 px-5 py-4 rounded-xl bg-primary/10 hover:bg-primary/20 border border-primary/20 transition-all text-xs font-bold text-primary-light mb-4 shadow-lg shadow-primary/5 active:scale-[0.98]"
                    >
                        <UploadCloud className="w-4 h-4" />
                        INGEST INTELLIGENCE
                    </button>
                    <button
                        onClick={onClearChat}
                        className="w-full py-4 flex items-center justify-center gap-3 bg-white/5 hover:bg-white/10 text-white/60 hover:text-white rounded-2xl transition-all border border-white/5 group mb-4"
                    >
                        <Trash2 className="w-4 h-4 group-hover:scale-110 transition-transform" />
                        <span className="text-xs font-bold uppercase tracking-wider">Clear Chat</span>
                    </button>

                    <button
                        onClick={handleClearSystem}
                        className="w-full py-4 flex items-center justify-center gap-3 bg-red-500/5 hover:bg-red-500/10 text-red-400/60 hover:text-red-400 rounded-2xl transition-all border border-red-500/10 group"
                    >
                        <RotateCcw className="w-4 h-4 group-hover:rotate-[-180deg] transition-transform duration-500" />
                        <span className="text-xs font-bold uppercase tracking-wider text-[10px]">Wipe System Data</span>
                    </button>
                </div>
            </nav>

            <div className="mt-auto pt-8 border-t border-white/10">
                <div className="flex items-center gap-3 text-white/30 hover:text-white/60 transition-all cursor-pointer group">
                    <div className="p-2 bg-white/5 rounded-lg group-hover:bg-green-500/10 transition-all">
                        <Activity className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-bold tracking-wider uppercase">Kernel Status</span>
                    <Activity className="w-3 h-3 ml-auto text-green-500 animate-pulse" />
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
