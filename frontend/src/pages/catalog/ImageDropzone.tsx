import { ImagePlus, X } from "lucide-react";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { useUploadImage } from "@/api/products";
import { Button } from "@/components/ui/button";
import { API_BASE_URL, cn } from "@/lib/utils";

interface ImageDropzoneProps {
  value: string[];
  onChange: (urls: string[]) => void;
}

function fullUrl(u: string): string {
  return u.startsWith("http") ? u : `${API_BASE_URL}${u}`;
}

export function ImageDropzone({ value, onChange }: ImageDropzoneProps) {
  const { t } = useTranslation();
  const upload = useUploadImage();
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (accepted.length === 0) return;
      setUploading(true);
      try {
        const results = await Promise.all(
          accepted.map((f) => upload.mutateAsync(f)),
        );
        onChange([...value, ...results.map((r) => r.url)]);
        toast.success(`${results.length} ${t("products.fields.images").toLowerCase()}`);
      } catch {
        toast.error(t("products.error_toast"));
      } finally {
        setUploading(false);
      }
    },
    [value, onChange, upload, t],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/jpeg": [], "image/png": [], "image/webp": [] },
    multiple: true,
    disabled: uploading,
  });

  function removeAt(i: number) {
    onChange(value.filter((_, idx) => idx !== i));
  }

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={cn(
          "flex cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center text-sm transition-colors",
          isDragActive
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/30 hover:border-foreground/50",
          uploading && "pointer-events-none opacity-60",
        )}
      >
        <input {...getInputProps()} />
        <ImagePlus className="h-5 w-5 text-muted-foreground" />
        <span>
          {uploading ? t("common.loading") : t("products.drop_images")}
        </span>
      </div>

      {value.length > 0 && (
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
          {value.map((url, i) => (
            <div
              key={`${url}-${i}`}
              className="group relative aspect-square overflow-hidden rounded-md border bg-muted"
            >
              <img
                src={fullUrl(url)}
                alt=""
                className="h-full w-full object-cover"
              />
              <Button
                type="button"
                variant="destructive"
                size="icon"
                className="absolute right-1 top-1 h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100"
                onClick={() => removeAt(i)}
                aria-label="remove"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
