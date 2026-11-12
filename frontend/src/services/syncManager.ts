import { indexDB, OfflineDraft } from '../db/indexdb';
import { api } from './api';

export type SyncState = 'Sincronizado' | 'Pendiente' | 'Sincronizando' | 'Error' | 'Conflicto';

export interface ConflictDetails {
  localDraft: OfflineDraft;
  outboxActionId?: string;
  campaignId?: string;
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
      this.conflictListeners = this.conflictListeners.filter((l) => l !== listener);
    };
  }

  onStatusChange(listener: StatusListener) {
    this.statusListeners.push(listener);
    listener(this.currentStatus);
    return () => {
      this.statusListeners = this.statusListeners.filter((l) => l !== listener);
    };
  }

  private setStatus(status: SyncState) {
    this.currentStatus = status;
    this.statusListeners.forEach((l) => l(status));
  }

  /**
   * Auto-retry with exponential backoff & jitter <= 60s (RNF-10, RNF-19)
   */
  async processOutbox(): Promise<void> {
    if (this.isSyncing || !navigator.onLine) return;
    this.isSyncing = true;
    this.setStatus('Sincronizando');

    let hasFailure = false;
    let hasConflict = false;

    try {
      const actions = await indexDB.getOutboxActions();
      for (const action of actions) {
        let success = false;
        let attempt = 0;
        const maxAttempts = 3;

        while (!success && attempt < maxAttempts) {
          try {
            const { data } = await api.request<any>(action.endpoint, {
              method: action.method || 'POST',
              body: action.payload,
              idempotencyKey: action.idempotency_key,
            });
            await indexDB.removeOutboxAction(action.id);
            if (action.local_draft_id) {
              await indexDB.updateLocalDraftStatus(action.local_draft_id, 'Sincronizado', {
                server_id: data?.id,
                version_id: data?.version_id || 1,
              });
            }
            success = true;
          } catch (err: any) {
            attempt++;
            if (err.status === 409) {
              hasConflict = true;
              this.setStatus('Conflicto');
              const localDrafts = await indexDB.getLocalDrafts();
              const match =
                localDrafts.find((d) => d.local_id === action.local_draft_id) ||
                localDrafts.find((d) => d.title === action.payload?.title);

              if (match) {
                await indexDB.updateLocalDraftStatus(match.local_id, 'Conflicto');
                const campaignIdFromEndpoint = action.endpoint.split('/campaigns/')[1]?.split('/')[0];
                this.conflictListeners.forEach((l) =>
                  l({
                    localDraft: match,
                    outboxActionId: action.id,
                    campaignId: match.server_id || err.conflictData?.server_data?.id || campaignIdFromEndpoint,
                    serverVersion: err.conflictData?.server_version || 2,
                    serverData: err.conflictData?.server_data || {},
                  })
                );
              }
              return;
            }

            if (attempt < maxAttempts) {
              const jitter = Math.floor(Math.random() * 500);
              const delay = Math.min(60000, Math.pow(2, attempt) * 1000 + jitter);
              await new Promise((res) => setTimeout(res, delay));
            }
          }
        }

        if (!success) {
          hasFailure = true;
          await indexDB.addToOutbox({
            ...action,
            retry_count: (action.retry_count || 0) + maxAttempts,
          });
          if (action.local_draft_id) {
            await indexDB.updateLocalDraftStatus(action.local_draft_id, 'Error');
          }
        }
      }

      if (hasConflict) {
        this.setStatus('Conflicto');
      } else if (hasFailure) {
        this.setStatus('Error');
      } else {
        const remaining = await indexDB.getOutboxActions();
        this.setStatus(remaining.length > 0 ? 'Pendiente' : 'Sincronizado');
      }
    } catch (e) {
      console.error('[SyncManager] Error syncing outbox:', e);
      this.setStatus('Error');
    } finally {
      this.isSyncing = false;
    }
  }
}

export const syncManager = new SyncManager();
