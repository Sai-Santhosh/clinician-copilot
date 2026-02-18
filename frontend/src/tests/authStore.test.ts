import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '../store/authStore';

describe('authStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useAuthStore.getState().logout();
  });

  it('starts with no user', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('sets auth state correctly', () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      role: 'clinician' as const,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
    };

    useAuthStore.getState().setAuth(mockUser, 'access-token', 'refresh-token');

    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.accessToken).toBe('access-token');
    expect(state.refreshToken).toBe('refresh-token');
    expect(state.isAuthenticated).toBe(true);
  });

  it('updates tokens correctly', () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      role: 'clinician' as const,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
    };

    useAuthStore.getState().setAuth(mockUser, 'old-access', 'old-refresh');
    useAuthStore.getState().updateTokens('new-access', 'new-refresh');

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe('new-access');
    expect(state.refreshToken).toBe('new-refresh');
    expect(state.user).toEqual(mockUser);
  });

  it('logs out correctly', () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      role: 'admin' as const,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
    };

    useAuthStore.getState().setAuth(mockUser, 'token', 'refresh');
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });
});
