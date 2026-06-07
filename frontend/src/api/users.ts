import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";

import { api } from "@/lib/api";

import type { AppUser, Page, Role } from "./types";

export const userKeys = {
  all: ["users"] as const,
  list: (params: UsersListParams) => ["users", "list", params] as const,
  detail: (id: string) => ["users", "detail", id] as const,
  roles: ["roles"] as const,
};

export interface UsersListParams {
  page?: number;
  page_size?: number;
  search?: string;
  role_id?: string;
  is_active?: boolean;
  include_deleted?: boolean;
}

export interface UserCreateBody {
  email: string;
  full_name: string;
  password: string;
  role_ids?: string[];
}

export interface UserUpdateBody {
  full_name?: string;
  is_active?: boolean;
  role_ids?: string[];
}

// ---- Queries ----

export function useUsersList(params: UsersListParams): UseQueryResult<Page<AppUser>> {
  return useQuery({
    queryKey: userKeys.list(params),
    queryFn: async () => {
      const r = await api.get<Page<AppUser>>("/users", { params });
      return r.data;
    },
  });
}

export function useUser(id: string | undefined) {
  return useQuery({
    queryKey: userKeys.detail(id ?? ""),
    enabled: !!id,
    queryFn: async () => {
      const r = await api.get<AppUser>(`/users/${id}`);
      return r.data;
    },
  });
}

export function useRolesList(): UseQueryResult<Role[]> {
  return useQuery({
    queryKey: userKeys.roles,
    queryFn: async () => {
      const r = await api.get<Role[]>("/roles");
      return r.data;
    },
    staleTime: 5 * 60_000,
  });
}

// ---- Mutations ----

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: UserCreateBody) => {
      const r = await api.post<AppUser>("/auth/register", body);
      return r.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}

export function useUpdateUser(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: UserUpdateBody) => {
      const r = await api.patch<AppUser>(`/users/${id}`, body);
      return r.data;
    },
    onSuccess: (data) => {
      qc.setQueryData(userKeys.detail(id), data);
      void qc.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/users/${id}`);
      return id;
    },
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: userKeys.all });
      const snapshots = qc.getQueriesData<Page<AppUser>>({ queryKey: ["users", "list"] });
      snapshots.forEach(([key, data]) => {
        if (!data) return;
        qc.setQueryData<Page<AppUser>>(key, {
          ...data,
          items: data.items.filter((u) => u.id !== id),
          total: Math.max(0, data.total - 1),
        });
      });
      return { snapshots };
    },
    onError: (_e, _id, ctx) => {
      ctx?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}

export function useRestoreUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const r = await api.post<AppUser>(`/users/${id}/restore`);
      return r.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}

export function useResetPassword(id: string) {
  return useMutation({
    mutationFn: async (password: string) => {
      await api.post(`/users/${id}/reset-password`, { password });
    },
  });
}
