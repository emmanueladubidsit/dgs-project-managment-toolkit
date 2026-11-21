"use client";
import { useState, type ReactNode } from "react";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Confirmation for destructive actions. With `typeToConfirm`, the user must type that text. */
export function ConfirmDialog({
  trigger, title, description, confirmLabel = "Delete", typeToConfirm, onConfirm, destructive = true,
}: {
  trigger: ReactNode;
  title: string;
  description: ReactNode;
  confirmLabel?: string;
  typeToConfirm?: string;
  onConfirm: (typed: string) => void;
  destructive?: boolean;
}) {
  const [typed, setTyped] = useState("");
  const blocked = typeToConfirm !== undefined && typed !== typeToConfirm;
  return (
    <AlertDialog onOpenChange={() => setTyped("")}>
      <AlertDialogTrigger asChild>{trigger}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div>{description}</div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        {typeToConfirm !== undefined && (
          <div className="space-y-1.5">
            <Label htmlFor="confirm-text">
              Type <strong className="font-semibold">{typeToConfirm}</strong> to confirm
            </Label>
            <Input id="confirm-text" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
          </div>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            disabled={blocked}
            className={destructive ? "bg-destructive text-white hover:bg-destructive/90" : undefined}
            onClick={() => onConfirm(typed)}
          >
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
