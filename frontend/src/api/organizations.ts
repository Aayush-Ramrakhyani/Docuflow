import { apiClient } from "./client";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  plan: string;
  documents_used: number;
  documents_limit: number;
  is_active: boolean;
}

export interface Member {
  id: string;
  user_id: string;
  organization_id: string;
  role: string;
  user_email: string | null;
  user_full_name: string | null;
  user_avatar_url: string | null;
}

export const organizationsApi = {
  listMine: () => apiClient.get<Organization[]>("/organizations/my"),

  get: (orgId: string) => apiClient.get<Organization>(`/organizations/${orgId}`),

  update: (orgId: string, data: { name?: string; logo_url?: string }) =>
    apiClient.patch<Organization>(`/organizations/${orgId}`, data),

  listMembers: (orgId: string) =>
    apiClient.get<Member[]>(`/organizations/${orgId}/members`),

  inviteMember: (orgId: string, email: string, role: string) =>
    apiClient.post(`/organizations/${orgId}/members/invite`, { email, role }),

  updateMemberRole: (orgId: string, membershipId: string, role: string) =>
    apiClient.patch(`/organizations/${orgId}/members/${membershipId}/role`, { role }),

  removeMember: (orgId: string, membershipId: string) =>
    apiClient.delete(`/organizations/${orgId}/members/${membershipId}`),
};
