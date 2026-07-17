"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Play, Pencil, Trash2, Globe } from "lucide-react";
import { getSources, createSource, updateSource, deleteSource, triggerCrawl } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { formatRelative } from "@/lib/utils";
import type { Source } from "@/lib/types";

const DEFAULT_FORM = { name: "", onion_url: "", crawl_frequency_hours: 24 };

export default function SourcesPage() {
  const qc = useQueryClient();
  const [modal, setModal] = useState<"create" | "edit" | null>(null);
  const [editTarget, setEditTarget] = useState<Source | null>(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [crawlingIds, setCrawlingIds] = useState<Set<number>>(new Set());
  const [formError, setFormError] = useState("");

  const { data: sources, isLoading } = useQuery({
    queryKey: ["sources"],
    queryFn: () => getSources(false),
  });

  const createMut = useMutation({
    mutationFn: createSource,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sources"] }); closeModal(); },
    onError: (e: Error) => setFormError(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: typeof DEFAULT_FORM }) =>
      updateSource(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sources"] }); closeModal(); },
    onError: (e: Error) => setFormError(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: deleteSource,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources"] }),
  });

  function openCreate() {
    setForm(DEFAULT_FORM);
    setFormError("");
    setEditTarget(null);
    setModal("create");
  }

  function openEdit(source: Source) {
    setForm({ name: source.name, onion_url: source.onion_url, crawl_frequency_hours: source.crawl_frequency_hours });
    setFormError("");
    setEditTarget(source);
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
    if (modal === "create") createMut.mutate(form);
    else if (editTarget) updateMut.mutate({ id: editTarget.id, payload: form });
  }

  async function handleCrawl(id: number) {
    setCrawlingIds((s) => new Set(s).add(id));
    try { await triggerCrawl(id); }
    finally { setCrawlingIds((s) => { const n = new Set(s); n.delete(id); return n; }); }
  }

  const isSaving = createMut.isPending || updateMut.isPending;

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-100">Sources</h1>
        <Button onClick={openCreate} size="sm">
          <Plus size={13} /> Add Source
        </Button>
      </div>

      {isLoading && <div className="flex justify-center py-16"><Spinner size="lg" /></div>}

      {!isLoading && sources?.length === 0 && (
        <EmptyState
          icon={<Globe size={36} />}
          title="No sources yet"
          description="Add a .onion URL to start monitoring."
          action={<Button onClick={openCreate} size="sm"><Plus size={13} /> Add Source</Button>}
        />
      )}

      {!isLoading && sources && sources.length > 0 && (
        <div className="rounded-lg border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/50">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">URL</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Freq</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Last Crawled</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {sources.map((s) => (
                <tr key={s.id} className="bg-gray-900 hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-200">{s.name}</td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs text-gray-400">{s.onion_url.slice(0, 40)}{s.onion_url.length > 40 ? "…" : ""}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{s.crawl_frequency_hours}h</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {s.last_crawled_at ? formatRelative(s.last_crawled_at) : <span className="text-gray-600">Never</span>}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={s.is_active ? "success" : "default"}>
                      {s.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <Button
                        variant="ghost"
                        size="sm"
                        loading={crawlingIds.has(s.id)}
                        onClick={() => handleCrawl(s.id)}
                        disabled={!s.is_active}
                        title="Crawl now"
                      >
                        <Play size={13} />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => openEdit(s)} title="Edit">
                        <Pencil size={13} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => { if (confirm(`Remove "${s.name}"?`)) deleteMut.mutate(s.id); }}
                        title="Remove"
                        className="hover:text-red-400"
                      >
                        <Trash2 size={13} />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={modal !== null} onClose={closeModal} title={modal === "create" ? "Add Source" : "Edit Source"}>
        <form onSubmit={submitForm} className="space-y-4">
          <Field label="Name">
            <input
              required
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Paste Site Alpha"
              className={inputCls}
            />
          </Field>
          <Field label=".onion URL">
            <input
              required
              value={form.onion_url}
              onChange={(e) => setForm((f) => ({ ...f, onion_url: e.target.value }))}
              placeholder="http://examplexxxxxxxx.onion"
              className={inputCls}
            />
          </Field>
          <Field label="Crawl frequency (hours)">
            <input
              type="number"
              min={1}
              max={8760}
              value={form.crawl_frequency_hours}
              onChange={(e) => setForm((f) => ({ ...f, crawl_frequency_hours: Number(e.target.value) }))}
              className={inputCls}
            />
          </Field>
          {formError && <p className="text-xs text-red-400">{formError}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" onClick={closeModal}>Cancel</Button>
            <Button type="submit" size="sm" loading={isSaving}>
              {modal === "create" ? "Add Source" : "Save"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

const inputCls = "w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-500 transition-colors";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-gray-400">{label}</label>
      {children}
    </div>
  );
}
