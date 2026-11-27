import { Eyebrow, SilverRule } from "@/components/atoms";

interface PageHeaderProps {
  eyebrow: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <header className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1.5">
          <Eyebrow className="text-navy-600">{eyebrow}</Eyebrow>
          <h1 className="text-2xl font-bold tracking-tight text-navy-900 md:text-[28px]">{title}</h1>
          {description && <p className="max-w-3xl text-sm text-muted-foreground">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      <SilverRule className="max-w-24" />
    </header>
  );
}
