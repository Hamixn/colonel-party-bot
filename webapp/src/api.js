/**
 * API Client for Colonel's Garden Telegram Mini App
 * Sends cryptographically validated Telegram WebApp initData to server.
 */

const API_BASE = window.location.origin;

export const Api = {
  getInitData() {
    return window.Telegram?.WebApp?.initData || '';
  },

  getTelegramUser() {
    return window.Telegram?.WebApp?.initDataUnsafe?.user || null;
  },

  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': this.getInitData(),
      ...(options.headers || {})
    };

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }
      return await response.json();
    } catch (e) {
      console.warn(`API Error [${endpoint}]:`, e);
      // Fallback mock profile when running locally outside Telegram
      if (endpoint === '/api/me') {
        return this.getMockProfile();
      }
      throw e;
    }
  },

  async getProfile() {
    return await this.request('/api/me');
  },

  async submitRiddle(answer) {
    return await this.request('/api/solve', {
      method: 'POST',
      body: JSON.stringify({ answer })
    });
  },

  async triggerRescue() {
    return await this.request('/api/rescue', {
      method: 'POST'
    });
  },

  async claimImmunity() {
    return await this.request('/api/claim_immunity', {
      method: 'POST'
    });
  },

  async getGameState() {
    return await this.request('/api/state');
  },

  getMockProfile() {
    const tgUser = this.getTelegramUser();
    return {
      id: 1,
      telegram_id: tgUser?.id || 102725917,
      full_name: tgUser?.first_name || 'حامد',
      role: 'role_player',
      has_car: 1,
      car_number: 2,
      driver_name: 'حامد',
      driver_contact: '(@Hamixon)',
      serial_number: 1,
      soul_pin: '210',
      team_number: 1,
      team_name: 'تیم ۱ (خون)',
      teammates: ['لیلا', 'مسعود', 'رویا'],
      riddle_1_solved: 0,
      riddle_2_solved: 0,
      is_immune: 0,
      is_traitor: 0,
      got_stickered: 0
    };
  }
};
