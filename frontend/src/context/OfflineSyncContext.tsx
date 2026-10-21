import React, { createContext, useContext, useState, useEffect } from 'react';
import { syncManager, SyncState, ConflictDetails } from '../services/syncManager';

interface OfflineSyncContextType {
  isOnline: boolean;
  syncStatus: SyncState;
  lastOfflineSavedDate: string | null;
  conflict: ConflictDetails | null;
  setConflict: (conflict: ConflictDetails | null) => void;
  resolveConflict: (choice: 'keep_server' | 'keep_local') => void;
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
      setLastOfflineSavedDate(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
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

  const resolveConflict = (choice: 'keep_server' | 'keep_local') => {
    // RF-31 & RNF-14 resolution
    console.log(`[ConflictResolution] User chose: ${choice}`);
    setConflict(null);
    setSyncStatus('Sincronizado');
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
        triggerSync
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
