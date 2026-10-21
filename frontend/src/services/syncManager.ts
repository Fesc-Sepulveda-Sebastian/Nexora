import { indexDB, OutboxAction, OfflineDraft } from '../db/indexdb';
import { api } from './api';

export type SyncState = 'Sincronizado' | 'Pendiente' | 'Sincronizando' | 'Error' | 'Conflicto';

export interface ConflictDetails {
  localDraft: OfflineDraft;
  serverVersion: number;
  serverData: any;
}

type ConflictListener = (conflict: ConflictDetails) => void;
type StatusListener = (status: SyncState) => void;

class SyncManager {
  private isSyncing = false;
  private conflictListeners: ConflictListener[] = [];
  private statusListeners: StatusListener[] = [];
  private currentStatus: SyncState = 'Sincronizado';

  onConflict(listener: ConflictListener) {
    this.conflictListeners.push(listener);
    return () => {
      this.conflictListeners = this.conflictListeners.filter(l => l !== listener);
    };
  }

  onStatusChange(listener: StatusListener) {
    this.statusListeners.push(listener);
    listener(this.currentStatus);
    return () => {
      this.statusListeners = this.statusListeners.filter(l => l !== listener);
    };
  }

  private setStatus(status: SyncState) {
    this.currentStatus = status;
    this.statusListeners.forEach(l => l(status));
  }

  /**
   * Auto-retry with exponential backoff & jitter <= 60s (RNF-10, RNF-19)
   */
  async processOutbox(): Promise<void> {
    if (this.isSyncing || !navigator.onLine) return;
    this.isSyncing = true;
    this.setStatus('Sincronizando');

    try {
      const actions = await indexDB.getOutboxActions();
      for (const action of actions) {
        let success = false;
        let attempt = 0;
        const maxAttempts = 3;

        while (!success && attempt < maxAttempts) {
          try {
            await api.request(action.endpoint, {
              method: 'POST',
              body: action.payload,
              idempotencyKey: action.idempotency_key
            });
            await indexDB.removeOutboxAction(action.id);
            success = true;
          } catch (err: any) {
            attempt++;
            if (err.status === 409) {
              // Version conflict detected (RF-31, RNF-14)
              this.setStatus('Conflicto');
              const localDrafts = await indexDB.getLocalDrafts();
              const match = localDrafts.find(d => d.title === action.payload.title);
              if (match) {
                this.conflictListeners.forEach(l => l({
                  localDraft: match,
                  serverVersion: err.conflictData?.server_version || 2,
                  serverData: err.conflictData?.server_data || {}
                }));
              }
              this.isSyncing = false;
              return;
            }

            // Exponential backoff with jitter: min(60s, (2^attempt * 1000) + jitter)
            const jitter = Math.floor(Math.random() * 500);
            const delay = Math.min(60000, Math.pow(2, attempt) * 1000 + jitter);
            await new Promise(res => setTimeout(res, delay));
          }
        }
      }
      this.setStatus('Sincronizado');
    } catch (e) {
      console.error('[SyncManager] Error syncing outbox:', e);
      this.setStatus('Error');
    } finally {
      this.isSyncing = false;
    }
  }
}

export const syncManager = new SyncManager();
