import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
import IngestionPanel from './components/IngestionPanel';
import BriefingModal from './components/BriefingModal';
import axios from 'axios';

function App() {
  const [messages, setMessages] = useState([]);
  const [isIngestOpen, setIsIngestOpen] = useState(false);
  const [isBriefingOpen, setIsBriefingOpen] = useState(false);
  const [briefing, setBriefing] = useState('');
  const [refreshStats, setRefreshStats] = useState(0);

  useEffect(() => {
    fetchBriefing();
  }, [refreshStats]);

  const fetchBriefing = async () => {
    try {
      const response = await axios.get('http://localhost:5000/api/briefing', {
        params: { user_id: 'tester' }
      });
      if (response.data.should_show && response.data.briefing) {
        setBriefing(response.data.briefing);
        setIsBriefingOpen(true);
      }
    } catch (error) {
      console.error('Failed to fetch briefing:', error);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  return (
    <div className="flex h-screen w-full bg-[#0f172a] overflow-hidden">
      {/* Background Orbs */}
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-secondary/10 blur-[120px] rounded-full" />
      </div>

      <Sidebar
        onClearChat={handleClearChat}
        onIngestClick={() => setIsIngestOpen(true)}
        refreshTrigger={refreshStats}
      />

      <main className="flex-1 flex flex-col relative z-10">
        <Chat messages={messages} setMessages={setMessages} />
      </main>

      <IngestionPanel
        isOpen={isIngestOpen}
        onClose={() => setIsIngestOpen(false)}
        onIngestionComplete={() => setRefreshStats(prev => prev + 1)}
      />

      <BriefingModal
        isOpen={isBriefingOpen}
        onClose={() => setIsBriefingOpen(false)}
        briefing={briefing}
      />
    </div>
  );
}

export default App;
