const MAP: Record<string, string> = {
  B: "X",
  Z: "X",
  U: "X",
  O: "X",
  J: "X",
};
const AA = new Set("ACDEFGHIKLMNPQRSTVWXY".split(""));

export type SeqRecord = { id: string; seq: string };

export const EXAMPLES: { id: string; name: string; seq: string; note: string }[] = [
  {
    id: "magainin-2",
    name: "magainin-2",
    seq: "GIGKFLHSAKKFGKAFVGEIMNS",
    note: "homology train",
  },
  {
    id: "LL-37",
    name: "LL-37",
    seq: "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES",
    note: "homology train",
  },
  {
    id: "melittin",
    name: "melittin",
    seq: "GIGAVLKVLTTGLPALISWIKRKRQQ",
    note: "homology train",
  },
  {
    id: "hCAP-18",
    name: "hCAP-18 (protein, 170 aa)",
    seq: "MKTQRDGHSLGRWSLVLLLLGLVMPLAIIAQVLSYKEAVLRAIDGINQRSSDANLYRLLDLDPRPTMDGDPDTPKPVSFTVKETVCPRTTQQSPEDCDFKKDGLVKRCMGTVTLNQARGSFDISCDKDNKRFALLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES",
    note: "protein sliding scan",
  },
];

export const MAGAININ2 = EXAMPLES[0].seq;
export const HCAP18 = EXAMPLES[3].seq;

export function stripToSequence(raw: string): string {
  const recs = parseRecords(raw);
  return recs[0]?.seq ?? "";
}

export function parseRecords(raw: string): SeqRecord[] {
  const t = raw.trim();
  if (!t) return [];
  if (t.startsWith(">")) {
    const recs: SeqRecord[] = [];
    let id = "seq1";
    let buf: string[] = [];
    const flush = () => {
      const seq = cleanLetters(buf.join(""));
      if (seq) recs.push({ id, seq });
    };
    for (const line of t.split(/\r?\n/)) {
      if (line.startsWith(">")) {
        if (buf.length) flush();
        id = line.slice(1).trim().split(/\s+/)[0] || `seq${recs.length + 1}`;
        buf = [];
      } else buf.push(line);
    }
    flush();
    return recs;
  }
  const seq = cleanLetters(t);
  return seq ? [{ id: "pasted", seq }] : [];
}

function cleanLetters(s: string): string {
  return s
    .replace(/[\s*]/g, "")
    .toUpperCase()
    .replace(/[BZUOJ]/g, (c) => MAP[c] ?? c);
}

export function validateSeq(seq: string): string[] {
  const errors: string[] = [];
  if (!seq) errors.push("No sequence.");
  else {
    if (seq.length < 5 || seq.length > 100) {
      errors.push(`Length ${seq.length} is outside 5-100.`);
    }
    const bad = [...new Set([...seq].filter((c) => !AA.has(c)))].sort().join("");
    if (bad) errors.push(`Non-amino-acid characters after B/Z/U/O/J→X: ${bad}`);
  }
  return errors;
}

export const BATCH_CAP = 500;

