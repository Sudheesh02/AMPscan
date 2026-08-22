export default function Logo({ className = "h-10 w-10" }: { className?: string }) {
  return (
    <span className={`relative inline-flex overflow-hidden rounded-full ring-1 ring-[color:var(--accent)]/40 ${className}`}>
      <img src="/media/mark.jpg" alt="" className="h-full w-full scale-110 object-cover" />
    </span>
  );
}
