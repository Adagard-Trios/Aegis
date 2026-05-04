"use client";

/**
 * Compact image-upload widget — feeds the retinal_disease, retinal_age,
 * and skin_disease runtime adapters via POST /api/upload-image.
 *
 * Usage (mounted on /dashboard/patient):
 *
 *   <ImageUploadWidget patientId={patientId} />
 *
 * Two file inputs (retinal fundus + skin lesion). Each upload posts
 * multipart, surfaces the saved server-side path, and shows a confirm
 * pill so the user knows the next collaborative-diagnosis run will pick
 * it up. Validates client-side for png/jpg/jpeg + 10 MB cap before
 * hitting the network.
 */
import { useRef, useState } from "react";
import { Eye, Image as ImageIcon, Loader2, CheckCircle2, AlertOctagon, UploadCloud } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { uploadImage, type UploadImageResponse } from "../lib/api";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPT = ".png,.jpg,.jpeg";
const ACCEPT_TYPES = ["image/png", "image/jpeg"];

interface ModalitySpec {
  key: "retinal" | "skin";
  label: string;
  hint: string;
  Icon: typeof Eye;
}

const MODALITIES: ModalitySpec[] = [
  { key: "retinal", label: "Retinal fundus", hint: "Drives retinal_disease + retinal_age models", Icon: Eye },
  { key: "skin", label: "Skin lesion", hint: "Drives skin_disease model (Phase 2.B)", Icon: ImageIcon },
];

interface UploadState {
  status: "idle" | "uploading" | "ok" | "error";
  message?: string;
  filename?: string;
}

function ModalityRow({
  spec,
  patientId,
  state,
  setState,
}: {
  spec: ModalitySpec;
  patientId: string | null;
  state: UploadState;
  setState: (s: UploadState) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const Icon = spec.Icon;

  const onPick = () => inputRef.current?.click();

  const onChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";  // reset so re-uploading the same file fires onChange

    if (!ACCEPT_TYPES.includes(file.type) && !ACCEPT.split(",").some((ext) => file.name.toLowerCase().endsWith(ext))) {
      setState({ status: "error", message: `Unsupported type: ${file.type || "unknown"}` });
      return;
    }
    if (file.size > MAX_BYTES) {
      setState({ status: "error", message: `Too large (${(file.size / 1024 / 1024).toFixed(1)} MB > 10 MB cap)` });
      return;
    }

    setState({ status: "uploading", filename: file.name });
    try {
      const res: UploadImageResponse = await uploadImage(file, spec.key, patientId || undefined);
      if (res.status === "ok") {
        setState({ status: "ok", filename: res.filename, message: `Saved as ${res.filename}` });
      } else {
        setState({ status: "error", message: res.error || "Upload failed" });
      }
    } catch (err) {
      setState({ status: "error", message: err instanceof Error ? err.message : "Upload failed" });
    }
  };

  return (
    <div className="flex items-center gap-3 border border-border rounded-md p-3">
      <div className="w-9 h-9 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
        <Icon className="w-4 h-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs font-semibold text-foreground">{spec.label}</div>
        <div className="text-[10px] text-muted-foreground">{spec.hint}</div>

        <AnimatePresence mode="wait">
          {state.status === "ok" && (
            <motion.div
              key="ok"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="text-[10px] text-emerald-300 flex items-center gap-1 mt-1"
            >
              <CheckCircle2 className="w-3 h-3" />
              <span className="truncate">{state.message}</span>
            </motion.div>
          )}
          {state.status === "error" && (
            <motion.div
              key="err"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="text-[10px] text-rose-300 flex items-center gap-1 mt-1"
            >
              <AlertOctagon className="w-3 h-3" />
              <span className="truncate">{state.message}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        onChange={onChange}
        className="hidden"
      />
      <button
        onClick={onPick}
        disabled={state.status === "uploading"}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-primary/10 hover:bg-primary/20 text-primary text-[11px] font-semibold transition-colors disabled:opacity-50"
      >
        {state.status === "uploading" ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <UploadCloud className="w-3.5 h-3.5" />
        )}
        {state.status === "uploading" ? "Uploading..." : "Upload"}
      </button>
    </div>
  );
}

export default function ImageUploadWidget({ patientId }: { patientId: string | null }) {
  const [states, setStates] = useState<Record<string, UploadState>>({
    retinal: { status: "idle" },
    skin: { status: "idle" },
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card border border-border rounded-md p-4 shadow-card space-y-3"
    >
      <div className="flex items-center gap-2">
        <UploadCloud className="w-4 h-4 text-primary" />
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Imaging upload
        </h3>
        <span className="ml-auto text-[10px] text-muted-foreground">PNG / JPG, max 10 MB</span>
      </div>
      <div className="space-y-2">
        {MODALITIES.map((m) => (
          <ModalityRow
            key={m.key}
            spec={m}
            patientId={patientId}
            state={states[m.key]}
            setState={(s) => setStates((prev) => ({ ...prev, [m.key]: s }))}
          />
        ))}
      </div>
      <p className="text-[10px] text-muted-foreground italic">
        Uploaded images are picked up on the next <strong>Run collaborative diagnosis</strong> click on the
        Diagnostics page — the ocular adapter receives the most recent image of each modality.
      </p>
    </motion.div>
  );
}
