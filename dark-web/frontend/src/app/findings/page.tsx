"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Search, SlidersHorizontal } from "lucide-react";
import { getFindings, getSources, searchFindings } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { Pagination } from "@/components/ui/Pagination";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatRelative, truncate } from "@/lib/utils";
import type { Finding, SearchHit } from "@/lib/types";

const PAGE_SIZE = 20;

export default function FindingsPage() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [page, setPage] = useState(1);
  const [sourceFilter, setSourceFilter] = useState<number | undefined>();
  const [since, setSince] = useState("");
  const [expanded, setExpanded] = useState<number | string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Debounce search input 350ms
  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(query);
      setPage(1);
    }, 350);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  const isSearchMode = debouncedQuery.length >= 2;

  const browseQuery = useQuery({
    queryKey: ["findings", page, sourceFilter, since],
    queryFn: () =>
      getFindings({ page, page_size: PAGE_SIZE, source_id: sourceFilter, since: since || undefined }),
    enabled: !isSearchMode,
  });

  const searchQuery = useQuery({
    queryKey: ["findings-search", debouncedQuery],
    queryFn: () => searchFindings(debouncedQuery, 50),
    enabled: isSearchMode,
  });

  const sourcesQuery = useQuery({ queryKey: ["sources"], queryFn: () => getSources() });

  const isLoading = isSearchMode ? searchQuery.isLoading : browseQuery.isLoading;
  const isError = isSearchMode ? searchQuery.isError : browseQuery.isError;

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-100">Findings</h1>
        {!isSearchMode && browseQuery.data && (
          <span className="text-xs text-gray-500">{browseQuery.data.total.toLocaleString()} total</span>
        )}
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search findings by keyword, URL, or content…"
          className="w-full bg-gray-900 border border-gray-800 rounded pl-8 pr-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-600 transition-colors"
        />
        {query && (
          <button onClick={() => setQuery("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 text-xs">
            ✕
          </button>
        )}
      </div>

      {/* Filters (browse mode only) */}
      {!isSearchMode && (
        <div className="flex items-center gap-3 flex-wrap">
          <SlidersHorizontal size={13} className="text-gray-600" />
          <select
            value={sourceFilter ?? ""}
            onChange={(e) => { setSourceFilter(e.target.value ? Number(e.target.value) : undefined); setPage(1); }}
            className="bg-gray-900 border border-gray-800 rounded px-2.5 py-1 text-xs text-gray-300 focus:outline-none focus:border-gray-600"
          >
            <option value="">All sources</option>
            {sourcesQuery.data?.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <input
            type="date"
            value={since}
            onChange={(e) => { setSince(e.target.value); setPage(1); }}
            className="bg-gray-900 border border-gray-800 rounded px-2.5 py-1 text-xs text-gray-400 focus:outline-none focus:border-gray-600"
          />
          {(sourceFilter || since) && (
            <button onClick={() => { setSourceFilter(undefined); setSince(""); }} className="text-xs text-gray-500 hover:text-gray-300">
              Clear
            </button>
          )}
        </div>
      )}

      {/* Results */}
      {isLoading && (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      )}

      {isError && (
        <p className="text-sm text-red-400 text-center py-8">Failed to load findings.</p>
      )}

      {/* Search results */}
      {isSearchMode && !isLoading && (
        <>
          {searchQuery.data?.length === 0 ? (
            <EmptyState title="No results" description={`Nothing matched "${debouncedQuery}"`} icon={<Search size={36} />} />
          ) : (
            <div className="space-y-2">
              {searchQuery.data?.map((hit) => (
                <SearchHitCard key={hit.id} hit={hit} expanded={expanded === hit.id} onToggle={() => setExpanded(expanded === hit.id ? null : hit.id)} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Browse results */}
      {!isSearchMode && !isLoading && (
        <>
          {browseQuery.data?.items.length === 0 ? (
            <EmptyState title="No findings yet" description="Add a source and trigger a crawl to start collecting findings." icon={<Search size={36} />} />
          ) : (
            <>
              <div className="space-y-2">
                {browseQuery.data?.items.map((f) => (
                  <FindingCard key={f.id} finding={f} expanded={expanded === f.id} onToggle={() => setExpanded(expanded === f.id ? null : f.id)} />
                ))}
              </div>
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={browseQuery.data?.total ?? 0}
                onPageChange={setPage}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}

function FindingCard({ finding, expanded, onToggle }: { finding: Finding; expanded: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 hover:border-gray-700 transition-colors cursor-pointer" onClick={onToggle}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-200 truncate">{finding.title || truncate(finding.url, 80)}</p>
          <a href="#" onClick={(e) => e.stopPropagation()} className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 mt-0.5 font-mono">
            {truncate(finding.url, 60)} <ExternalLink size={10} />
          </a>
        </div>
        <span className="text-xs text-gray-600 whitespace-nowrap">{formatRelative(finding.first_seen)}</span>
      </div>
      <div className="flex flex-wrap gap-1.5 mt-3">
        {finding.matched_keywords.map((kw) => (
          <Badge key={kw} variant="danger">{kw}</Badge>
        ))}
        {finding.matched_keywords.length === 0 && (
          <Badge variant="default">No keyword match</Badge>
        )}
      </div>
      {expanded && (
        <p className="mt-3 text-xs text-gray-400 leading-relaxed border-t border-gray-800 pt-3">
          {finding.content_snippet}
        </p>
      )}
    </div>
  );
}

function SearchHitCard({ hit, expanded, onToggle }: { hit: SearchHit; expanded: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 hover:border-gray-700 transition-colors cursor-pointer" onClick={onToggle}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-200 truncate">{hit.title || truncate(hit.url ?? "", 80)}</p>
          <span className="text-xs text-gray-500 font-mono">{truncate(hit.url ?? "", 60)}</span>
        </div>
        <span className="text-xs text-gray-600 whitespace-nowrap">score {hit.score.toFixed(2)}</span>
      </div>
      <div className="flex flex-wrap gap-1.5 mt-3">
        {hit.matched_keywords.map((kw) => (
          <Badge key={kw} variant="danger">{kw}</Badge>
        ))}
      </div>
      {expanded && hit.highlights.length > 0 && (
        <div className="mt-3 border-t border-gray-800 pt-3 space-y-1">
          {hit.highlights.map((h, i) => (
            <p key={i} className="text-xs text-gray-400 leading-relaxed" dangerouslySetInnerHTML={{ __html: h }} />
          ))}
        </div>
      )}
    </div>
  );
}
