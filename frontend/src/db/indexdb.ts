/**
 * IndexedDB Controlled Local Storage Layer for Nexora Mobile-First PWA.
 * Strictly adheres to RNF-02, RNF-13, and RNF-21:
 * - Stores ONLY: own Media Kit, up to 50 recent campaigns, non-sensitive preferences,
 *   max 5 local drafts, and outbox queue for pending actions.
 * - NEVER stores passwords, OAuth tokens, credit cards, or raw private evidence.
 * - Provides full cache purge upon logout.
 */

const DB_NAME = 'NexoraOfflineDB';
const DB_VERSION = 1;

export interface OfflineCampaign {
  id: string;
  title: string;
  objective: string;
  niche: string;
  budget: number;
  compensation_type: string;
  status: string;
  version_id: number;
  cached_at: string;
}

export interface OfflineDraft {
  local_id: string;
  title: string;
  objective: string;
  niche: string;
  budget: number;
  compensation_type: string;
  deliverables: any[];
  selection_criteria: any;
  version_id: number;
  sync_status: 'Sincronizado' | 'Pendiente' | 'Sincronizando' | 'Error' | 'Conflicto';
  last_modified: string;
}

export interface OutboxAction {
  id: string;
  action_type: 'SAVE_DRAFT' | 'UPDATE_PROFILE' | 'SYNC_CAMPAIGN';
  endpoint: string;
  payload: any;
  idempotency_key: string;
  created_at: string;
  retry_count: number;
}

class IndexedDBController {
  private dbPromise: Promise<IDBDatabase> | null = null;

  private getDB(): Promise<IDBDatabase> {
    if (this.dbPromise) return this.dbPromise;

    this.dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // 1. Media Kit Store
        if (!db.objectStoreNames.contains('mediakit')) {
          db.createObjectStore('mediakit', { keyPath: 'creator_id' });
        }

        // 2. Recent Campaigns Store (max 50)
        if (!db.objectStoreNames.contains('campaigns')) {
          const campStore = db.createObjectStore('campaigns', { keyPath: 'id' });
          campStore.createIndex('cached_at', 'cached_at', { unique: false });
        }

        // 3. Local Drafts Store (max 5)
        if (!db.objectStoreNames.contains('drafts')) {
          db.createObjectStore('drafts', { keyPath: 'local_id' });
        }

        // 4. Outbox Sync Queue Store
        if (!db.objectStoreNames.contains('outbox')) {
          const outboxStore = db.createObjectStore('outbox', { keyPath: 'id' });
          outboxStore.createIndex('created_at', 'created_at', { unique: false });
        }

        // 5. Non-sensitive Preferences Store
        if (!db.objectStoreNames.contains('preferences')) {
          db.createObjectStore('preferences', { keyPath: 'key' });
        }
      };

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });

    return this.dbPromise;
  }

  // --- CAMPAIGNS (Max 50) ---
  async saveRecentCampaign(campaign: OfflineCampaign): Promise<void> {
    const db = await this.getDB();
    const tx = db.transaction('campaigns', 'readwrite');
    const store = tx.objectStore('campaigns');

    store.put({ ...campaign, cached_at: new Date().toISOString() });

    // Prune to maximum 50 campaigns
    const countReq = store.count();
    countReq.onsuccess = () => {
      if (countReq.result > 50) {
        const index = store.index('cached_at');
        const cursorReq = index.openCursor();
        let deleted = 0;
        cursorReq.onsuccess = (e) => {
          const cursor = (e.target as IDBRequest).result;
          if (cursor && deleted < countReq.result - 50) {
            cursor.delete();
            deleted++;
            cursor.continue();
          }
        };
      }
    };
  }

  async getRecentCampaigns(): Promise<OfflineCampaign[]> {
    const db = await this.getDB();
    return new Promise((resolve) => {
      const tx = db.transaction('campaigns', 'readonly');
      const store = tx.objectStore('campaigns');
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  // --- DRAFTS (Max 5) ---
  async saveLocalDraft(draft: OfflineDraft): Promise<void> {
    const db = await this.getDB();
    const tx = db.transaction('drafts', 'readwrite');
    const store = tx.objectStore('drafts');

    const drafts = await this.getLocalDrafts();
    if (drafts.length >= 5 && !drafts.some(d => d.local_id === draft.local_id)) {
      throw new Error('Límite de 5 borradores locales alcanzado (RNF-02). Elimine o sincronice un borrador existente.');
    }

    store.put({ ...draft, last_modified: new Date().toISOString() });
  }

  async getLocalDrafts(): Promise<OfflineDraft[]> {
    const db = await this.getDB();
    return new Promise((resolve) => {
      const tx = db.transaction('drafts', 'readonly');
      const store = tx.objectStore('drafts');
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  async deleteLocalDraft(local_id: string): Promise<void> {
    const db = await this.getDB();
    const tx = db.transaction('drafts', 'readwrite');
    tx.objectStore('drafts').delete(local_id);
  }

  // --- MEDIA KIT ---
  async saveMediaKit(mediaKit: any): Promise<void> {
    const db = await this.getDB();
    const tx = db.transaction('mediakit', 'readwrite');
    tx.objectStore('mediakit').put(mediaKit);
  }

  async getMediaKit(creator_id: string): Promise<any | null> {
    const db = await this.getDB();
    return new Promise((resolve) => {
      const tx = db.transaction('mediakit', 'readonly');
      const req = tx.objectStore('mediakit').get(creator_id);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => resolve(null);
    });
  }

  // --- OUTBOX QUEUE ---
  async addToOutbox(action: OutboxAction): Promise<void> {
    const db = await this.getDB();
    const tx = db.transaction('outbox', 'readwrite');
    tx.objectStore('outbox').put(action);
  }

  async getOutboxActions(): Promise<OutboxAction[]> {
    const db = await this.getDB();
    return new Promise((resolve) => {
      const tx = db.transaction('outbox', 'readonly');
      const req = tx.objectStore('outbox').getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  async removeOutboxAction(id: string): Promise<void> {
    const db = await this.getDB();
    const tx = db.transaction('outbox', 'readwrite');
    tx.objectStore('outbox').delete(id);
  }

  // --- PURGE ON LOGOUT (RNF-21) ---
  async purgeAllLocalData(): Promise<void> {
    const db = await this.getDB();
    const stores = ['mediakit', 'campaigns', 'drafts', 'outbox', 'preferences'];
    const tx = db.transaction(stores, 'readwrite');
    stores.forEach((s) => tx.objectStore(s).clear());
    console.log('[IndexedDB] All local storage purged for privacy and security (RNF-21).');
  }
}

export const indexDB = new IndexedDBController();
