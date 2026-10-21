import React, { useState, useEffect } from 'react';
import { CampaignWizard } from '../components/campaign-wizard/CampaignWizard';
import { indexDB, OfflineDraft } from '../db/indexdb';
import { Campaign } from '../types';
import { FileEdit, Clock, CheckCircle2, AlertTriangle, Layers } from 'lucide-react';

interface IU04CampaignWizardProps {
  onSuccess: (campaign: Campaign) => void;
}

export const IU04_CampaignWizard: React.FC<IU04CampaignWizardProps> = ({ onSuccess }) => {
  const [localDrafts, setLocalDrafts] = useState<OfflineDraft[]>([]);

  useEffect(() => {
    loadLocalDrafts();
  }, []);

  const loadLocalDrafts = async () => {
    const drafts = await indexDB.getLocalDrafts();
    setLocalDrafts(drafts);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-24">
      {/* Drafts Drawer / Status Badge if there are offline drafts */}
      {localDrafts.length > 0 && (
        <div className="mb-6 p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center gap-2 text-brand-400 font-bold text-xs uppercase tracking-wider mb-2">
            <Layers className="w-4 h-4" />
            <span>Borradores Guardados Localmente ({localDrafts.length}/5 permitidos RNF-02):</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {localDrafts.map((d) => (
              <div
                key={d.local_id}
                className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 flex items-center gap-2"
              >
                <FileEdit className="w-3.5 h-3.5 text-brand-400" />
                <span className="font-semibold">{d.title}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-amber-400">
                  {d.sync_status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Wizard */}
      <CampaignWizard onCampaignCreated={onSuccess} />
    </div>
  );
};
