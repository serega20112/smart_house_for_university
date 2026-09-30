/** Rounded pill used across the interface. */

interface BadgeProps {
  tone: "ok" | "warn" | "idle" | "bad";
  label: string;
}

export function Badge({ tone, label }: BadgeProps) {
  return <span className={`badge badge--${tone}`}>{label}</span>;
}
