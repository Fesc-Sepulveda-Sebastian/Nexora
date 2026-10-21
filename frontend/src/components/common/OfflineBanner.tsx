import React from 'react';
import { useOfflineSync } from '../../context/OfflineSyncContext';
import { WifiOff, AlertTriangle } from 'lucide-react';

export const OfflineBanner: React.FC = () => {
  const { isOnline, lastOfflineSavedDate } = useOfflineSync();

  if (isOnline) return null;

  return (
    <div 
      role="alert"
      className="bg-amber-500/90 text-slate-950 px-4 py-2 text-xs md:text-sm font-semibold flex items-center justify-center gap-2 shadow-md sticky top-0 z-50 backdrop-blur-md"
    >
      <WifiOff className="w-4 h-4 shrink-0 text-slate-950" />
      <span>
        Sin conexión: mostrando datos guardados {lastOfflineSavedDate ? `a las ${lastOfflineSavedDate}` : 'localmente'} (RNF-02). Las acciones comerciales están temporalmente deshabilitadas.
      </span>
    </div>
  );
};
