import React, { useState, useEffect } from 'react';
import { CampaignWizard } from '../components/campaign-wizard/CampaignWizard';
import { indexDB, OfflineDraft } from '../db/indexdb';
import { Campaign } from '../types';
import { FileEdit, Layers, Trash2 } from 'lucide-react';

interface IU04CampaignWizardProps {
  onSuccess: (campaign: Campaign) => void;
}

export const IU04_CampaignWizard: React.FC<IU04CampaignWizardProps> = ({ onSuccess }) => {
  const [localDrafts, setLocalDrafts] = useState<OfflineDraft[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<OfflineDraft | null>(null);

  useEffect(() => {
    loadLocalDrafts();
  }, []);

  const loadLocalDrafts = async () => {
    const drafts = await indexDB.getLocalDrafts();
    setLocalDrafts(drafts);
  };

  const handleDeleteDraft = async (e: React.MouseEvent, localId: string) => {
    e.stopPropagation();
    await indexDB.deleteLocalDraft(localId);
    await indexDB.removeOutboxAction(`outbox_${localId}`);
    if (selectedDraft?.local_id === localId) {
      setSelectedDraft(null);
    }
    await loadLocalDrafts();
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-24">
      {/* Drafts Drawer: click to load into wizard */}
      {localDrafts.length > 0 && (
        <div className="mb-6 p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center gap-2 text-brand-400 font-bold text-xs uppercase tracking-wider mb-2">
            <Layers className="w-4 h-4" />
            <span>Borradores Guardados Localmente ({localDrafts.length}/5 permitidos RNF-02):</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {localDrafts.map((d) => {
              const isSelected = selectedDraft?.local_id === d.local_id;
              return (
                <div
                  key={d.local_id}
                  onClick={() => setSelectedDraft(d)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setSelectedDraft(d)}
                  className={`px-3 py-2 rounded-xl border text-xs flex items-center gap-2 cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-brand-950/60 border-brand-500 text-white'
                      : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-brand-500/50'
                  }`}
                >
                  <FileEdit className="w-3.5 h-3.5 text-brand-400" />
                  <span className="font-semibold">{d.title}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-amber-400">
                    {d.sync_status}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => handleDeleteDraft(e, d.local_id)}
                    aria-label="Eliminar borrador local"
                    className="p-1 text-slate-400 hover:text-rose-400"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Main Wizard */}
      <CampaignWizard
        initialDraft={selectedDraft}
        onDraftSaved={loadLocalDrafts}
        onCampaignCreated={onSuccess}
      />
    </div>
  );
};
