"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, List } from "lucide-react";
import { getWatchlists, createWatchlist, updateWatchlist, deleteWatchlist } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { TagInput } from "@/components/ui/TagInput";
import type { ThreatCategory, Watchlist } from "@/lib/types";
import { CategoryBadge } from "@/components/ui/CategoryBadge";

// ── Category metadata (for the picker form) ───────────────────────────────────

const CATEGORIES: { value: ThreatCategory; label: string; color: string; description: string }[] = [
  { value: "general",     label: "General",     color: "bg-gray-700 text-gray-300",         description: "Brand names, internal terms, credentials" },
  { value: "narcotics",   label: "Narcotics",   color: "bg-yellow-900 text-yellow-300",     description: "Drug trafficking, vendor activity" },
  { value: "weapons",     label: "Weapons",     color: "bg-orange-900 text-orange-300",     description: "Illegal firearms, explosives, arms dealers" },
  { value: "trafficking", label: "Trafficking", color: "bg-red-900 text-red-300",           description: "Human trafficking, forced labour" },
  { value: "csam",        label: "CSAM",        color: "bg-red-950 text-red-200 font-bold", description: "Child safety — content auto-redacted, CRITICAL alerts" },
  { value: "fraud",       label: "Fraud",       color: "bg-blue-900 text-blue-300",         description: "Financial fraud, carding, identity theft" },
  { value: "hacking",     label: "Hacking",     color: "bg-purple-900 text-purple-300",     description: "Exploit sales, initial access brokers, 0-days" },
];

const DEFAULT_FORM = {
  name: "",
  keywords: [] as string[],
  domains: [] as string[],
  emails: [] as string[],
  category: "general" as ThreatCategory,
};

