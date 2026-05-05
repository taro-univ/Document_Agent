import type { CatalogStatus } from "@/types";

const styles: Record<CatalogStatus, string> = {
  proposed: "bg-gray-100 text-gray-600",
  approved: "bg-blue-100 text-blue-700",
  fetched:  "bg-yellow-100 text-yellow-700",
  extracted:"bg-green-100 text-green-700",
};

export function StatusBadge({ status }: { status: CatalogStatus }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}
