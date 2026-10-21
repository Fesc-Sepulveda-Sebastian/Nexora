import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { OfflineSyncProvider } from './context/OfflineSyncContext';
import { Navbar } from './components/common/Navbar';
import { BottomNav } from './components/common/BottomNav';
import { OfflineBanner } from './components/common/OfflineBanner';
import { ConflictResolutionModal } from './components/common/ConflictResolutionModal';

import { IU01_Auth } from './views/IU01_Auth';
import { IU02_Marketplace } from './views/IU02_Marketplace';
import { IU03_MediaKit } from './views/IU03_MediaKit';
import { IU04_CampaignWizard } from './views/IU04_CampaignWizard';
import { IU05_CampaignDetail } from './views/IU05_CampaignDetail';
import { IU06_Collaboration } from './views/IU06_Collaboration';

const MainApp: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [currentView, setCurrentView] = useState<string>('marketplace');
  const [selectedCreatorId, setSelectedCreatorId] = useState<string | undefined>(undefined);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | undefined>(undefined);

  const handleSelectCreator = (creatorId: string) => {
    setSelectedCreatorId(creatorId);
    setCurrentView('mediakit');
  };

  const handleSelectCampaign = (campaignId: string) => {
    setSelectedCampaignId(campaignId);
    setCurrentView('campaign_detail');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-brand-500 selection:text-white">
      {/* Offline Alert Banner (RF-20 / RNF-02) */}
      <OfflineBanner />

      {/* Responsive Top Navbar */}
      <Navbar currentView={currentView} onNavigate={setCurrentView} />

      {/* Main Content Area */}
      <main className="flex-1">
        {currentView === 'auth' && (
          <IU01_Auth onSuccess={() => setCurrentView('marketplace')} />
        )}

        {currentView === 'marketplace' && (
          <IU02_Marketplace
            onSelectCreator={handleSelectCreator}
            onSelectCampaign={handleSelectCampaign}
          />
        )}

        {currentView === 'mediakit' && (
          <IU03_MediaKit
            creatorId={selectedCreatorId}
            onContactOrInvite={() => setCurrentView('collaboration')}
          />
        )}

        {currentView === 'create_campaign' && (
          <IU04_CampaignWizard
            onSuccess={() => setCurrentView('marketplace')}
          />
        )}

        {currentView === 'campaign_detail' && selectedCampaignId && (
          <IU05_CampaignDetail
            campaignId={selectedCampaignId}
            onBack={() => setCurrentView('marketplace')}
            onApplicationSuccess={() => setCurrentView('collaboration')}
          />
        )}

        {currentView === 'collaboration' && (
          <IU06_Collaboration campaignId={selectedCampaignId} />
        )}
      </main>

      {/* Mobile Bottom Navigation (< 768px with touch targets >= 44x44px) */}
      <BottomNav currentView={currentView} onNavigate={setCurrentView} />

      {/* HTTP 409 Version Conflict Modal (RF-31, RNF-14) */}
      <ConflictResolutionModal />
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <OfflineSyncProvider>
        <MainApp />
      </OfflineSyncProvider>
    </AuthProvider>
  );
}
