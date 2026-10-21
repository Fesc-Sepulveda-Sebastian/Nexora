import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useOfflineSync } from '../../context/OfflineSyncContext';
import { Flame, Cloud, CloudOff, RefreshCw, AlertCircle, CheckCircle, LogOut } from 'lucide-react';

interface NavbarProps {
  currentView: string;
  onNavigate: (view: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate }) => {
  const { user, isAuthenticated, logout } = useAuth();
  const { isOnline, syncStatus, triggerSync } = useOfflineSync();

  const getSyncBadge = () => {
    switch (syncStatus) {
      case 'Sincronizado':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-emerald-950/70 text-emerald-400 border border-emerald-800/50">
            <CheckCircle className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sincronizado</span>
          </span>
        );
      case 'Sincronizando':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-brand-950/70 text-brand-400 border border-brand-800/50 animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span className="hidden sm:inline">Sincronizando</span>
          </span>
        );
      case 'Conflicto':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-amber-950/70 text-amber-400 border border-amber-800/50">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Conflicto (409)</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-slate-800 text-slate-300">
            {isOnline ? <Cloud className="w-3.5 h-3.5" /> : <CloudOff className="w-3.5 h-3.5 text-amber-400" />}
            <span className="hidden sm:inline">{syncStatus}</span>
          </span>
        );
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full bg-slate-950/90 backdrop-blur-md border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div 
          onClick={() => onNavigate('marketplace')}
          className="flex items-center gap-2 cursor-pointer select-none group min-h-touch"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-brand-500/25 group-hover:scale-105 transition-transform">
            <Flame className="w-6 h-6 text-white" />
          </div>
          <div>
            <span className="text-xl font-extrabold tracking-tight text-white flex items-center gap-1">
              NEXORA
              <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-300 border border-brand-500/30">
                MVP FASE 1
              </span>
            </span>
          </div>
        </div>

        {/* Desktop Navigation Links (> 1024px) */}
        <nav className="hidden lg:flex items-center gap-1">
          <button
            onClick={() => onNavigate('marketplace')}
            className={`px-4 py-2 rounded-lg text-sm font-medium min-h-touch transition-colors ${
              currentView === 'marketplace' ? 'bg-brand-600 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Marketplace
          </button>
          <button
            onClick={() => onNavigate('create_campaign')}
            className={`px-4 py-2 rounded-lg text-sm font-medium min-h-touch transition-colors ${
              currentView === 'create_campaign' ? 'bg-brand-600 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Crear Campaña
          </button>
          <button
            onClick={() => onNavigate('collaboration')}
            className={`px-4 py-2 rounded-lg text-sm font-medium min-h-touch transition-colors ${
              currentView === 'collaboration' ? 'bg-brand-600 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Espacio de Colaboración
          </button>
          <button
            onClick={() => onNavigate('mediakit')}
            className={`px-4 py-2 rounded-lg text-sm font-medium min-h-touch transition-colors ${
              currentView === 'mediakit' ? 'bg-brand-600 text-white' : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Media Kit Dinámico
          </button>
        </nav>

        {/* Right side status & user badge */}
        <div className="flex items-center gap-3">
          <div onClick={triggerSync} className="cursor-pointer" title="Estado de sincronización">
            {getSyncBadge()}
          </div>

          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              <button
                onClick={() => onNavigate('mediakit')}
                className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 text-xs font-medium hover:border-brand-500/50 transition-colors min-h-touch"
              >
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span>{user?.profile?.display_name || user?.email?.split('@')[0]}</span>
                <span className="text-[10px] text-slate-400 uppercase font-semibold">({user?.role})</span>
              </button>
              <button
                onClick={logout}
                title="Cerrar Sesión (RNF-21 purga caché)"
                className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/20 transition-colors min-h-touch min-w-touch flex items-center justify-center"
                aria-label="Cerrar sesión"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => onNavigate('auth')}
              className="bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold px-4 py-2.5 rounded-lg min-h-touch shadow-md shadow-brand-500/25 transition-all"
            >
              Iniciar Sesión
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
