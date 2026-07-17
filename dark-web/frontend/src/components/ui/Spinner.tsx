import { cn } from "@/lib/utils";

const sizes = { sm: "w-3 h-3 border", md: "w-5 h-5 border-2", lg: "w-8 h-8 border-2" };

export function Spinner({ size = "md", className }: { size?: "sm" | "md" | "lg"; className?: string }) {
  return (
    <div
      className={cn(
        "rounded-full animate-spin border-current border-t-transparent opacity-60",
        sizes[size],
        className
      )}
    />
  );
}
