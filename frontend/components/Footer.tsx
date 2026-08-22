import Link from "next/link";

export default function Footer() {
  return (
    <footer className="mt-auto border-t" style={{ borderColor: "var(--line)" }}>
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-8 text-sm sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted">AMPscan · peptide vs membrane · 5-100 aa · homology RF ROC-AUC 0.9515</p>
        <div className="flex flex-wrap gap-4 text-muted">
          <Link href="/predict" className="hover:underline">
            Classify
          </Link>
          <Link href="/metrics" className="hover:underline">
            Evidence
          </Link>
          <Link href="/about" className="hover:underline">
            Limits
          </Link>
          <span>MIT code · DRAMP/AMPlify CC BY 4.0</span>
        </div>
      </div>
    </footer>
  );
}
