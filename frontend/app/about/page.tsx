export default function AboutPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-10">
      <header>
        <p className="text-xs uppercase tracking-[0.22em] text-muted">Scope</p>
        <h1 className="mt-1 font-display text-4xl tracking-tight">Limits</h1>
        <p className="mt-4 text-lg text-muted">
          AMPscan scores whether a peptide looks like DRAMP General AMPs versus AMPlify published
          non-AMPs. It does not measure killing, MIC, or hemolysis.
        </p>
      </header>

      <section className="membrane rounded-2xl p-6 pt-8">
        <h2 className="font-display text-2xl">Data</h2>
        <ul className="mt-3 space-y-2 text-sm text-muted">
          <li>Positives: DRAMP General FASTA, CC BY 4.0.</li>
          <li>Negatives: AMPlify non-AMP FASTAs, Zenodo 10.5281/zenodo.7320306, CC BY 4.0.</li>
          <li>Length 5-100. B/Z/U/O/J to X. Exact-sequence dedup.</li>
        </ul>
      </section>

      <section className="membrane rounded-2xl p-6 pt-8">
        <h2 className="font-display text-2xl">Homology split</h2>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          MMseqs2 easy-cluster, 30% identity, 80% coverage on the shorter sequence. Whole clusters
          go to train or val or test. 9,241 clusters; <strong>72 mixed</strong> (AMP and non-AMP in
          the same cluster) stay unsplit across folds.
        </p>
      </section>

      <section className="space-y-3">
        {[
          {
            q: "What did we not build?",
            a: "Gene Ontology, Pfam, EC, DeepLoc, full-length proteins, LoRA of ESM-2, and any paid cloud API for the core demo.",
          },
          {
            q: "What does a high P(AMP) mean?",
            a: "The sequence resembles the DRAMP-style AMP class more than the AMPlify non-AMP class on a balanced, homology-held-out test. It is not a wet-lab result.",
          },
          {
            q: "Why is the random-split AUC higher?",
            a: "Related peptides can sit in both train and test. The reported number is homology-split Random Forest ROC-AUC 0.9515.",
          },
        ].map((x) => (
          <details key={x.q} className="panel p-4">
            <summary className="cursor-pointer font-medium">{x.q}</summary>
            <p className="mt-2 text-sm text-muted">{x.a}</p>
          </details>
        ))}
      </section>

      <p className="text-sm text-muted">Hardware: student laptop, NVIDIA RTX 5060 class, 8 GB VRAM. Magainin-2, LL-37, and melittin are homology training sequences.</p>
    </article>
  );
}
