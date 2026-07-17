"use client";

import { cn } from "@/lib/utils";
import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "danger" | "ghost";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variants: Record<Variant, string> = {
  primary:   "bg-red-600 hover:bg-red-500 text-white",
  secondary: "bg-gray-800 hover:bg-gray-700 text-gray-100 border border-gray-700",
  danger:    "hover:bg-red-900/30 text-red-400 border border-red-800",
  ghost:     "hover:bg-gray-800 text-gray-400 hover:text-gray-100",
};

const sizes: Record<Size, string> = {
  sm: "px-2.5 py-1 text-xs",
  md: "px-3.5 py-1.5 text-sm",
  lg: "px-5 py-2 text-base",
};

export function Button({
  variant = "primary",
  size = "md",
  loading,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center gap-2 rounded font-medium transition-colors focus:outline-none",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        className
      )}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
