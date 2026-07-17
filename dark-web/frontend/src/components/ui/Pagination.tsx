import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between text-xs text-gray-500 pt-2">
      <span>{from}–{to} of {total.toLocaleString()}</span>
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="sm" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
          <ChevronLeft size={13} />
        </Button>
        <span className="px-2 text-gray-400">{page} / {totalPages}</span>
        <Button variant="ghost" size="sm" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>
          <ChevronRight size={13} />
        </Button>
      </div>
    </div>
  );
}
