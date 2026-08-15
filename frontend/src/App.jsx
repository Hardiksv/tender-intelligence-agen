import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import TenderDetail from './pages/TenderDetail';
import ProfileEditor from './pages/ProfileEditor';
import RagChat from './pages/RagChat';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedTenderId, setSelectedTenderId] = useState(null);

  const handleSelectTender = (id) => {
    setSelectedTenderId(id);
    setActiveTab('detail');
  };

  const handleBackToDashboard = () => {
    setSelectedTenderId(null);
    setActiveTab('dashboard');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar 
        activeTab={activeTab} 
        setActiveTab={(tab) => {
          setSelectedTenderId(null);
          setActiveTab(tab);
        }}
        onIngestionCompleted={() => {
          if (activeTab === 'dashboard') {
            window.location.reload();
          }
        }}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {activeTab === 'dashboard' && (
          <Dashboard onSelectTender={handleSelectTender} />
        )}

        {activeTab === 'detail' && selectedTenderId && (
          <TenderDetail tenderId={selectedTenderId} onBack={handleBackToDashboard} />
        )}

        {activeTab === 'profile' && (
          <ProfileEditor />
        )}

        {activeTab === 'chat' && (
          <RagChat />
        )}
      </main>

      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
        Tender Intelligence Agent • Bus Operations Procurement AI Platform • Asia/Kolkata
      </footer>
    </div>
  );
}
