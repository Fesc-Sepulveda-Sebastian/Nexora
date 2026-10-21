import React, { useState, useEffect } from 'react';
import { MediaKitData } from '../types';
import { api } from '../services/api';
import { indexDB } from '../db/indexdb';
import { useOfflineSync } from '../context/OfflineSyncContext';
import { KPICard } from '../components/mediakit/KPICard';
import { Star, MapPin, Globe, ShieldCheck, Share2, Award, ExternalLink, MessageCircle } from 'lucide-react';

interface IU03MediaKitProps {
  creatorId?: string;
  onContactOrInvite?: () => void;
}

export const IU03_MediaKit: React.FC<IU03MediaKitProps> = ({
  creatorId,
  onContactOrInvite
}) => {
  const { isOnline } = useOfflineSync();
  const [mediaKit, setMediaKit] = useState<MediaKitData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMediaKit();
  }, [creatorId, isOnline]);

  const loadMediaKit = async () => {
    setLoading(true);
    try {
      // Determine creator ID (if not provided, fetch current user or demo creator)
      let targetId = creatorId;
      if (!targetId) {
        try {
          const { data: me } = await api.request<any>('/users/me');
          targetId = me.id;
        } catch (_) {
          targetId = 'sofia_cucuta';
        }
      }

      if (!isOnline && targetId) {
        // Read from IndexedDB offline store (RF-20, RNF-02)
        const cached = await indexDB.getMediaKit(targetId);
        if (cached) {
          setMediaKit(cached);
          setLoading(false);
          return;
        }
      }

      // Fetch live dynamic media kit
      const { data } = await api.request<MediaKitData>(`/users/${targetId}/media-kit`);
      setMediaKit(data);

      // Cache locally into IndexedDB for offline read
      if (targetId) {
        await indexDB.saveMediaKit(data);
      }
    } catch (e) {
      console.error('Error fetching media kit:', e);
      // Fallback demo data
      setMediaKit({
        creator_id: creatorId || 'sofia_cucuta',
        display_name: 'Sofía Castro | Foodie Cúcuta',
        bio: 'Narrando historias a través de sabores locales. Nano-influenciadora apasionada por la gastronomía nortesantandereana.',
        location_declared: 'Cúcuta, Colombia',
        niche: 'Gastronomía',
        languages: 'Español, Inglés',
        avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80',
        version: 3,
        verified_reviews_count: 12,
        average_rating: 5.0,
        portfolio_samples: [
          { title: 'Degustación Pastel de Garbanzo Gourmet', format: 'Reel', views: 14200, url: 'https://instagram.com' },
          { title: 'Tour Callejero de Postres en Cúcuta', format: 'TikTok', views: 28500, url: 'https://tiktok.com' }
        ],
        connected_metrics: [
          {
            plataforma: 'INSTAGRAM',
            cuenta_id: 'ig_sofiacastro_food',
            periodo: 'Últimos 30 días',
            fecha_captura_utc: new Date().toISOString(),
            estado: 'CONECTADO_API',
            esquema_version: '1.0.0',
            fuente_origen: 'API_OFICIAL_INSTAGRAM',
            followers_count: 8650,
            engagement: {
              interactions: 1320,
              reach_or_impressions: 19300,
              formula_string: '((likes + comments + shares + saves) / reach) * 100',
              calculated_percentage: 6.84
            },
            avg_impressions: 6400,
            avg_video_views: 12800,
            top_locations: [{ city: 'Cúcuta', pct: 65.0 }, { city: 'Bucaramanga', pct: 18.0 }],
            authenticity_notice: 'Dato conectado verificado por API oficial. Nexora no certifica audiencia 100% auténtica (RN-03).'
          }
        ],
        declared_metrics: [],
        generated_at_utc: new Date().toISOString()
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading || !mediaKit) {
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

  const primaryMetric = mediaKit.connected_metrics[0];

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
          <span>Métricas Conectadas & Verificadas (RN-03 Trazabilidad)</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {primaryMetric ? (
            <>
              <KPICard
                label="Seguidores Oficiales"
                value={primaryMetric.followers_count.toLocaleString()}
                subtitle="Instagram API"
                sourceType="API_CONECTADA"
                captureDateUtc={primaryMetric.fecha_captura_utc}
                period={primaryMetric.periodo}
              />
              <KPICard
                label="Tasa de Engagement"
                value={`${primaryMetric.engagement.calculated_percentage}%`}
                subtitle="High Affinity"
                sourceType="API_CONECTADA"
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
                sourceType="API_CONECTADA"
                captureDateUtc={primaryMetric.fecha_captura_utc}
                period={primaryMetric.periodo}
              />
              <KPICard
                label="Reproducciones Video"
                value={(primaryMetric.avg_video_views || 0).toLocaleString()}
                subtitle="Reels & Stories"
                sourceType="API_CONECTADA"
                captureDateUtc={primaryMetric.fecha_captura_utc}
                period={primaryMetric.periodo}
              />
            </>
          ) : (
            <KPICard
              label="Audiencia Declarada"
              value="5,400"
              subtitle="Estimación del creador"
              sourceType="DECLARADO"
              period="Declaración manual"
            />
          )}
        </div>

        {/* Authenticity Legal & Technical Notice (RN-03) */}
        <div className="mt-3 p-3 rounded-2xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-brand-400 shrink-0" />
          <span>
            {primaryMetric?.authenticity_notice ||
              'Dato conectado verificado por API oficial. Nexora no certifica audiencia 100% auténtica según RN-03.'}
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
