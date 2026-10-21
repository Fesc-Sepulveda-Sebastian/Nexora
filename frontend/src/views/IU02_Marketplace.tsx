import React, { useState, useEffect } from 'react';
import { CreatorRecommendation, Campaign } from '../types';
import { api } from '../services/api';
import { indexDB } from '../db/indexdb';
import { useOfflineSync } from '../context/OfflineSyncContext';
import { CreatorCard } from '../components/marketplace/CreatorCard';
import { CampaignCard } from '../components/marketplace/CampaignCard';
import { BottomSheetFilters } from '../components/marketplace/BottomSheetFilters';
import { Search, SlidersHorizontal, Sparkles, Users, Megaphone, ToggleLeft, ToggleRight } from 'lucide-react';

interface IU02MarketplaceProps {
  onSelectCreator: (creatorId: string) => void;
  onSelectCampaign: (campaignId: string) => void;
}

export const IU02_Marketplace: React.FC<IU02MarketplaceProps> = ({
  onSelectCreator,
  onSelectCampaign
}) => {
  const { isOnline } = useOfflineSync();
  const [activeTab, setActiveTab] = useState<'creators' | 'campaigns'>('creators');
  const [searchTerm, setSearchTerm] = useState('');
  const [personalizationActive, setPersonalizationActive] = useState(true);
  const [isBottomSheetOpen, setIsBottomSheetOpen] = useState(false);

  // Filters State
  const [filters, setFilters] = useState({
    niche: '',
    location: '',
    platform: '',
    minFollowers: 1000
  });

  // Data States
  const [creators, setCreators] = useState<CreatorRecommendation[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [activeTab, personalizationActive, filters.niche, isOnline]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'creators') {
        if (!isOnline) {
          // Offline fallback
          setCreators([
            {
              creator_id: 'sofia_cucuta',
              display_name: 'Sofía Castro | Foodie Cúcuta (Caché)',
              niche: 'Gastronomía',
              location_declared: 'Cúcuta, Colombia',
              average_rating: 5.0,
              total_score: 92.0,
              matching_criteria: [{ criterion: 'nicho', detail: 'Coincide por: Nicho Gastronomía', weight_score: 35 }],
              rule_version: 'recommender-v1.2'
            }
          ]);
          setLoading(false);
          return;
        }

        // Fetch campaigns to recommend creators for first campaign
        const campRes = await api.request<any>('/campaigns?limit=1');
        const firstCampId = campRes.data.items?.[0]?.id;

        if (firstCampId) {
          const { data } = await api.request<any>(
            `/recommendations/campaigns/${firstCampId}/creators?personalization=${personalizationActive}`
          );
          setCreators(data.items || []);
        }
      } else {
        // Fetch campaigns
        if (!isOnline) {
          const cached = await indexDB.getRecentCampaigns();
          setCampaigns(cached as any);
          setLoading(false);
          return;
        }

        let url = `/campaigns?status_filter=Publicada`;
        if (filters.niche) url += `&niche=${encodeURIComponent(filters.niche)}`;

        const { data } = await api.request<any>(url);
        const fetchedCampaigns = data.items || [];
        setCampaigns(fetchedCampaigns);

        // Cache first 50 campaigns into IndexedDB for offline resilience (RNF-02)
        fetchedCampaigns.slice(0, 50).forEach((c: Campaign) => {
          indexDB.saveRecentCampaign({
            id: c.id,
            title: c.title,
            objective: c.objective,
            niche: c.niche,
            budget: c.budget,
            compensation_type: c.compensation_type,
            status: c.status,
            version_id: c.version_id,
            cached_at: new Date().toISOString()
          });
        });
      }
    } catch (e) {
      console.error('Error fetching marketplace data:', e);
    } finally {
      setLoading(false);
    }
  };

  // Filtered views
  const filteredCreators = creators.filter((c) => {
    const matchesSearch = c.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.niche.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesNiche = !filters.niche || c.niche.toLowerCase().includes(filters.niche.toLowerCase());
    const matchesLoc = !filters.location || c.location_declared.toLowerCase().includes(filters.location.toLowerCase());
    return matchesSearch && matchesNiche && matchesLoc;
  });

  const filteredCampaigns = campaigns.filter((c) => {
    const matchesSearch = c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          c.niche.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesNiche = !filters.niche || c.niche.toLowerCase().includes(filters.niche.toLowerCase());
    return matchesSearch && matchesNiche;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-24 lg:pb-12">
      {/* Top Banner / Hero */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/60 p-6 rounded-3xl border border-slate-800 shadow-xl">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-brand-400 bg-brand-500/10 px-2.5 py-1 rounded-full border border-brand-500/20">
            Marketplace Transparente & Trazable
          </span>
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-black text-white mt-2">
            Descubre Creadores y Campañas Verificadas
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-xl">
            Priorizando nano y micro influenciadores con métricas oficiales de API social y sin intermediarios fragmentados.
          </p>
        </div>

        {/* Explainable Recommender Toggle (RF-26) */}
        <div className="flex items-center gap-3 bg-slate-950/80 p-3 rounded-2xl border border-slate-800 shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <div className="text-left">
              <span className="text-xs font-bold text-white block">Recomendaciones IA</span>
              <span className="text-[10px] text-slate-400 block">Motor explicable (RF-26)</span>
            </div>
          </div>
          <button
            onClick={() => setPersonalizationActive(!personalizationActive)}
            className="text-brand-400 hover:text-brand-300 min-h-touch min-w-touch flex items-center justify-center"
            title="Activar o desactivar personalización algorítmica"
            aria-label="Alternar motor de recomendaciones"
          >
            {personalizationActive ? (
              <ToggleRight className="w-8 h-8 text-brand-500" />
            ) : (
              <ToggleLeft className="w-8 h-8 text-slate-600" />
            )}
          </button>
        </div>
      </div>

      {/* Tabs Switcher: Creators vs Campaigns */}
      <div className="flex items-center justify-between gap-3 mb-6">
        <div className="flex gap-2 p-1 bg-slate-900 rounded-2xl border border-slate-800">
          <button
            onClick={() => setActiveTab('creators')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold min-h-touch transition-all ${
              activeTab === 'creators'
                ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Creadores ({filteredCreators.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('campaigns')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold min-h-touch transition-all ${
              activeTab === 'campaigns'
                ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Megaphone className="w-4 h-4" />
            <span>Campañas Activas ({filteredCampaigns.length})</span>
          </button>
        </div>

        {/* Mobile Filter Button (Triggers Bottom Sheet) */}
        <button
          onClick={() => setIsBottomSheetOpen(true)}
          className="lg:hidden flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 text-xs font-semibold hover:border-brand-500 min-h-touch min-w-touch"
          aria-label="Abrir filtros"
        >
          <SlidersHorizontal className="w-4 h-4 text-brand-400" />
          <span className="hidden sm:inline">Filtros</span>
        </button>
      </div>

      {/* Main Grid Layout: Sidebar on Desktop + Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Desktop Sidebar Filters (25% width fixed) */}
        <aside className="hidden lg:block lg:col-span-1 bg-slate-900/90 border border-slate-800 rounded-3xl p-5 h-fit sticky top-24 shadow-xl">
          <div className="flex items-center gap-2 text-brand-400 font-bold text-sm pb-3 border-b border-slate-800 mb-4">
            <SlidersHorizontal className="w-4 h-4" />
            <span>Filtros Avanzados</span>
          </div>

          <div className="space-y-4 text-xs">
            {/* Search Input */}
            <div>
              <label className="text-[11px] font-semibold text-slate-400 uppercase block mb-1">
                Búsqueda Rápida
              </label>
              <div className="relative">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Buscar nombre o nicho..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
                />
              </div>
            </div>

            {/* Niche */}
            <div>
              <label className="text-[11px] font-semibold text-slate-400 uppercase block mb-1">
                Nicho / Categoría
              </label>
              <select
                value={filters.niche}
                onChange={(e) => setFilters({ ...filters, niche: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
              >
                <option value="">Todos los nichos</option>
                <option value="Gastronomía">Gastronomía</option>
                <option value="Fitness & Salud">Fitness & Salud</option>
                <option value="Moda & Belleza">Moda & Belleza</option>
                <option value="Tecnología">Tecnología</option>
                <option value="Turismo">Turismo</option>
              </select>
            </div>

            {/* Location */}
            <div>
              <label className="text-[11px] font-semibold text-slate-400 uppercase block mb-1">
                Ubicación Declarada
              </label>
              <select
                value={filters.location}
                onChange={(e) => setFilters({ ...filters, location: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
              >
                <option value="">Todas las ciudades</option>
                <option value="Cúcuta">Cúcuta, Colombia</option>
                <option value="Bucaramanga">Bucaramanga, Colombia</option>
                <option value="Bogotá">Bogotá, Colombia</option>
              </select>
            </div>

            <button
              onClick={() => {
                setFilters({ niche: '', location: '', platform: '', minFollowers: 1000 });
                setSearchTerm('');
              }}
              className="w-full mt-2 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium text-xs min-h-touch transition-colors"
            >
              Restablecer Filtros
            </button>
          </div>
        </aside>

        {/* Content Column: 3 cols on Desktop, 2 on Tablet, 1 on Mobile */}
        <main className="lg:col-span-3">
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="h-48 bg-slate-900/60 rounded-2xl animate-pulse border border-slate-800/80" />
              ))}
            </div>
          ) : activeTab === 'creators' ? (
            filteredCreators.length === 0 ? (
              <div className="text-center py-16 bg-slate-900/50 rounded-3xl border border-slate-800">
                <Users className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-300 font-bold text-sm">No se encontraron creadores con los filtros seleccionados.</p>
                <p className="text-slate-500 text-xs mt-1">Intenta ampliar los criterios o restablecer los filtros.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {filteredCreators.map((creator) => (
                  <CreatorCard
                    key={creator.creator_id}
                    creator={creator}
                    onSelect={onSelectCreator}
                  />
                ))}
              </div>
            )
          ) : (
            filteredCampaigns.length === 0 ? (
              <div className="text-center py-16 bg-slate-900/50 rounded-3xl border border-slate-800">
                <Megaphone className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-300 font-bold text-sm">No hay campañas activas en este nicho.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {filteredCampaigns.map((camp) => (
                  <CampaignCard
                    key={camp.id}
                    campaign={camp}
                    onSelect={onSelectCampaign}
                  />
                ))}
              </div>
            )
          )}
        </main>
      </div>

      {/* Mobile Bottom Sheet Filters */}
      <BottomSheetFilters
        isOpen={isBottomSheetOpen}
        onClose={() => setIsBottomSheetOpen(false)}
        filters={filters}
        onChange={setFilters}
        onApply={loadData}
        totalResultsCount={activeTab === 'creators' ? filteredCreators.length : filteredCampaigns.length}
      />
    </div>
  );
};
