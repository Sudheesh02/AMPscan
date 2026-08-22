const API = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export type PrimaryScore = {
  model: string;
  p_amp: number;
  label: "AMP" | "non-AMP";
  calibrated: boolean;
  threshold: number;
};

export type SecondaryScore = {
  model: string;
  p_amp: number;
  temperature: number;
  calibrated: boolean;
};

export type PredictResponse = {
  sequence: string;
  length: number;
  valid: boolean;
  errors: string[];
  primary: PrimaryScore | null;
  secondary: SecondaryScore | null;
  features_preview: {
    length: number;
    net_charge_pH7: number;
    GRAVY: number;
    hydrophobic_moment: number;
    aromatic_fraction: number;
    aac_nonzero: Record<string, number>;
  } | null;
};

export type Residue = { pos: number; aa: string; ig: number };

export type ExplainResponse = {
  method: string;
  valid: boolean;
  errors: string[];
  residues: Residue[];
  train_set_warning: boolean;
  matched_train_id: string | null;
  canonical_name: string | null;
  note: string;
};

export type MetricsResponse = {
  homology_test: Array<{
    model: string;
    accuracy: number;
    macro_f1: number;
    roc_auc: number;
    pr_auc: number;
  }>;
  random_test: Array<{
    model: string;
    accuracy: number;
    roc_auc: number;
  }>;
  calibration_ece_homology_test: Array<{
    model: string;
    method: string;
    ece_uncal: number;
    ece_cal: number;
    roc_auc: number;
  }>;
  headline: {
    quote: number;
    model: string;
    do_not_quote: number;
    do_not_quote_note: string;
  };
  plain_english: string;
  sources: string[];
  recomputed: boolean;
};

export type HealthResponse = {
  ok: boolean;
  version?: string;
  device?: string;
  models_loaded?: Record<string, string | number | boolean>;
};

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`API ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function health(): Promise<HealthResponse> {
  const res = await fetch(`${API}/health`, { cache: "no-store" });
  return parseJson(res);
}

export async function predict(sequence: string): Promise<PredictResponse> {
  const res = await fetch(`${API}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sequence }),
  });
  return parseJson(res);
}

export async function explain(sequence: string): Promise<ExplainResponse> {
  const res = await fetch(`${API}/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sequence }),
  });
  return parseJson(res);
}

export async function metrics(): Promise<MetricsResponse> {
  const res = await fetch(`${API}/metrics`, { cache: "no-store" });
  return parseJson(res);
}

export { API };
