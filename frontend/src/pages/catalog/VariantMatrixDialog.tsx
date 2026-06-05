import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { z } from "zod";

import { useCreateVariantMatrix } from "@/api/products";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

const schema = z.object({
  sizes: z.string().min(1, "Bo'sh bo'lmasin"),
  colors: z.string().min(1, "Bo'sh bo'lmasin"),
  wholesale_price: z.string().regex(/^\d+(\.\d{1,2})?$/, "Narx noto'g'ri"),
  retail_price: z.string().regex(/^\d+(\.\d{1,2})?$/, "Narx noto'g'ri"),
});
type FormValues = z.infer<typeof schema>;

interface Props {
  productId: string;
  open: boolean;
  onOpenChange: (o: boolean) => void;
}

function parseColors(raw: string): { name: string; hex?: string | null }[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((token) => {
      // "Qora #000000" yoki "Qora"
      const parts = token.split(/\s+/);
      const last = parts[parts.length - 1];
      if (last.startsWith("#")) {
        return { name: parts.slice(0, -1).join(" "), hex: last };
      }
      return { name: token, hex: null };
    });
}

export function VariantMatrixDialog({ productId, open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const create = useCreateVariantMatrix(productId);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      sizes: "S, M, L",
      colors: "Qora #000000, Oq #FFFFFF",
      wholesale_price: "0",
      retail_price: "0",
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("variants.matrix_title")}</DialogTitle>
          <DialogDescription>{t("variants.matrix_desc")}</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            className="space-y-4"
            onSubmit={form.handleSubmit(async (v) => {
              try {
                const result = await create.mutateAsync({
                  sizes: v.sizes
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                  colors: parseColors(v.colors),
                  wholesale_price: v.wholesale_price,
                  retail_price: v.retail_price,
                });
                toast.success(
                  `${t("variants.created_count", { count: result.created.length })} · ${t("variants.skipped_count", { count: result.skipped_existing.length })}`,
                );
                onOpenChange(false);
                form.reset();
              } catch {
                toast.error(t("products.error_toast"));
              }
            })}
          >
            <FormField
              control={form.control}
              name="sizes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("variants.sizes")}</FormLabel>
                  <FormControl>
                    <Input placeholder="S, M, L, XL" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="colors"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("variants.colors")}</FormLabel>
                  <FormControl>
                    <Input placeholder="Qora #000000, Oq #FFFFFF" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="wholesale_price"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("variants.wholesale")}</FormLabel>
                    <FormControl>
                      <Input inputMode="decimal" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="retail_price"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("variants.retail")}</FormLabel>
                    <FormControl>
                      <Input inputMode="decimal" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <DialogFooter className="gap-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={create.isPending}>
                {t("variants.create_matrix")}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
