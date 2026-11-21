"use client";
import { Mic, Pause, Play, Square, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

type State = "idle" | "recording" | "paused" | "stopped";

function pickMime(): string {
  const options = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  return options.find((t) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) ?? "";
}

const clock = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

/** Record → pause/resume → stop → play back → transcribe or discard. Audio stays in the browser
 *  until the user chooses to transcribe it. */
export function Recorder({ onTranscribe, busy, disabledReason }: { onTranscribe: (blob: Blob) => void; busy: boolean; disabledReason?: string }) {
  const [state, setState] = useState<State>("idle");
  const [seconds, setSeconds] = useState(0);
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const blob = useRef<Blob | null>(null);

  useEffect(() => {
    if (state !== "recording") return;
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [state]);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  useEffect(() => () => rec.current?.stream.getTracks().forEach((t) => t.stop()), []);

  async function start() {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("This browser cannot record audio. Try a current version of Chrome, Edge, Firefox or Safari.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = pickMime();
      const r = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      chunks.current = [];
      r.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data); };
      r.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        blob.current = new Blob(chunks.current, { type: r.mimeType || "audio/webm" });
        setUrl(URL.createObjectURL(blob.current));
        setState("stopped");
      };
      r.start(1000);
      rec.current = r;
      setSeconds(0);
      setState("recording");
    } catch (e) {
      const name = (e as DOMException).name;
      setError(name === "NotAllowedError"
        ? "Microphone access was blocked. Allow it in your browser’s site settings, then try again."
        : name === "NotFoundError" ? "No microphone was found." : "The microphone could not be started.");
    }
  }

  function discard() {
    if (url) URL.revokeObjectURL(url);
    setUrl(null);
    blob.current = null;
    setSeconds(0);
    setState("idle");
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {state === "idle" && <Button onClick={start} disabled={!!disabledReason}><Mic /> Record</Button>}
        {state === "recording" && <>
          <Button variant="outline" onClick={() => { rec.current?.pause(); setState("paused"); }}><Pause /> Pause</Button>
          <Button variant="destructive" onClick={() => rec.current?.stop()}><Square /> Stop</Button>
        </>}
        {state === "paused" && <>
          <Button variant="outline" onClick={() => { rec.current?.resume(); setState("recording"); }}><Play /> Resume</Button>
          <Button variant="destructive" onClick={() => rec.current?.stop()}><Square /> Stop</Button>
        </>}
        {state !== "idle" && state !== "stopped" && (
          <span className="flex items-center gap-2 text-sm tabular-nums" role="status">
            <span className={state === "recording" ? "size-2.5 animate-pulse rounded-full bg-destructive" : "size-2.5 rounded-full bg-muted-foreground"} aria-hidden />
            {state === "recording" ? "Recording" : "Paused"} {clock(seconds)}
          </span>
        )}
      </div>
      {state === "stopped" && url && (
        <div className="space-y-2">
          { }
          <audio controls src={url} className="w-full" aria-label="Play back your recording" />
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => blob.current && onTranscribe(blob.current)} disabled={busy || !!disabledReason}><Upload /> {busy ? "Transcribing…" : "Transcribe"}</Button>
            <Button variant="outline" onClick={discard} disabled={busy}><Trash2 /> Discard</Button>
            <span className="self-center text-xs text-muted-foreground">{clock(seconds)} recorded · not uploaded until you transcribe</span>
          </div>
        </div>
      )}
      {disabledReason && <p className="text-sm text-muted-foreground">{disabledReason}</p>}
      {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
    </div>
  );
}
