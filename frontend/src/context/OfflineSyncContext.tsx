import React, { createContext, useContext, useState, useEffect } from 'react';
import { syncManager, SyncState, ConflictDetails } from '../services/syncManager';
import { indexDB } from '../db/indexdb';

interface OfflineSyncContextType {
  isOnline: boolean;
  syncStatus: SyncState;
  lastOfflineSavedDate: string | null;
  conflict: ConflictDetails | null;
  setConflict: (conflict: ConflictDetails | null) => void;
  resolveConflict: (choice: 'keep_server' | 'keep_local') => Promise<void>;
  triggerSync: () => Promise<void>;
}

const OfflineSyncContext = createContext<OfflineSyncContextType | undefined>(undefined);

export const OfflineSyncProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [syncStatus, setSyncStatus] = useState<SyncState>('Sincronizado');
  const [lastOfflineSavedDate, setLastOfflineSavedDate] = useState<string | null>(null);
  const [conflict, setConflict] = useState<ConflictDetails | null>(null);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      syncManager.processOutbox();
    };

    const handleOffline = () => {
      setIsOnline(false);
      setLastOfflineSavedDate(
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      );
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    const unsubStatus = syncManager.onStatusChange((status) => {
      setSyncStatus(status);
    });

    const unsubConflict = syncManager.onConflict((c) => {
      setConflict(c);
    });

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      unsubStatus();
      unsubConflict();
    };
  }, []);

  const resolveConflict = async (choice: 'keep_server' | 'keep_local') => {
    if (!conflict) return;

    const { localDraft, outboxActionId, campaignId, serverVersion, serverData } = conflict;

    if (choice === 'keep_server') {
      // Adopt server version locally and discard conflicting outbox mutation
      await indexDB.saveLocalDraft({
        ...localDraft,
        server_id: serverData.id || campaignId || localDraft.server_id,
        title: serverData.title ?? localDraft.title,
        objective: serverData.objective ?? localDraft.objective,
        niche: serverData.niche ?? localDraft.niche,
        budget: serverData.budget ?? localDraft.budget,
        compensation_type: serverData.compensation_type ?? localDraft.compensation_type,
        compensation_notes: serverData.compensation_notes ?? localDraft.compensation_notes,
        deliverables: serverData.deliverables ?? localDraft.deliverables,
        selection_criteria: serverData.selection_criteria ?? localDraft.selection_criteria,
        version_id: serverVersion,
        sync_status: 'Sincronizado',
        last_modified: new Date().toISOString(),
      });
      if (outboxActionId) {
        await indexDB.removeOutboxAction(outboxActionId);
      }
      setConflict(null);
      setSyncStatus('Sincronizado');
      return;
    }

    // choice === 'keep_local': Force local changes onto server using serverVersion as expected base
    const targetCampaignId = serverData.id || campaignId || localDraft.server_id;
    const updatedDraft = {
      ...localDraft,
      server_id: targetCampaignId,
      version_id: serverVersion,
      sync_status: 'Pendiente' as const,
      last_modified: new Date().toISOString(),
    };
    await indexDB.saveLocalDraft(updatedDraft);

    if (outboxActionId) {
      await indexDB.removeOutboxAction(outboxActionId);
    }

    if (targetCampaignId) {
      await indexDB.addToOutbox({
        id: `outbox_${localDraft.local_id}_resolve_${Date.now()}`,
        action_type: 'SYNC_CAMPAIGN',
        method: 'PUT',
        endpoint: `/campaigns/${targetCampaignId}`,
        payload: {
          title: localDraft.title,
          objective: localDraft.objective,
          niche: localDraft.niche,
          budget: localDraft.budget,
          compensation_type: localDraft.compensation_type,
          compensation_notes: localDraft.compensation_notes,
          start_date: localDraft.start_date,
          end_date: localDraft.end_date,
          deliverables: localDraft.deliverables,
          selection_criteria: localDraft.selection_criteria,
          version_id: serverVersion,
        },
        idempotency_key: `resolve_${localDraft.local_id}_v${serverVersion}_${Date.now()}`,
        local_draft_id: localDraft.local_id,
        created_at: new Date().toISOString(),
        retry_count: 0,
      });
    }

    setConflict(null);
    setSyncStatus('Pendiente');
    if (navigator.onLine) {
      await syncManager.processOutbox();
    }
  };

  const triggerSync = async () => {
    await syncManager.processOutbox();
  };

  return (
    <OfflineSyncContext.Provider
      value={{
        isOnline,
        syncStatus,
        lastOfflineSavedDate,
        conflict,
        setConflict,
        resolveConflict,
        triggerSync,
      }}
    >
      {children}
    </OfflineSyncContext.Provider>
  );
};

export const useOfflineSync = () => {
  const context = useContext(OfflineSyncContext);
  if (!context) throw new Error('useOfflineSync must be used within OfflineSyncProvider');
  return context;
};
