"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Plus, Trash2, CheckCheck } from "lucide-react";
import {
  getAlertHistory, getAlertConfigs, getWatchlists,
  acknowledgeAlert, createAlertConfig, deleteAlertConfig,
} from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { Pagination } from "@/components/ui/Pagination";
import { formatRelative, truncate } from "@/lib/utils";
import type { AlertChannel } from "@/lib/types";

type Tab = "history" | "config";

const CHANNEL_OPTIONS: AlertChannel[] = ["email", "slack", "webhook"];
const PAGE_SIZE = 20;

const channelVariant = (c: AlertChannel) =>
  c === "email" ? "info" : c === "slack" ? "warning" : "default";

export default function AlertsPage() {
  const [tab, setTab] = useState<Tab>("history");
  const [page, setPage] = useState(1);
  const [configModal, setConfigModal] = useState(false);
  const [configForm, setConfigForm] = useState({ watchlist_id: 0, channel: "email" as AlertChannel, destination: "" });
  const [configError, setConfigError] = useState("");
  const qc = useQueryClient();

  const historyQuery = useQuery({
    queryKey: ["alert-history", page],
    queryFn: () => getAlertHistory({ page }),
    enabled: tab === "history",
  });

  const configQuery = useQuery({
    queryKey: ["alert-configs"],
    queryFn: getAlertConfigs,
    enabled: tab === "config",
  });

  const watchlistsQuery = useQuery({
    queryKey: ["watchlists"],
    queryFn: getWatchlists,
  });

  const ackMut = useMutation({
    mutationFn: acknowledgeAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-history"] }),
  });

  const createConfigMut = useMutation({
    mutationFn: createAlertConfig,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alert-configs"] }); closeConfigModal(); },
    onError: (e: Error) => setConfigError(e.message),
  });

  const deleteConfigMut = useMutation({
    mutationFn: deleteAlertConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-configs"] }),
  });

  function closeConfigModal() {
    setConfigModal(false);
    setConfigForm({ watchlist_id: 0, channel: "email", destination: "" });
    setConfigError("");
  }

  function submitConfig(e: React.FormEvent) {
    e.preventDefault();
    setConfigError("");
    if (!configForm.watchlist_id) { setConfigError("Select a watchlist"); return; }
    if (!configForm.destination.trim()) { setConfigError("Destination is required"); return; }
    createConfigMut.mutate(configForm);
  }

  const destinationPlaceholder =
    configForm.channel === "email" ? "alerts@yourcompany.com"
    : configForm.channel === "slack" ? "https://hooks.slack.com/services/…"
    : "https://your-siem.example.com/webhook";

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-100">Alerts</h1>
        {tab === "config" && (
          <Button size="sm" onClick={() => setConfigModal(true)}>
            <Plus size={13} /> Add Config
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800">
        {(["history", "config"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t
                ? "border-red-500 text-gray-100"
                : "border-transparent text-gray-500 hover:text-gray-300"
            }`}
          >
            {t === "history" ? "Alert History" : "Notification Config"}
          </button>
        ))}
      </div>

      {/* ── History tab ─────────────────────────────────────────────────────── */}
      {tab === "history" && (
        <>
          {historyQuery.isLoading && <div className="flex justify-center py-16"><Spinner size="lg" /></div>}
          {!historyQuery.isLoading && historyQuery.data?.length === 0 && (
            <EmptyState icon={<Bell size={36} />} title="No alerts yet" description="Alerts appear here when a crawl matches a watchlist term." />
          )}
          {!historyQuery.isLoading && historyQuery.data && historyQuery.data.length > 0 && (
            <>
              <div className="rounded-lg border border-gray-800 overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 bg-gray-900/50">
                      <Th>Watchlist</Th>
                      <Th>Finding</Th>
                      <Th>Channel</Th>
                      <Th>Triggered</Th>
                      <Th>Status</Th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {historyQuery.data.map((a) => {
                      const wl = watchlistsQuery.data?.find((w) => w.id === a.watchlist_id);
                      return (
                        <tr key={a.id} className="bg-gray-900 hover:bg-gray-800/50 transition-colors">
                          <td className="px-4 py-3 text-gray-200 font-medium text-xs">
                            {wl?.name ?? `#${a.watchlist_id}`}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs text-gray-500">
                            finding #{a.finding_id}
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={channelVariant(a.channel)}>{a.channel}</Badge>
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-500">
                            {formatRelative(a.triggered_at)}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex gap-1.5">
                              <Badge variant={a.delivered ? "success" : "warning"}>
                                {a.delivered ? "Delivered" : "Pending"}
                              </Badge>
                              {a.acknowledged && <Badge variant="default">ACK</Badge>}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            {!a.acknowledged && (
                              <Button
                                variant="ghost"
                                size="sm"
                                loading={ackMut.isPending && ackMut.variables === a.id}
                                onClick={() => ackMut.mutate(a.id)}
                                title="Acknowledge"
                              >
                                <CheckCheck size={13} />
                              </Button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <Pagination page={page} pageSize={PAGE_SIZE} total={historyQuery.data.length < PAGE_SIZE ? (page - 1) * PAGE_SIZE + historyQuery.data.length : page * PAGE_SIZE + 1} onPageChange={setPage} />
            </>
          )}
        </>
      )}

      {/* ── Config tab ──────────────────────────────────────────────────────── */}
      {tab === "config" && (
        <>
          {configQuery.isLoading && <div className="flex justify-center py-16"><Spinner size="lg" /></div>}
          {!configQuery.isLoading && configQuery.data?.length === 0 && (
            <EmptyState
              icon={<Bell size={36} />}
              title="No notification configs"
              description="Add a config to start receiving email, Slack, or webhook alerts."
              action={<Button size="sm" onClick={() => setConfigModal(true)}><Plus size={13} /> Add Config</Button>}
            />
          )}
          {!configQuery.isLoading && configQuery.data && configQuery.data.length > 0 && (
            <div className="rounded-lg border border-gray-800 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-900/50">
                    <Th>Watchlist</Th>
                    <Th>Channel</Th>
                    <Th>Destination</Th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {configQuery.data.map((c) => {
                    const wl = watchlistsQuery.data?.find((w) => w.id === c.watchlist_id);
                    return (
                      <tr key={c.id} className="bg-gray-900 hover:bg-gray-800/50 transition-colors">
                        <td className="px-4 py-3 text-gray-200 font-medium text-xs">{wl?.name ?? `#${c.watchlist_id}`}</td>
                        <td className="px-4 py-3"><Badge variant={channelVariant(c.channel)}>{c.channel}</Badge></td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-400">{truncate(c.destination, 55)}</td>
                        <td className="px-4 py-3">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="hover:text-red-400"
                            onClick={() => { if (confirm("Remove this config?")) deleteConfigMut.mutate(c.id); }}
                          >
                            <Trash2 size={13} />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Add config modal */}
      <Modal open={configModal} onClose={closeConfigModal} title="Add Notification Config">
        <form onSubmit={submitConfig} className="space-y-4">
          <Field label="Watchlist">
            <select
              value={configForm.watchlist_id}
              onChange={(e) => setConfigForm((f) => ({ ...f, watchlist_id: Number(e.target.value) }))}
              className={selectCls}
            >
              <option value={0}>Select watchlist…</option>
              {watchlistsQuery.data?.map((wl) => (
                <option key={wl.id} value={wl.id}>{wl.name}</option>
              ))}
            </select>
          </Field>
          <Field label="Channel">
            <div className="flex gap-2">
              {CHANNEL_OPTIONS.map((ch) => (
                <button
                  key={ch}
                  type="button"
                  onClick={() => setConfigForm((f) => ({ ...f, channel: ch }))}
                  className={`flex-1 py-1.5 rounded text-xs font-medium border transition-colors capitalize ${
                    configForm.channel === ch
                      ? "bg-gray-700 border-gray-500 text-gray-100"
                      : "bg-gray-800 border-gray-700 text-gray-500 hover:text-gray-300"
                  }`}
                >
                  {ch}
                </button>
              ))}
            </div>
          </Field>
          <Field label="Destination">
            <input
              required
              value={configForm.destination}
              onChange={(e) => setConfigForm((f) => ({ ...f, destination: e.target.value }))}
              placeholder={destinationPlaceholder}
              className={inputCls}
            />
          </Field>
          {configError && <p className="text-xs text-red-400">{configError}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" onClick={closeConfigModal}>Cancel</Button>
            <Button type="submit" size="sm" loading={createConfigMut.isPending}>Add Config</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

const inputCls = "w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-500 transition-colors";
const selectCls = "w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-gray-500 transition-colors";

function Th({ children }: { children: React.ReactNode }) {
  return <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{children}</th>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-gray-400">{label}</label>
      {children}
    </div>
  );
}
