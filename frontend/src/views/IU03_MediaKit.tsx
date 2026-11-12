import React, { useState, useEffect } from 'react';
import { MediaKitData } from '../types';
import { api } from '../services/api';
import { indexDB } from '../db/indexdb';
import { useAuth } from '../context/AuthContext';
import { useOfflineSync } from '../context/OfflineSyncContext';
import { KPICard } from '../components/mediakit/KPICard';
import { Star, MapPin, Globe, ShieldCheck, Award, ExternalLink, MessageCircle, AlertCircle, Lock, Trash2 } from 'lucide-react';

interface IU03MediaKitProps {
  creatorId?: string;
  onContactOrInvite?: () => void;
}

export const IU03_MediaKit: React.FC<IU03MediaKitProps> = ({
  creatorId,
  onContactOrInvite
}) => {
  const { user, logout } = useAuth();
  const { isOnline } = useOfflineSync();
  const [mediaKit, setMediaKit] = useState<MediaKitData | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);

  useEffect(() => {
    loadMediaKit();
  }, [creatorId, isOnline, user?.id]);

  const loadMediaKit = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      let targetId = creatorId;
      if (!targetId) {
        if (user?.id) {
          targetId = user.id;
        } else {
          const { data: me } = await api.request<any>('/users/me');
          targetId = me.id;
        }
      }

      if (!targetId) {
        setErrorMsg('No se especificó un creador para visualizar el Media Kit.');
        return;
      }

      // H13: Only cache and read offline Media Kit for the authenticated creator's own profile (privacy protection)
      const isOwnMediaKit = Boolean(user?.id && targetId === user.id);

      if (!isOnline) {
        if (isOwnMediaKit) {
          const cached = await indexDB.getMediaKit(targetId);
          if (cached) {
            setMediaKit(cached);
            return;
          }
        }
        setErrorMsg('Sin conexión a internet. Por privacidad, solo el Media Kit propio se almacena en caché local.');
        return;
      }

      // Fetch live dynamic media kit
      const { data } = await api.request<MediaKitData>(`/users/${targetId}/media-kit`);
      setMediaKit(data);

      // Cache locally into IndexedDB strictly for own Media Kit
      if (isOwnMediaKit) {
        await indexDB.saveMediaKit(data);
      }
    } catch (e: any) {
      console.error('Error fetching media kit:', e);
      setErrorMsg(e?.message || 'No fue posible cargar el Media Kit desde el servidor.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePrivacyAccount = async () => {
    setDeletingAccount(true);
    setErrorMsg(null);
    try {
      await api.request('/users/me/privacy/delete-request', {
        method: 'POST',
        body: { notes: 'Solicitud de eliminación / anonimización de datos personales (Habeas Data RNF-12).' }
      });
      await logout();
    } catch (e: any) {
      setErrorMsg(e?.message || 'No se pudo procesar la solicitud de eliminación.');
      setDeletingAccount(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-4 sm:p-6 lg:p-8 animate-pulse">
        <div className="h-48 bg-slate-900 rounded-3xl mb-6"></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-slate-900 rounded-2xl"></div>
          ))}
        </div>
      </div>
    );
  }

  if (errorMsg || !mediaKit) {
    return (
      <div className="max-w-3xl mx-auto p-6 mt-8 bg-slate-900 border border-slate-800 rounded-3xl text-center">
        <AlertCircle className="w-10 h-10 text-amber-400 mx-auto mb-3" />
        <p className="text-sm font-bold text-white">{errorMsg || 'Media Kit no disponible.'}</p>
      </div>
    );
  }

  const isOwnMediaKit = Boolean(user?.id && mediaKit.creator_id === user.id);
  const primaryMetric = mediaKit.connected_metrics[0];
  const declaredFollowers = mediaKit.declared_metrics?.[0]?.seguidores_estimados;
  const isOfficialApi = Boolean(
    primaryMetric &&
    primaryMetric.estado === 'CONECTADO_API' &&
    !primaryMetric.fuente_origen.toUpperCase().includes('DEMO') &&
    !primaryMetric.fuente_origen.toUpperCase().includes('SIMULADO')
  );
  const metricSourceType = isOfficialApi ? 'API_CONECTADA' : 'DEMO_SIMULADO';

  return (
    <div className="max-w-6xl mx-auto p-4 sm:px-6 lg:px-8 py-6 pb-28 lg:pb-12 text-slate-100">
      {/* Header Profile Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden mb-6">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-5">
          <img
            src={mediaKit.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80'}
            alt={mediaKit.display_name}
            className="w-24 h-24 sm:w-28 sm:h-28 rounded-3xl object-cover border-4 border-brand-500/40 shadow-xl shrink-0"
          />

          <div className="flex-1 text-center sm:text-left min-w-0">
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mb-1">
              <h1 className="text-xl sm:text-2xl font-black text-white">
                {mediaKit.display_name}
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-brand-500/20 text-brand-300 border border-brand-500/30">
                Media Kit v{mediaKit.version}
              </span>
              {mediaKit.creator_tier && (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-200 border border-slate-700">
                  Nivel {mediaKit.creator_tier}
                </span>
              )}
              {mediaKit.nexora_premium_eligible && (
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  NEXORA Premium
                </span>
              )}
            </div>

            <p className="text-xs sm:text-sm text-slate-300 max-w-2xl mt-1">
              {mediaKit.bio}
            </p>

            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3 mt-3 text-xs text-slate-400">
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-brand-400" />
                <span>{mediaKit.location_declared}</span>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Globe className="w-3.5 h-3.5 text-slate-400" />
                <span>{mediaKit.languages}</span>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-amber-400 font-bold">
                <Star className="w-3.5 h-3.5 fill-amber-400" />
                <span>{mediaKit.average_rating.toFixed(1)}</span>
                <span className="text-slate-400 font-normal">({mediaKit.verified_reviews_count} reseñas bilaterales RN-05)</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid (Mobile-First: 1 col on mobile, 2 on tablet, 4 on desktop) */}
      <div className="mb-6">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>
            {isOfficialApi
              ? 'Métricas Conectadas & Verificadas (RN-03 Trazabilidad)'
              : 'Métricas en Modo DEMO / Simulado & Declaradas (RN-03 Trazabilidad)'}
          </span>
        </h2>

        {mediaKit.metrics_restricted ? (
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
            <Lock className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-white mb-1">Métricas detalladas protegidas por control de acceso</p>
              <p className="text-slate-400">
                Por política de privacidad de Nexora (Guía 03), los snapshots de audiencia y métricas detalladas solo son visibles para el creador propietario y administradores autorizados.
              </p>
            </div>
          </div>
        ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {primaryMetric ? (
            <>
              <KPICard
                label={isOfficialApi ? 'Seguidores Oficiales' : 'Seguidores (Demo)'}
                value={primaryMetric.followers_count.toLocaleString()}
                subtitle={isOfficialApi ? `${primaryMetric.plataforma} API` : `${primaryMetric.plataforma} (Simulado)`}
                sourceType={metricSourceType}
                captureDateUtc={primaryMetric.fecha_captura_utc}
                period={primaryMetric.periodo}
              />
              <KPICard
                label="Tasa de Engagement"
                value={`${primaryMetric.engagement.calculated_percentage}%`}
                subtitle={isOfficialApi ? 'High Affinity' : 'Estimación Demo'}
                sourceType={metricSourceType}
                captureDateUtc={primaryMetric.fecha_captura_utc}
                period={primaryMetric.periodo}
                formulaDetails={{
                  interactions: primaryMetric.engagement.interactions,
                  reach: primaryMetric.engagement.reach_or_impressions,
                  formula: primaryMetric.engagement.formula_string
                }}
              />
              <KPICard
                label="Impresiones Promedio"
                value={primaryMetric.avg_impressions.toLocaleString()}
                subtitle="Por publicación"
                sourceType={metricSourceType}
                captureDateUtc={primaryMetric.fecha_captura_utc}
                period={primaryMetric.periodo}
              />
              <KPICard
                label="Reproducciones Video"
                value={(primaryMetric.avg_video_views || 0).toLocaleString()}
                subtitle="Reels & Stories"
                sourceType={metricSourceType}
                captureDateUtc={primaryMetric.fecha_captura_utc}
                period={primaryMetric.periodo}
              />
            </>
          ) : declaredFollowers ? (
            <KPICard
              label="Audiencia Declarada"
              value={Number(declaredFollowers).toLocaleString()}
              subtitle="Estimación del creador"
              sourceType="DECLARADO"
              period="Declaración manual"
            />
          ) : (
            <div className="sm:col-span-2 lg:col-span-4 p-4 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
              Aún no hay snapshots conectados ni seguidores declarados registrados en este Media Kit.
            </div>
          )}
        </div>
        )}

        {/* Authenticity Legal & Technical Notice (RN-03) */}
        <div className="mt-3 p-3 rounded-2xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-brand-400 shrink-0" />
          <span>
            {primaryMetric?.authenticity_notice ||
              'Dato declarado manualmente o en modo DEMO. Nexora no certifica audiencia 100% auténtica según RN-03.'}
          </span>
        </div>
      </div>

      {/* Content Samples / Portfolio */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl mb-6">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
          <Award className="w-4 h-4 text-brand-400" />
          <span>Muestras de Contenido y Portafolio Aprobado</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {mediaKit.portfolio_samples && mediaKit.portfolio_samples.map((sample, idx) => (
            <div
              key={idx}
              className="p-4 rounded-2xl bg-slate-950 border border-slate-800/80 flex items-center justify-between hover:border-brand-500/40 transition-colors"
            >
              <div>
                <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-brand-500/15 text-brand-300 border border-brand-500/30">
                  {sample.format}
                </span>
                <h4 className="text-xs sm:text-sm font-bold text-white mt-1.5">{sample.title}</h4>
                <span className="text-[11px] text-slate-400">{sample.views ? `${Number(sample.views).toLocaleString()} reproducciones` : 'Publicación autorizada'}</span>
              </div>
              <a
                href={sample.url}
                target="_blank"
                rel="noreferrer"
                className="p-3 bg-slate-900 hover:bg-brand-600 text-slate-300 hover:text-white rounded-xl min-h-touch min-w-touch flex items-center justify-center transition-colors"
                aria-label="Ver muestra externa"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          ))}
        </div>
      </div>

      {isOwnMediaKit && (
        <div className="bg-slate-900 border border-rose-900/50 rounded-3xl p-6 shadow-xl mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-rose-300 flex items-center gap-2">
                <Trash2 className="w-4 h-4" />
                <span>Privacidad y Habeas Data (RNF-12)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Puedes solicitar la eliminación y anonimización irreversible de tu cuenta, perfil y consentimientos OAuth activos.
              </p>
            </div>
            {!showDeleteConfirm ? (
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                className="px-4 py-2.5 bg-rose-950 hover:bg-rose-900 text-rose-200 border border-rose-800 rounded-xl text-xs font-bold min-h-touch shrink-0"
              >
                Solicitar Baja / Anonimización
              </button>
            ) : (
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deletingAccount}
                  className="px-3 py-2 bg-slate-800 text-slate-300 rounded-xl text-xs font-semibold min-h-touch"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleDeletePrivacyAccount}
                  disabled={deletingAccount}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-bold min-h-touch"
                >
                  {deletingAccount ? 'Procesando...' : 'Confirmar Anonimización'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Floating Bottom Action CTA for Mobile (< 768px) and Inline on Desktop */}
      <div className="fixed lg:static bottom-14 left-0 right-0 p-4 bg-slate-950/95 lg:bg-transparent backdrop-blur-lg lg:backdrop-blur-none border-t border-slate-800 lg:border-t-0 z-30">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          <div className="hidden lg:block text-xs text-slate-400">
            ¿Interesado en colaborar con este creador? Envía una invitación directa o vincula a una campaña activa.
          </div>
          <button
            onClick={onContactOrInvite}
            className="w-full lg:w-auto px-8 py-4 bg-brand-600 hover:bg-brand-500 text-white font-extrabold text-sm rounded-2xl min-h-touch flex items-center justify-center gap-2 shadow-xl shadow-brand-500/25 transition-all active:scale-95"
          >
            <MessageCircle className="w-5 h-5" />
            <span>Invitar a Campaña / Contactar</span>
          </button>
        </div>
      </div>
    </div>
  );
};
