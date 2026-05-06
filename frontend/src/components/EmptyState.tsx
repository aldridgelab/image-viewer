import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  detail?: string;
  spin?: boolean;
}

export function EmptyState({ icon: Icon, title, detail, spin = false }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <Icon size={spin ? 36 : 42} className={spin ? 'spin' : undefined} />
      <h2>{title}</h2>
      {detail && <p>{detail}</p>}
    </div>
  );
}
