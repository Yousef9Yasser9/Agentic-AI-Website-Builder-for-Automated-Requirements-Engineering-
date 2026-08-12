export type UserRole = "user" | "admin";

export interface AuthUser {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user?: AuthUser;
}

export interface AuthMessageResponse {
  message: string;
  dev_otp?: string;
}