export default function WatchlistsPage() {
  const qc = useQueryClient();
  const [modal, setModal] = useState<"create" | "edit" | null>(null);
  const [editTarget, setEditTarget] = useState<Watchlist | null>(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [formError, setFormError] = useState("");

  const { data: watchlists, isLoading } = useQuery({
    queryKey: ["watchlists"],
    queryFn: getWatchlists,
  });

  const createMut = useMutation({
    mutationFn: createWatchlist,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlists"] }); closeModal(); },
    onError: (e: Error) => setFormError(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: typeof DEFAULT_FORM }) =>
      updateWatchlist(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlists"] }); closeModal(); },
    onError: (e: Error) => setFormError(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: deleteWatchlist,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });

  function openCreate() {
    setForm(DEFAULT_FORM);
    setFormError("");
    setEditTarget(null);
    setModal("create");
  }

  function openEdit(wl: Watchlist) {
    setForm({ name: wl.name, keywords: wl.keywords, domains: wl.domains, emails: wl.emails, category: wl.category });
    setFormError("");
    setEditTarget(wl);
    setModal("edit");
  }

  function closeModal() {
    setModal(null);
    setEditTarget(null);
    setFormError("");
  }

  function submitForm(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    if (!form.name.trim()) { setFormError("Name is required"); return; }
    if (modal === "create") createMut.mutate(form);
    else if (editTarget) updateMut.mutate({ id: editTarget.id, payload: form });
  }

  const isSaving = createMut.isPending || updateMut.isPending;
  const totalTerms = (wl: Watchlist) => wl.keywords.length + wl.domains.length + wl.emails.length;
  const selectedCatMeta = CATEGORIES.find((c) => c.value === form.category) ?? CATEGORIES[0];

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-100">Watchlists</h1>
        <Button onClick={openCreate} size="sm">
          <Plus size={13} /> New Watchlist
        </Button>
      </div>

      {isLoading && <div className="flex justify-center py-16"><Spinner size="lg" /></div>}

      {!isLoading && watchlists?.length === 0 && (
        <EmptyState
          icon={<List size={36} />}
          title="No watchlists yet"
          description="Create a watchlist to define what to monitor for across crawled dark web sources."
          action={<Button onClick={openCreate} size="sm"><Plus size={13} /> New Watchlist</Button>}
        />
      )}

      {!isLoading && watchlists && watchlists.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {watchlists.map((wl) => (
            <div key={wl.id} className="rounded-lg border border-gray-800 bg-gray-900 p-4 flex flex-col gap-3">
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-gray-100">{wl.name}</p>
                  <div className="flex items-center gap-1.5">
                    <CategoryBadge category={wl.category} />
                    <span className="text-xs text-gray-600">{totalTerms(wl)} term{totalTerms(wl) !== 1 ? "s" : ""}</span>
                  </div>
                </div>
                <Badge variant={wl.is_active ? "success" : "default"}>
                  {wl.is_active ? "Active" : "Off"}
                </Badge>
              </div>

              <div className="space-y-1.5 flex-1">
                <TermRow label="Keywords" items={wl.keywords} variant="danger" />
                <TermRow label="Domains"  items={wl.domains}  variant="info" />
                <TermRow label="Emails"   items={wl.emails}   variant="warning" />
              </div>

              <div className="flex items-center gap-1.5 pt-1 border-t border-gray-800">
                <Button variant="ghost" size="sm" onClick={() => openEdit(wl)}>
                  <Pencil size={12} /> Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="hover:text-red-400 ml-auto"
                  onClick={() => { if (confirm(`Delete "${wl.name}"?`)) deleteMut.mutate(wl.id); }}
                >
                  <Trash2 size={12} />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={modal !== null}
        onClose={closeModal}
        title={modal === "create" ? "New Watchlist" : `Edit — ${editTarget?.name}`}
        className="max-w-xl"
      >
        <form onSubmit={submitForm} className="space-y-4">
          <Field label="Name">
            <input
              required
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Operation Dread — Narcotics"
              className={inputCls}
            />
          </Field>

          {/* Category picker */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-gray-400">Threat Category</label>
            <div className="grid grid-cols-2 gap-1.5">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, category: cat.value }))}
                  className={`text-left px-2.5 py-2 rounded border text-xs transition-colors ${
                    form.category === cat.value
                      ? "border-gray-500 bg-gray-700"
                      : "border-gray-800 bg-gray-800/50 hover:border-gray-700"
                  }`}
                >
                  <span className={`inline-block rounded px-1 py-0.5 text-[9px] font-bold uppercase tracking-wider mb-1 ${cat.color}`}>
                    {cat.label}
                  </span>
                  <p className="text-gray-500 leading-tight">{cat.description}</p>
                </button>
              ))}
            </div>
            {form.category === "csam" && (
              <p className="text-xs text-red-400 bg-red-950/40 border border-red-900/50 rounded px-3 py-2">
                CSAM category: content snippets are automatically withheld and never stored.
                Findings trigger CRITICAL alerts. Ensure appropriate legal authorization is in place.
              </p>
            )}
          </div>

          <Field label="Keywords" hint={`${selectedCatMeta.label} — ${selectedCatMeta.description}`}>
            <TagInput
              tags={form.keywords}
              onChange={(tags) => setForm((f) => ({ ...f, keywords: tags }))}
              placeholder="term1, term2…"
            />
          </Field>

          <Field label="Domains" hint="Matched anywhere in scraped text">
            <TagInput
              tags={form.domains}
              onChange={(tags) => setForm((f) => ({ ...f, domains: tags }))}
              placeholder="example.com…"
            />
          </Field>

          <Field label="Emails" hint="Specific email addresses to watch for">
            <TagInput
              tags={form.emails}
              onChange={(tags) => setForm((f) => ({ ...f, emails: tags }))}
              placeholder="person@example.com…"
            />
          </Field>

          {formError && <p className="text-xs text-red-400">{formError}</p>}

          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" onClick={closeModal}>Cancel</Button>
            <Button type="submit" size="sm" loading={isSaving}>
              {modal === "create" ? "Create" : "Save"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function TermRow({ label, items, variant }: { label: string; items: string[]; variant: "danger" | "info" | "warning" }) {
  if (items.length === 0) return null;
  return (
    <div className="flex items-start gap-2">
      <span className="text-xs text-gray-600 w-16 pt-0.5 shrink-0">{label}</span>
      <div className="flex flex-wrap gap-1">
        {items.slice(0, 4).map((t) => <Badge key={t} variant={variant}>{t}</Badge>)}
        {items.length > 4 && <span className="text-xs text-gray-600">+{items.length - 4}</span>}
      </div>
    </div>
  );
}

const inputCls = "w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-500 transition-colors";

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div>
        <label className="text-xs font-medium text-gray-400">{label}</label>
        {hint && <p className="text-xs text-gray-600">{hint}</p>}
      </div>
      {children}
    </div>
  );
}
