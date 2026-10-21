import React, { useState, useEffect } from 'react';
import { Campaign, Application } from '../types';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useOfflineSync } from '../context/OfflineSyncContext';
import { DollarSign, Calendar, Package, MapPin, Send, AlertCircle, CheckCircle2, ShieldCheck, ArrowLeft } from 'lucide-react';

interface IU05CampaignDetailProps {
  campaignId: string;
  onBack: () => void;
  onApplicationSuccess: (application: Application) => void;
}

export const IU05_CampaignDetail: React.FC<IU05CampaignDetailProps> = ({
  campaignId,
  onBack,
  onApplicationSuccess
}) => {
  const { user, isAuthenticated } = useAuth();
  const { isOnline } = useOfflineSync();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [proposal, setProposal] = useState('');
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    api.request<Campaign>(`/campaigns/${campaignId}`)
      .then(({ data }) => setCampaign(data))
      .catch((e) => setErrorMsg(e.message || 'Error al cargar detalles de campaña'))
      .finally(() => setLoading(false));
  }, [campaignId]);

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated) {
      setErrorMsg('Debes iniciar sesión con tu cuenta de Creador para postularte.');
      return;
    }

    if (!isOnline) {
      setErrorMsg('RN-02: La confirmación de postulación solo se procesa en línea contra el servidor.');
      return;
    }

    if (proposal.trim().length < 15) {
      setErrorMsg('La propuesta creativa debe contener al menos 15 caracteres.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    // Generate unique Idempotency Key (RN-02, RNF-10)
    const idempotencyKey = `apply-${campaignId}-${user?.id}-${Date.now()}`;

    try {
      const { data } = await api.request<Application>(`/campaigns/${campaignId}/apply`, {
        method: 'POST',
        body: {
          creative_proposal: proposal,
          media_kit_snapshot_version: user?.profile?.current_media_kit_version || 1
        },
        idempotencyKey
      });

      setSuccessMsg('¡Postulación enviada exitosamente a la marca! Se ha congelado la versión de tu Media Kit.');
      onApplicationSuccess(data);
    } catch (e: any) {
      setErrorMsg(e.message || 'Error al enviar postulación');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading || !campaign) {
    return (
      <div className="max-w-4xl mx-auto p-6 animate-pulse">
        <div className="h-40 bg-slate-900 rounded-3xl mb-4"></div>
        <div className="h-60 bg-slate-900 rounded-3xl"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-28 lg:pb-12 text-slate-100">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-xs font-bold text-slate-400 hover:text-white mb-4 min-h-touch min-w-touch"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Volver al Marketplace</span>
      </button>

      {/* Campaign Details Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl mb-6">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <span className="text-[11px] font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-brand-500/15 text-brand-300 border border-brand-500/30">
            {campaign.niche}
          </span>
          <span className="text-xs font-semibold text-emerald-400 bg-emerald-950/70 border border-emerald-800/40 px-3 py-1 rounded-full">
            {campaign.status}
          </span>
        </div>

        <h1 className="text-xl sm:text-3xl font-black text-white">{campaign.title}</h1>
        <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">{campaign.objective}</p>

        {/* Highlights: Budget, Dates, Deliverables */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-6">
          <div className="p-3.5 bg-slate-950 rounded-2xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Compensación</span>
            <span className="text-base font-extrabold text-white flex items-center gap-1 mt-0.5">
              <DollarSign className="w-4 h-4 text-emerald-400" />
              {campaign.compensation_type === 'canje' ? 'Canje VIP' : `$${Number(campaign.budget).toLocaleString()} COP`}
            </span>
          </div>

          <div className="p-3.5 bg-slate-950 rounded-2xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Vigencia</span>
            <span className="text-xs font-bold text-white flex items-center gap-1 mt-1">
              <Calendar className="w-4 h-4 text-brand-400" />
              <span>{campaign.end_date ? new Date(campaign.end_date).toLocaleDateString() : 'A convenir'}</span>
            </span>
          </div>

          <div className="p-3.5 bg-slate-950 rounded-2xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Ubicación Requerida</span>
            <span className="text-xs font-bold text-white flex items-center gap-1 mt-1">
              <MapPin className="w-4 h-4 text-amber-400" />
              <span>{campaign.selection_criteria?.location || 'Cúcuta, Colombia'}</span>
            </span>
          </div>
        </div>

        {/* Deliverables details */}
        <div>
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
            <Package className="w-4 h-4 text-brand-400" />
            <span>Entregables Solicitados</span>
          </h2>
          <div className="space-y-2">
            {campaign.deliverables && campaign.deliverables.map((deliv, idx) => (
              <div key={idx} className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl flex items-center justify-between text-xs">
                <div>
                  <span className="font-bold text-white">{deliv.qty}x {deliv.format}</span>
                  <p className="text-slate-400 text-[11px] mt-0.5">{deliv.specs}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Application Form for Creators */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
        <h2 className="text-base sm:text-lg font-bold text-white mb-2 flex items-center gap-2">
          <Send className="w-5 h-5 text-brand-400" />
          <span>Postularme a esta Campaña (RF-10)</span>
        </h2>
        <p className="text-xs text-slate-400 mb-4">
          Al postularte, se congelará la instantánea de tu Media Kit actual (v{user?.profile?.current_media_kit_version || 1}) para evaluación transparente de la marca.
        </p>

        {errorMsg && (
          <div role="alert" className="p-3 mb-4 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3 mb-4 rounded-xl bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleApply} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 uppercase block mb-1">
              Propuesta Creativa y Enfoque de Contenido *
            </label>
            <textarea
              rows={4}
              required
              minLength={15}
              value={proposal}
              onChange={(e) => setProposal(e.target.value)}
              placeholder="Explica cómo abordarás la campaña, qué elementos visuales destacarás y cómo conectarás con tu audiencia local..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-xs text-white focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* Frozen Media Kit Snapshot Notice */}
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-[11px] text-slate-400 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              Se adjuntará automáticamente tu Media Kit con métricas verificadas de API oficial (RN-03).
            </span>
          </div>

          {/* Sticky CTA on Mobile (< 768px), Standard on Desktop */}
          <div className="fixed lg:static bottom-14 left-0 right-0 p-4 bg-slate-950/95 lg:bg-transparent backdrop-blur-lg lg:backdrop-blur-none border-t border-slate-800 lg:border-t-0 z-30">
            <button
              type="submit"
              disabled={isSubmitting || !isOnline}
              className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-extrabold text-sm py-4 rounded-2xl min-h-touch flex items-center justify-center gap-2 shadow-xl shadow-brand-500/25 transition-all active:scale-95"
            >
              <Send className="w-5 h-5" />
              <span>{isSubmitting ? 'Enviando...' : 'Revisar y Enviar Postulación (RN-02)'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
