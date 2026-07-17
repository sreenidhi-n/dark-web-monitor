import { cn } from "@/lib/utils";

type Variant = "default" | "success" | "warning" | "danger" | "info";

const variants: Record<Variant, string> = {
  default: "bg-gray-800 text-gray-300",
  success: "bg-green-900/40 text-green-400",
  warning: "bg-yellow-900/40 text-yellow-400",
  danger:  "bg-red-900/40 text-red-400",
  info:    "bg-blue-900/40 text-blue-400",
};

export function Badge({
  children,
  variant = "default",
  className,
}: {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded text-xs font-medium", variants[variant], className)}>
      {children}
    </span>
  );
}
