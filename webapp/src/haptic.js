/**
 * Telegram WebApp Haptic Feedback Engine
 * Provides tactile feedback for taps, heartbeats, jumpscares, and riddle solutions.
 */

export const Haptic = {
  get tg() {
    return window.Telegram?.WebApp?.HapticFeedback;
  },

  impact(style = 'medium') {
    // style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'
    try {
      this.tg?.impactOccurred(style);
    } catch (e) {
      // fallback on web
    }
  },

  notification(type = 'success') {
    // type: 'error' | 'success' | 'warning'
    try {
      this.tg?.notificationOccurred(type);
    } catch (e) {}
  },

  selection() {
    try {
      this.tg?.selectionChanged();
    } catch (e) {}
  },

  heartbeat() {
    // Double pulse simulating human heartbeat
    this.impact('light');
    setTimeout(() => {
      this.impact('medium');
    }, 180);
  },

  jumpscare() {
    this.impact('heavy');
    setTimeout(() => this.notification('error'), 100);
  }
};
