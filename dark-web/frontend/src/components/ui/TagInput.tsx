"use client";

import { useRef, useState, KeyboardEvent } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface TagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  className?: string;
}

export function TagInput({ tags, onChange, placeholder = "Type and press Enter…", className }: TagInputProps) {
  const [input, setInput] = useState("");
  const ref = useRef<HTMLInputElement>(null);

  function add(raw: string) {
    const val = raw.trim().toLowerCase();
    if (val && !tags.includes(val)) onChange([...tags, val]);
    setInput("");
  }

  function remove(tag: string) {
    onChange(tags.filter((t) => t !== tag));
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(input); }
    else if (e.key === "Backspace" && !input && tags.length > 0) remove(tags[tags.length - 1]);
  }

  return (
    <div
      className={cn(
        "flex flex-wrap gap-1.5 min-h-10 p-2 rounded bg-gray-800 border border-gray-700 cursor-text",
        "focus-within:border-gray-500 transition-colors",
        className
      )}
      onClick={() => ref.current?.focus()}
    >
      {tags.map((tag) => (
        <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-700 text-gray-200 text-xs rounded">
          {tag}
          <button type="button" onClick={() => remove(tag)} className="text-gray-400 hover:text-gray-100">
            <X size={10} />
          </button>
        </span>
      ))}
      <input
        ref={ref}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={() => input.trim() && add(input)}
        placeholder={tags.length === 0 ? placeholder : ""}
        className="flex-1 min-w-24 bg-transparent text-sm text-gray-200 placeholder-gray-600 outline-none"
      />
    </div>
  );
}
