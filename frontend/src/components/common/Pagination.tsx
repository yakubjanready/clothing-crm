import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pages, total, pageSize, onPageChange }: PaginationProps) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);
  return (
    <div className="flex items-center justify-between gap-3 py-3 text-sm">
      <div className="text-muted-foreground">
        {from}–{to} / {total}
      </div>
      <div className="flex items-center gap-2">
        <Button
          size="icon"
          variant="outline"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label="Previous"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="min-w-[5ch] text-center">
          {page} / {Math.max(1, pages)}
        </span>
        <Button
          size="icon"
          variant="outline"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
          aria-label="Next"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
