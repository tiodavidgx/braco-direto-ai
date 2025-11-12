import { apiClient } from "./api";

export interface AuthConfig {
  client_id: string | null;
  has_token: boolean;
  user_email: string | null;
  token_expires: string | null;
}

export interface DeviceFlowResponse {
  user_code: string;
  device_code: string;
  verification_uri: string;
  message: string;
  expires_in: number;
  interval: number;
}

export interface PollResponse {
  success: boolean;
  message: string;
  access_token?: string;
  user_email?: string;
  expires_at?: string;
  error?: boolean;
}

class AuthService {
  async getConfig(): Promise<AuthConfig> {
    return await apiClient.get<AuthConfig>("/auth/config");
  }

  async startDeviceFlow(): Promise<DeviceFlowResponse> {
    return await apiClient.post<DeviceFlowResponse>("/auth/start-device-flow");
  }

  async pollDeviceFlow(deviceCode: string): Promise<PollResponse> {
    return await apiClient.post<PollResponse>("/auth/poll-device-flow", {
      device_code: deviceCode,
    });
  }

  async refreshToken(): Promise<void> {
    await apiClient.post<void>("/auth/refresh");
  }

  async logout(): Promise<void> {
    await apiClient.post<void>("/auth/logout");
  }
}

export const authService = new AuthService();
