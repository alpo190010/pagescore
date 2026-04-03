"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { authFetch } from "@/lib/auth-fetch";
import { API_URL } from "@/lib/api";

/* ══════════════════════════════════════════════════════════════
   /admin/users — Searchable, filterable user list with pagination
   Protected by proxy.ts admin route guard (S01).
   ══════════════════════════════════════════════════════════════ */

interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  role: string;
  plan_tier: string;
  credits_used: number;
  email_verified: boolean;
  created_at: string | null;
  updated_at: string | null;
}

interface UsersResponse {
  users: AdminUser[];
  total: number;
  page: number;
  per_page: number;
}

const ROLE_OPTIONS = ["all", "user", "admin"] as const;
const PLAN_OPTIONS = ["all", "free", "starter", "growth", "pro"] as const;

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

/** Color token for plan tier badges */
function planBadgeStyle(tier: string): React.CSSProperties {
  switch (tier) {
    case "pro":
      return {
        background: "var(--brand)",
        color: "var(--brand-light)",
      };
    case "growth":
      return {
        background: "var(--success)",
        color: "#fff",
      };
    case "starter":
      return {
        background: "var(--surface-container-high)",
        color: "var(--text-primary)",
      };
    default:
      return {
        background: "var(--surface-container)",
        color: "var(--text-secondary)",
      };
  }
}

function roleBadgeStyle(role: string): React.CSSProperties {
  if (role === "admin") {
    return {
      background: "var(--brand)",
      color: "var(--brand-light)",
    };
  }
  return {
    background: "var(--surface-container)",
    color: "var(--text-secondary)",
  };
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [planFilter, setPlanFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1); // Reset to first page on new search
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [roleFilter, planFilter]);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(perPage));
      if (debouncedSearch) params.set("search", debouncedSearch);
      if (roleFilter !== "all") params.set("role", roleFilter);
      if (planFilter !== "all") params.set("plan_tier", planFilter);

      const res = await authFetch(`${API_URL}/admin/users?${params}`);
      if (!res.ok) throw new Error(`Failed to load users (${res.status})`);

      const data: UsersResponse = await res.json();
      setUsers(data.users);
      setTotal(data.total);
    } catch {
      setError("Failed to load users. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [page, perPage, debouncedSearch, roleFilter, planFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const totalPages = Math.max(1, Math.ceil(total / perPage));

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <h1
          className="text-2xl font-extrabold text-[var(--on-surface)] tracking-tight"
          style={{ fontFamily: "var(--font-manrope), Manrope, sans-serif" }}
        >
          Users
        </h1>
        <span className="text-sm text-[var(--text-secondary)]">
          {total} user{total !== 1 ? "s" : ""} total
        </span>
      </div>

      {/* Search + Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <input
          type="text"
          placeholder="Search by name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search users"
          className="flex-1 px-4 py-2.5 text-sm rounded-xl border-[1.5px] border-[var(--border)] bg-[var(--bg)] text-[var(--text-primary)] outline-none polish-focus-ring"
        />

        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          aria-label="Filter by role"
          className="px-3 py-2.5 text-sm rounded-xl border-[1.5px] border-[var(--border)] bg-[var(--bg)] text-[var(--text-primary)] outline-none polish-focus-ring"
        >
          {ROLE_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r === "all" ? "All roles" : r.charAt(0).toUpperCase() + r.slice(1)}
            </option>
          ))}
        </select>

        <select
          value={planFilter}
          onChange={(e) => setPlanFilter(e.target.value)}
          aria-label="Filter by plan"
          className="px-3 py-2.5 text-sm rounded-xl border-[1.5px] border-[var(--border)] bg-[var(--bg)] text-[var(--text-primary)] outline-none polish-focus-ring"
        >
          {PLAN_OPTIONS.map((p) => (
            <option key={p} value={p}>
              {p === "all" ? "All plans" : p.charAt(0).toUpperCase() + p.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Error state */}
      {error && (
        <div
          className="text-center py-12 rounded-2xl border border-[var(--outline-variant)]"
          style={{ background: "var(--surface-container-lowest)" }}
        >
          <p className="text-sm text-[var(--error)] font-medium mb-4" role="alert">
            {error}
          </p>
          <button
            type="button"
            onClick={fetchUsers}
            className="px-6 py-2 rounded-xl text-sm font-semibold text-white cursor-pointer"
            style={{ background: "var(--brand)" }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !error && (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-16 rounded-xl animate-pulse"
              style={{ background: "var(--surface-container-low)" }}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && users.length === 0 && (
        <div
          className="text-center py-16 rounded-2xl border border-[var(--outline-variant)]"
          style={{ background: "var(--surface-container-lowest)" }}
        >
          <p className="text-lg font-semibold text-[var(--on-surface)] mb-2">
            No users found
          </p>
          <p className="text-sm text-[var(--on-surface-variant)]">
            {debouncedSearch || roleFilter !== "all" || planFilter !== "all"
              ? "Try adjusting your search or filters."
              : "No users have signed up yet."}
          </p>
        </div>
      )}

      {/* User table */}
      {!loading && !error && users.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
            <table className="w-full text-sm">
              <thead>
                <tr
                  className="border-b border-[var(--border)]"
                  style={{ background: "var(--surface-container-low)" }}
                >
                  <th className="text-left px-4 py-3 font-semibold text-[var(--text-secondary)]">
                    Name / Email
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-[var(--text-secondary)]">
                    Role
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-[var(--text-secondary)]">
                    Plan
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-[var(--text-secondary)]">
                    Joined
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className="border-b border-[var(--border)] last:border-b-0 transition-colors hover:bg-[var(--surface-container-low)]"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/admin/users/${user.id}`}
                        className="block group"
                      >
                        <span className="font-medium text-[var(--text-primary)] group-hover:text-[var(--brand)] transition-colors">
                          {user.name || "—"}
                        </span>
                        <span className="block text-xs text-[var(--text-secondary)] mt-0.5">
                          {user.email}
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="inline-block px-2 py-0.5 rounded-full text-xs font-bold"
                        style={roleBadgeStyle(user.role)}
                      >
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="inline-block px-2 py-0.5 rounded-full text-xs font-bold"
                        style={planBadgeStyle(user.plan_tier)}
                      >
                        {user.plan_tier}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">
                      {formatDate(user.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-[var(--border)] text-[var(--text-primary)] bg-[var(--bg)] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors hover:bg-[var(--surface-container-low)]"
            >
              ← Previous
            </button>
            <span className="text-sm text-[var(--text-secondary)]">
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-[var(--border)] text-[var(--text-primary)] bg-[var(--bg)] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors hover:bg-[var(--surface-container-low)]"
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
