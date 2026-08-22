import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-24 text-center">
      <p className="font-display text-6xl">404</p>
      <p className="mt-3 text-muted">That page is not part of AMPscan.</p>
      <Link href="/" className="mt-6 inline-block text-sm" style={{ color: "var(--accent)" }}>
        Back to overview
      </Link>
    </div>
  );
}
