"use client";
import { useId, type ReactNode } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { NONE } from "./common";
import { cn } from "@/lib/utils";

export function Field({ label, hint, children, className, htmlFor }: { label: string; hint?: string; children: ReactNode; className?: string; htmlFor?: string }) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function TextField({ label, value, onChange, hint, className, required, type = "text", placeholder, ...rest }: {
  label: string; value: string; onChange: (v: string) => void; hint?: string; className?: string;
  required?: boolean; type?: string; placeholder?: string; min?: number; max?: number; step?: number | string; autoFocus?: boolean;
}) {
  const id = useId();
  return (
    <Field label={required ? `${label} (required)` : label} hint={hint} className={className} htmlFor={id}>
      <Input id={id} type={type} value={value} onChange={(e) => onChange(e.target.value)} required={required} placeholder={placeholder} {...rest} />
    </Field>
  );
}

export function TextAreaField({ label, value, onChange, hint, className, rows = 3, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; hint?: string; className?: string; rows?: number; placeholder?: string;
}) {
  const id = useId();
  return (
    <Field label={label} hint={hint} className={className} htmlFor={id}>
      <Textarea id={id} value={value} rows={rows} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </Field>
  );
}

/** Select with optional "none" choice. Uses a sentinel because Radix forbids empty values. */
export function SelectField({ label, value, onChange, options, noneLabel, hint, className, disabled }: {
  label: string; value: string | null; onChange: (v: string | null) => void;
  options: { value: string; label: string }[]; noneLabel?: string; hint?: string; className?: string; disabled?: boolean;
}) {
  const id = useId();
  return (
    <Field label={label} hint={hint} className={className} htmlFor={id}>
      <Select value={value ?? NONE} onValueChange={(v) => onChange(v === NONE ? null : v)} disabled={disabled}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {noneLabel !== undefined && <SelectItem value={NONE}>{noneLabel}</SelectItem>}
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </Field>
  );
}

export const orNull = (s: string) => (s.trim() === "" ? null : s.trim());
export const numOrNull = (s: string) => (s.trim() === "" ? null : Number(s));
