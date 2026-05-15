import { cn } from "@/lib/utils";

export function Section({
  className,
  title,
  subtitle,
  children,
}: {
  className?: string;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section
      className={cn("mx-auto flex scroll-mt-20 flex-col pt-24 pb-16", className)}
    >
      <header className="flex flex-none flex-col items-center justify-between overflow-visible">
        <div className="mb-4 flex-none overflow-visible bg-linear-to-r from-white via-gray-200 to-gray-400 bg-clip-text pb-2 text-center text-5xl leading-[1.25] font-bold text-transparent">
          {title}
        </div>
        {subtitle && (
          <div className="text-muted-foreground text-center text-xl">
            {subtitle}
          </div>
        )}
      </header>
      <main className="mt-4">{children}</main>
    </section>
  );
}
